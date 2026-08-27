from __future__ import annotations

from datetime import timedelta
import json
from types import SimpleNamespace
from typing import Any

import c2_imugs2.infrastructure.mongo as mongo_maintenance
import pytest
from c2_imugs2.infrastructure.mongo import (
    FeedbackCompactionPlan,
    FeedbackCompactionResult,
    FeedbackRetentionPolicy,
    MongoIndexManager,
    MongoIndexSpec,
    base_index_specs,
    compact_mission_feedback,
    map_feature_index_specs,
    plan_feedback_compaction,
)


class FakeCollection:
    def __init__(self, *, indexes: list[dict[str, Any]] | None = None, duplicate: Any = None) -> None:
        self.indexes = indexes or [{"name": "_id_", "key": {"_id": 1}, "unique": True}]
        self.duplicate = duplicate
        self.created: list[tuple[list[tuple[str, Any]], dict[str, Any]]] = []

    def list_indexes(self) -> list[dict[str, Any]]:
        return self.indexes

    def aggregate(self, _pipeline: list[dict[str, Any]], **_kwargs: Any) -> list[dict[str, Any]]:
        return [] if self.duplicate is None else [{"_id": self.duplicate, "count": 2}]

    def create_index(self, keys: list[tuple[str, Any]], **options: Any) -> str:
        self.created.append((keys, options))
        return str(options["name"])


class FakeClient:
    def __init__(self, collections: dict[tuple[str, str], FakeCollection]) -> None:
        self.collections = collections

    def __getitem__(self, database: str) -> Any:
        return _FakeDatabase(self.collections, database)


class _FakeDatabase:
    def __init__(self, collections: dict[tuple[str, str], FakeCollection], database: str) -> None:
        self.collections = collections
        self.database = database

    def __getitem__(self, collection: str) -> FakeCollection:
        return self.collections[(self.database, collection)]


class FakeCursor(list[dict[str, Any]]):
    def sort(self, _keys: list[tuple[str, int]]) -> "FakeCursor":
        return self

    def limit(self, value: int) -> "FakeCursor":
        return FakeCursor(self[:value])


class FakeFeedbackCollection:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents
        self.delete_filters: list[dict[str, Any]] = []

    def find(self, _query: dict[str, Any], _projection: dict[str, int]) -> FakeCursor:
        return FakeCursor(self.documents)

    def delete_many(self, query: dict[str, Any]) -> Any:
        self.delete_filters.append(query)
        return SimpleNamespace(deleted_count=len(query["_id"]["$in"]))


def test_index_plan_covers_runtime_catalog_and_versioned_map_queries() -> None:
    specs = {(spec.database, spec.collection, spec.name): spec for spec in base_index_specs()}

    feedback = specs[("RuntimeDB", "MissionFeedback", "mission_feedback_mission_order")]
    logs = specs[("RuntimeDB", "Logs", "logs_mission_order")]
    assert feedback.keys == (("mission_id", 1), ("_id", -1))
    assert logs.keys == (("mission_id", 1), ("_id", -1))
    assert specs[("RuntimeDB", "MissionConfig", "mission_config_mission")].unique is False
    assert specs[("RuntimeDB", "Planning", "planning_mission")].unique is False
    assert specs[("RuntimeDB", "ConnectedVehicles", "connected_vehicles_agent")].unique is False
    assert specs[("VehicleDB", "Vehicles", "vehicles_agent")].unique is False
    assert specs[("MapDB", "_scenario_versions", "scenario_versions_collection_unique")].unique
    assert specs[("MapDB", "_scenario_versions", "scenario_versions_identity_unique")].unique
    assert specs[("MapDB", "_active_scenario", "active_scenario_singleton_unique")].unique
    assert specs[("MapDB", "_scenario_activations", "scenario_activation_id_unique")].unique
    assert specs[("MapDB", "_scenario_activations", "scenario_activations_status_recorded")].keys == (
        ("status", 1),
        ("recorded_at", -1),
    )

    map_specs = {spec.name: spec for spec in map_feature_index_specs("scenario_alpha_v1")}
    assert map_specs["scenario_feature_id_unique"].unique
    assert map_specs["scenario_feature_type"].keys == (("properties.feature_type", 1),)
    assert map_specs["scenario_feature_geometry_2dsphere"].keys == (("geometry", "2dsphere"),)


def test_index_manager_is_idempotent_and_never_replaces_conflicts() -> None:
    spec = MongoIndexSpec(
        "MapDB",
        "_scenario_versions",
        (("map_collection", 1),),
        "scenario_versions_collection_unique",
        unique=True,
        partial_filter={"map_collection": {"$type": "string"}},
    )
    collection = FakeCollection()
    client = FakeClient({("MapDB", "_scenario_versions"): collection})

    created = MongoIndexManager(client).ensure([spec])[0]

    assert created.status == "created"
    assert collection.created == [
        (
            [("map_collection", 1)],
            {
                "name": "scenario_versions_collection_unique",
                "unique": True,
                "partialFilterExpression": {"map_collection": {"$type": "string"}},
            },
        )
    ]

    existing_collection = FakeCollection(
        indexes=[
            {
                "name": spec.name,
                "key": {"map_collection": 1},
                "unique": True,
                "partialFilterExpression": {"map_collection": {"$type": "string"}},
            }
        ]
    )
    existing_client = FakeClient({("MapDB", "_scenario_versions"): existing_collection})
    existing = MongoIndexManager(existing_client).ensure([spec])[0]
    assert existing.status == "existing"
    assert existing_collection.created == []

    conflict_collection = FakeCollection(
        indexes=[{"name": spec.name, "key": {"map_collection": -1}, "unique": True}]
    )
    conflict_client = FakeClient({("MapDB", "_scenario_versions"): conflict_collection})
    conflict = MongoIndexManager(conflict_client).ensure([spec])[0]
    assert conflict.status == "conflict"
    assert conflict_collection.created == []

    non_unique_spec = MongoIndexSpec(
        "RuntimeDB",
        "MissionConfig",
        (("mission_id", 1),),
        "mission_config_mission",
    )
    incompatible_unique = FakeCollection(
        indexes=[
            {
                "name": non_unique_spec.name,
                "key": {"mission_id": 1},
                "unique": True,
            }
        ]
    )
    non_unique_client = FakeClient(
        {("RuntimeDB", "MissionConfig"): incompatible_unique}
    )
    outcome = MongoIndexManager(non_unique_client).ensure([non_unique_spec])[0]
    assert outcome.status == "conflict"


