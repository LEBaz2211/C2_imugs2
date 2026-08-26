from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from pymongo.errors import ServerSelectionTimeoutError

from c2_imugs2.live_operational import LiveOperationalReadModelProvider
from c2_imugs2.operational_context import OperationalContextService, UpdateMode
from c2_imugs2.operational_picture import Freshness


MISSION_ID = "11111111-2222-3333-4444-555555555555"
LEGACY_MISSION_ID = "11111111_2222_3333_4444_555555555555"
AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5"


class FakeCursor(list):
    def __init__(self, values: list[dict[str, Any]], collection: "FakeCollection") -> None:
        super().__init__(values)
        self.collection = collection

    def limit(self, value: int) -> "FakeCursor":
        self.collection.find_limits.append(value)
        return FakeCursor(list(self)[:value], self.collection)


class FakeCollection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.find_calls: list[tuple[dict[str, Any], dict[str, Any]]] = []
        self.find_limits: list[int] = []
        self.aggregate_calls: list[tuple[list[dict[str, Any]], dict[str, Any]]] = []

    def find(
        self, query: dict[str, Any], projection: dict[str, Any]
    ) -> FakeCursor:
        self.find_calls.append((query, projection))
        return FakeCursor(self.rows, self)

    def aggregate(
        self, pipeline: list[dict[str, Any]], **kwargs: Any
    ) -> list[dict[str, Any]]:
        self.aggregate_calls.append((pipeline, kwargs))
        # The focused test exercises the pure summarizers with legacy raw rows;
        # production Mongo applies the recorded server-side projection.
        return self.rows


class FailingFindCollection(FakeCollection):
    def find(
        self, query: dict[str, Any], projection: dict[str, Any]
    ) -> FakeCursor:
        raise ServerSelectionTimeoutError("profile collection unavailable")


class FailingAggregateCollection(FakeCollection):
    def aggregate(
        self, pipeline: list[dict[str, Any]], **kwargs: Any
    ) -> list[dict[str, Any]]:
        raise ServerSelectionTimeoutError("active map collection unavailable")


class FakeAdmin:
    def command(self, name: str) -> dict[str, int]:
        assert name == "ping"
        return {"ok": 1}


class FakeClient:
    def __init__(self, collections: dict[tuple[str, str], FakeCollection]) -> None:
        self.collections = collections
        self.admin = FakeAdmin()

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def __getitem__(self, database: str) -> "FakeDatabase":
        return FakeDatabase(database, self.collections)


class FakeDatabase:
    def __init__(
        self, database: str, collections: dict[tuple[str, str], FakeCollection]
    ) -> None:
        self.database = database
        self.collections = collections

    def __getitem__(self, collection: str) -> FakeCollection:
        return self.collections[(self.database, collection)]


class Scenario:
    def validated_active(self) -> dict[str, Any]:
        return {
            "scenario_id": "rma-demo",
            "version": "1",
            "status": "ready",
            "ready": True,
            "map": "rma",
            "map_collection": "scenario_rma_demo_v1",
            "feature_count": 2,
            "road_count": 1,
            "feature_ids": ["parade-area"],
            "agents": [{"agent_id": AGENT_ID, "name": "Themis Fr"}],
        }