def test_index_manager_blocks_unique_index_when_duplicate_data_exists() -> None:
    spec = map_feature_index_specs("scenario_alpha_v1")[0]
    collection = FakeCollection(duplicate="road-1")
    client = FakeClient({("MapDB", "scenario_alpha_v1"): collection})

    outcome = MongoIndexManager(client).ensure([spec])[0]

    assert outcome.status == "blocked"
    assert "road-1" in outcome.detail
    assert collection.created == []


def test_feedback_compaction_preserves_latest_transitions_paths_and_checkpoints() -> None:
    documents = [
        _feedback(0, minute=0, status=0),
        _feedback(1, minute=1, status=0),
        _feedback(2, minute=2, status=1),
        _feedback(3, minute=3, status=1),
        _feedback(4, minute=4, status=1, tasks=[{"vehicle_id": "robot", "waypoints": [[1, 2]]}]),
        _feedback(5, minute=5, status=1, tasks=[{"vehicle_id": "robot", "waypoints": [[1, 2]]}]),
        _feedback(6, minute=8, status=1, tasks=[{"vehicle_id": "robot", "waypoints": [[1, 2]]}]),
        _feedback(7, minute=9, status=1, tasks=[{"vehicle_id": "robot", "waypoints": [[1, 2]]}]),
    ]
    policy = FeedbackRetentionPolicy(recent_per_mission=2, checkpoint_interval=timedelta(minutes=3))

    plan = plan_feedback_compaction(documents, policy)

    assert {0, 2, 4, 6, 7} <= set(plan.keep_ids)
    assert {1, 3, 5} == set(plan.delete_ids)
    assert plan.kept_by_reason["status_change"] == 1
    assert plan.kept_by_reason["path_change"] == 1
    assert plan.kept_by_reason["checkpoint"] >= 1


def test_feedback_compaction_is_dry_run_by_default_and_apply_is_explicit() -> None:
    documents = [_feedback(index, minute=index, status=0) for index in range(5)]
    collection = FakeFeedbackCollection(documents)
    policy = FeedbackRetentionPolicy(recent_per_mission=1, checkpoint_interval=timedelta(hours=1))

    preview = compact_mission_feedback(collection, policy=policy)

    assert preview.dry_run is True
    assert preview.deleted_count == 0
    assert set(preview.plan.delete_ids) == {1, 2, 3}
    assert collection.delete_filters == []

    applied = compact_mission_feedback(collection, policy=policy, dry_run=False, delete_batch_size=2)

    assert applied.dry_run is False
    assert applied.deleted_count == 3
    assert collection.delete_filters == [
        {"_id": {"$in": [1, 2]}},
        {"_id": {"$in": [3]}},
    ]


def test_feedback_compaction_refuses_an_unbounded_database_scope() -> None:
    documents = [_feedback(index, minute=index, status=0) for index in range(3)]
    collection = FakeFeedbackCollection(documents)

    with pytest.raises(ValueError, match="feedback-max-documents"):
        compact_mission_feedback(collection, max_documents=2)

    assert collection.delete_filters == []


def test_feedback_compaction_cli_is_dry_run_by_default(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def fake_compaction(_mongodb_url: str, **kwargs: Any) -> FeedbackCompactionResult:
        calls.append(kwargs)
        return FeedbackCompactionResult(
            plan=FeedbackCompactionPlan(
                documents_seen=10,
                keep_ids=(1, 10),
                delete_ids=tuple(range(2, 10)),
                kept_by_reason={"first": 1, "latest": 1},
            ),
            dry_run=kwargs["dry_run"],
            deleted_count=0,
        )

    monkeypatch.setattr(mongo_maintenance, "compact_feedback_history", fake_compaction)

    result = mongo_maintenance.main(["--compact-feedback", "--mongodb-url", "mongodb://unused"])

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert calls[0]["dry_run"] is True
    assert output["dry_run"] is True
    assert output["candidate_delete_count"] == 8
    assert "delete_ids" not in output


def _feedback(index: int, *, minute: int, status: int, tasks: Any = None) -> dict[str, Any]:
    document = {
        "_id": index,
        "mission_id": "mission-1",
        "date": f"2026-08-22T10:{minute:02d}:00Z",
        "status": status,
        "requested_status": 0,
        "issue": 0,
    }
    if tasks is not None:
        document["tasks"] = tasks
    return document