def _fixture() -> tuple[
    LiveOperationalReadModelProvider,
    SimpleNamespace,
    dict[tuple[str, str], FakeCollection],
]:
    runtime = SimpleNamespace(
        missions={
            MISSION_ID: {
                "mission_id": MISSION_ID,
                "status": 1,
                "status_name": "PLANNED",
                "status_source": "adapter_optimistic",
                "path_status": "missing",
                "config": {
                    "name": "Adapter mission",
                    "behavior": 0,
                    "vehicles": [AGENT_ID],
                    "objective": {
                        "geometries": [
                            {
                                "geometry": {
                                    "geometry_type": "Point",
                                    "coordinates": [[999.123, 888.456]],
                                }
                            }
                        ]
                    },
                },
            }
        },
        forgotten_missions=set(),
        agent_updates={},
        planner_state={},
        storage_bootstrap={"status": "ready", "ok": True},
    )
    collections = {
        ("RuntimeDB", "ConnectedVehicles"): FakeCollection(
            [{"AgentId": "agent_" + AGENT_ID.replace("-", "_")}]
        ),
        ("VehicleDB", "Vehicles"): FakeCollection(
            [{"agent_id": AGENT_ID, "name": "Themis Fr", "capabilities": ["drive"]}]
        ),
        ("RuntimeDB", "MissionConfig"): FakeCollection(
            [
                {
                    "_id": "config-1",
                    "MissionId": LEGACY_MISSION_ID,
                    "Name": "Backend mission",
                    "Behavior": 0,
                    "Vehicles": [AGENT_ID],
                    "objective": {"geometry": {"coordinates": [777.1, 777.2]}},
                }
            ]
        ),
        ("RuntimeDB", "MissionFeedback"): FakeCollection(
            [
                {
                    "_id": "feedback-1",
                    "MissionId": LEGACY_MISSION_ID,
                    "Behavior": 0,
                    "Status": 1,
                    "RequestedStatus": 0,
                    "Issue": 0,
                    "Date": "2026-08-22T10:00:00Z",
                    "Tasks": [
                        {
                            "VehicleId": AGENT_ID,
                            "Waypoints": [
                                {"Coordinates": [51.0, 4.0]},
                                {"Coordinates": [51.1, 4.1]},
                            ],
                        }
                    ],
                }
            ]
        ),
        ("RuntimeDB", "Planning"): FakeCollection(
            [
                {
                    "_id": "planning-1",
                    "mission_id": MISSION_ID,
                    "tasks": {
                        AGENT_ID: {
                            "objectives": [
                                {
                                    "primitives": [
                                        {"parameters": {"coordinates": [66.1, 66.2]}},
                                        {"parameters": {"coordinates": [66.3, 66.4]}},
                                    ]
                                }
                            ]
                        }
                    },
                }
            ]
        ),
        ("MapDB", "scenario_rma_demo_v1"): FakeCollection(
            [
                {
                    "type": "Feature",
                    "id": "parade-area",
                    "properties": {
                        "feature_id": "parade-area",
                        "feature_type": "geofence",
                        "name": "parade",
                        "source": "user",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [4.3919, 50.8455],
                                [4.3931, 50.8452],
                                [4.3934, 50.8457],
                                [4.3922, 50.8459],
                                [4.3919, 50.8455],
                            ]
                        ],
                    },
                }
            ]
        ),
    }
    client = FakeClient(collections)
    provider = LiveOperationalReadModelProvider(
        runtime,
        Scenario(),
        "mongodb://unused",
        mongo_timeout_ms=125,
        mission_limit=8,
        observation_limit=12,
        agent_limit=6,
        mongo_client_factory=lambda *args, **kwargs: client,
    )
    return provider, runtime, collections


def test_live_picture_merges_adapter_and_backend_truth_without_payload_arrays() -> None:
    provider, _, collections = _fixture()

    picture = provider.read_operational_model()
    mission = picture.sections["missions"].items[MISSION_ID]

    assert mission.source_ids == (
        "RuntimeDB.MissionConfig",
        "RuntimeDB.MissionFeedback",
        "RuntimeDB.Planning",
        "adapter-runtime",
    )
    assert mission.data["adapter_state"]["status"] == 1
    assert mission.data["adapter_state"]["status_source"] == "adapter_optimistic"
    assert mission.data["backend_feedback"]["status"] == 1
    assert mission.data["backend_feedback"]["status_name"] == "PLANNED"
    assert mission.data["backend_feedback"]["has_paths"] is True
    assert mission.data["backend_feedback"]["path_summary"] == {
        "path_count": 1,
        "waypoint_count": 2,
        "waypoints_by_agent": {AGENT_ID: 2},
    }
    assert mission.data["effective_status_source"] == "RuntimeDB.MissionFeedback"
    assert mission.data["backend_planning"]["has_paths"] is True
    scenario = next(iter(picture.sections["scenario"].items.values()))
    assert scenario.data["map_features"] == [
        {
            "feature_id": "parade-area",
            "name": "parade",
            "feature_type": "geofence",
            "origin": "user",
            "geometry_status": "exact",
            "coordinate_count": 5,
            "geometry": {
                "geometry_type": "Polygon",
                "coordinates": [
                    [
                        [4.3919, 50.8455],
                        [4.3931, 50.8452],
                        [4.3934, 50.8457],
                        [4.3922, 50.8459],
                        [4.3919, 50.8455],
                    ]
                ],
            },
            "freshness": "fresh",
            "provenance": "active operating map",
            "source_id": "MapDB.active",
        }
    ]
    assert scenario.source_ids == ("MapDB.active", "scenario-runtime")

    encoded = json.dumps(mission.data, sort_keys=True)
    assert "coordinates" not in encoded.lower()
    assert "999.123" not in encoded
    assert "777.1" not in encoded
    assert "66.1" not in encoded

    for collection_name in ("MissionConfig", "MissionFeedback", "Planning"):
        call = collections[("RuntimeDB", collection_name)].aggregate_calls[0]
        pipeline, kwargs = call
        assert pipeline[0] == {"$sort": {"_id": -1}}
        assert pipeline[1] == {"$limit": 12}
        assert kwargs == {"maxTimeMS": 125}
        projected_fields = set(pipeline[-1]["$project"])
        assert not projected_fields.intersection(
            {"objective", "geometry", "tasks", "Tasks", "waypoints", "Waypoints"}
        )
    map_pipeline, map_kwargs = collections[
        ("MapDB", "scenario_rma_demo_v1")
    ].aggregate_calls[0]
    assert map_pipeline[0]["$match"] == {
        "properties.feature_type": {
            "$in": ["objective", "geofence", "workspace", "risk"]
        }
    }
    assert map_pipeline[1] == {
        "$sort": {
            "properties.feature_type": 1,
            "properties.feature_id": 1,
            "id": 1,
        }
    }
    assert map_pipeline[2] == {"$limit": 65}
    assert "geometry" not in map_pipeline[-1]["$project"]
    assert map_kwargs == {"maxTimeMS": 125, "allowDiskUse": False}


def test_oversized_active_map_geometry_is_summarized_without_coordinates() -> None:
    provider, _, collections = _fixture()
    ring = [[4.0 + index / 10_000, 50.0] for index in range(129)]
    ring.append(ring[0])
    collections[("MapDB", "scenario_rma_demo_v1")].rows[0]["geometry"][
        "coordinates"
    ] = [ring]

    picture = provider.read_operational_model()
    scenario = next(iter(picture.sections["scenario"].items.values()))
    feature = scenario.data["map_features"][0]

    assert feature["geometry_status"] == "omitted_coordinate_limit"
    assert feature["coordinate_count"] == 130
    assert "geometry" not in feature
    assert "4.0001" not in json.dumps(picture.to_dict())


def test_invalid_active_map_geometry_is_retained_as_a_stale_named_fact() -> None:
    provider, _, collections = _fixture()
    collections[("MapDB", "scenario_rma_demo_v1")].rows[0]["geometry"][
        "coordinates"
    ] = [[[4.0, 50.0], [4.1, 50.0], [4.1, 50.1], [4.0, 50.1]]]

    picture = provider.read_operational_model()
    scenario = next(iter(picture.sections["scenario"].items.values()))
    feature = scenario.data["map_features"][0]

    assert feature["feature_id"] == "parade-area"
    assert feature["geometry_status"] == "invalid"
    assert feature["freshness"] == "stale"
    assert "geometry" not in feature
    assert picture.sources["MapDB.active"].freshness is Freshness.STALE
    assert "active-map-features-invalid" in picture.sections["warnings"].items


def test_active_map_feature_observation_is_strictly_limited_and_explicit() -> None:
    provider, _, collections = _fixture()
    provider.map_feature_limit = 3
    provider.map_total_coordinate_limit = 4
    collections[("MapDB", "scenario_rma_demo_v1")].rows = [
        {
            "id": f"objective-{index}",
            "properties": {
                "feature_id": f"objective-{index}",
                "feature_type": "objective",
                "name": f"Objective {index}",
                "source": "user",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [4.39 + index / 1000, 50.84],
            },
        }
        for index in range(4)
    ]

    picture = provider.read_operational_model()
    scenario = next(iter(picture.sections["scenario"].items.values()))

    assert [feature["feature_id"] for feature in scenario.data["map_features"]] == [
        "objective-0",
        "objective-1",
        "objective-2",
    ]
    assert [
        feature["geometry_status"] for feature in scenario.data["map_features"]
    ] == ["exact", "exact", "omitted_picture_budget"]
    assert "geometry" not in scenario.data["map_features"][2]
    assert scenario.data["map_feature_observation"]["truncated"] is True
    assert scenario.data["map_feature_observation"]["observed_row_count"] == 4
    assert picture.sources["MapDB.active"].details["feature_limit"] == 3
    assert (
        picture.sources["MapDB.active"].details[
            "total_geometry_coordinate_limit"
        ]
        == 4
    )
    assert "active-map-features-truncated" in picture.sections["warnings"].items
    pipeline = collections[("MapDB", "scenario_rma_demo_v1")].aggregate_calls[0][0]
    assert pipeline[2] == {"$limit": 4}


def test_active_map_failure_preserves_binding_and_marks_feature_facts_missing() -> None:
    provider, _, collections = _fixture()
    collections[("MapDB", "scenario_rma_demo_v1")] = FailingAggregateCollection([])

    picture = provider.read_operational_model()
    scenario = next(iter(picture.sections["scenario"].items.values()))

    assert scenario.data["map_collection"] == "scenario_rma_demo_v1"
    assert scenario.data["map_features"] == []
    assert scenario.data["map_feature_observation"]["freshness"] == "missing"
    assert scenario.freshness is Freshness.STALE
    assert picture.sources["MapDB.active"].freshness is Freshness.MISSING
    assert "source-unavailable:mapdb-active" in picture.sections["warnings"].items


def test_backend_only_mission_is_present_even_when_adapter_memory_is_empty() -> None:
    provider, runtime, _ = _fixture()
    runtime.missions.clear()

    picture = provider.read_operational_model()
    mission = picture.sections["missions"].items[MISSION_ID]

    assert "adapter_state" not in mission.data
    assert mission.data["backend_config"]["name"] == "Backend mission"
    assert mission.data["backend_feedback"]["status_name"] == "PLANNED"
    assert mission.data["effective_status_source"] == "RuntimeDB.MissionFeedback"


def test_failed_backend_command_is_explicit_without_exposing_response_body() -> None:
    provider, runtime, _ = _fixture()
    runtime.missions[MISSION_ID]["backend_rest"] = {
        "ok": False,
        "status_code": 503,
        "body": "large or sensitive upstream response",
    }
    runtime.missions[MISSION_ID]["command_phase"] = "start_failed"

    picture = provider.read_operational_model()
    mission = picture.sections["missions"].items[MISSION_ID]

    assert mission.data["adapter_state"]["backend_command"] == {
        "ok": False,
        "status_code": 503,
    }
    assert f"backend-command-failed:{MISSION_ID}" in picture.sections["warnings"].items
    assert "upstream response" not in json.dumps(picture.to_dict())


def test_stable_boundaries_make_unchanged_delta_empty_and_localize_status_change() -> None:
    provider, runtime, collections = _fixture()
    service = OperationalContextService(provider, runtime_id="test-runtime")
    initial = service.get_operational_update()
    assert initial.mode is UpdateMode.FULL

    unchanged = service.get_operational_update(
        initial.picture_revision, since_checksum=initial.picture_checksum
    )
    assert unchanged.mode is UpdateMode.DELTA
    assert unchanged.picture_revision == initial.picture_revision
    assert unchanged.picture_checksum == initial.picture_checksum
    assert unchanged.changed == {}
    assert unchanged.removed == ()

    runtime.missions[MISSION_ID]["status"] = 5
    runtime.missions[MISSION_ID]["status_name"] = "STARTED"
    collections[("RuntimeDB", "MissionFeedback")].rows[0]["Status"] = 5
    changed = service.get_operational_update(
        unchanged.picture_revision, since_checksum=unchanged.picture_checksum
    )

    assert changed.mode is UpdateMode.DELTA
    assert set(changed.changed) == {f"missions/{MISSION_ID}"}
    assert changed.removed == ()


def test_duplicate_connected_vehicle_rows_remain_visible_and_warn() -> None:
    provider, _, collections = _fixture()
    collections[("RuntimeDB", "ConnectedVehicles")].rows.append(
        {"agent_id": AGENT_ID.upper()}
    )

    picture = provider.read_operational_model()
    agent = picture.sections["agents"].items[AGENT_ID]
    source = picture.sources["RuntimeDB.ConnectedVehicles"]

    assert agent.data["connected"] is True
    assert agent.data["registration_count"] == 2
    assert source.details["bounded_rows"] == 2
    assert source.details["unique_agent_ids"] == 1
    assert source.details["duplicate_registrations"] == 1
    warning_id = f"duplicate-agent-registration:{AGENT_ID}"
    assert warning_id in picture.sections["warnings"].items
    assert "2 active" in picture.sections["warnings"].items[warning_id].data["message"]


def test_profile_failure_does_not_erase_known_connectivity() -> None:
    provider, _, collections = _fixture()
    collections[("VehicleDB", "Vehicles")] = FailingFindCollection([])

    picture = provider.read_operational_model()
    agent = picture.sections["agents"].items[AGENT_ID]

    assert agent.data["connected"] is True
    assert agent.data["registration_count"] == 1
    assert "advertised_profile" not in agent.data
    assert agent.freshness is Freshness.STALE
    assert picture.sources["RuntimeDB.ConnectedVehicles"].freshness is Freshness.FRESH
    assert picture.sources["VehicleDB.Vehicles"].freshness is Freshness.MISSING
    assert "agents-not-registered" not in picture.sections["warnings"].items


def test_invalid_newer_feedback_candidates_fall_back_to_bounded_valid_summary() -> None:
    provider, _, collections = _fixture()
    feedback_rows = collections[("RuntimeDB", "MissionFeedback")].rows
    feedback_rows[:0] = [
        {
            "_id": "feedback-invalid-status",
            "MissionId": LEGACY_MISSION_ID,
            "Behavior": 0,
            "Status": 999,
            "RequestedStatus": 0,
            "Issue": 0,
            "Date": "2026-08-22T10:02:00Z",
            "Tasks": [
                {
                    "VehicleId": AGENT_ID,
                    "Waypoints": [{"Coordinates": [91.2345, 12.3456]}],
                }
            ],
        },
        {
            "_id": "feedback-invalid-tasks",
            "mission_id": LEGACY_MISSION_ID,
            "behavior": 0,
            "status": 5,
            "requested_status": 2,
            "issue": 0,
            "date": "2026-08-22T10:01:00Z",
            "tasks_shape_valid": False,
            "task_count": 1,
            "tasks_truncated": False,
            "task_summaries": [
                {"agent_id": AGENT_ID, "waypoint_count": 1}
            ],
        },
    ]

    picture = provider.read_operational_model()
    feedback = picture.sections["missions"].items[MISSION_ID].data[
        "backend_feedback"
    ]

    assert feedback["document_id"] == "feedback-1"
    assert feedback["status_name"] == "PLANNED"
    assert feedback["skipped_newer_invalid_candidates"] == 2
    warning_id = f"invalid-newer-feedback:{MISSION_ID}"
    assert warning_id in picture.sections["warnings"].items
    encoded = json.dumps(picture.to_dict())
    assert "91.2345" not in encoded
    assert "12.3456" not in encoded


def test_mongo_failure_keeps_adapter_fact_but_marks_backend_sources_missing() -> None:
    provider, runtime, _ = _fixture()

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise ServerSelectionTimeoutError("backend unavailable")

    provider = LiveOperationalReadModelProvider(
        runtime,
        Scenario(),
        "mongodb://unused",
        mongo_client_factory=unavailable,
    )
    picture = provider.read_operational_model()

    assert picture.sections["missions"].items[MISSION_ID].freshness is Freshness.STALE
    assert (
        picture.sources["RuntimeDB.MissionFeedback"].freshness
        is Freshness.MISSING
    )
    assert "source-unavailable:runtimedb-missionfeedback" in picture.sections[
        "warnings"
    ].items


def test_mongo_failure_redacts_uri_credentials_from_operational_warnings() -> None:
    _, runtime, _ = _fixture()

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise ServerSelectionTimeoutError(
            "could not connect to mongodb://operator:super-secret@mongo.internal:27017"
        )

    provider = LiveOperationalReadModelProvider(
        runtime,
        Scenario(),
        "mongodb://unused",
        mongo_client_factory=unavailable,
    )
    picture = provider.read_operational_model()
    encoded = json.dumps(picture.to_dict())

    assert "super-secret" not in encoded
    assert "mongodb://<redacted>@mongo.internal:27017" in encoded
