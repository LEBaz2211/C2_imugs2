from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import c2_imugs2.worlds.service as world_service
from c2_imugs2.migrations.world_domain_v1 import apply_migration
from c2_imugs2.worlds.service import WorldConflictError, WorldManager


ROOT = Path(__file__).resolve().parents[1]
ROAD_ID = "60bae762-6c7a-4b11-8803-556fdfee4425"


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        if key == "road_imports.import_id":
            actual = [item.get("import_id") for item in document.get("road_imports") or []]
        else:
            actual = document.get(key)
        if isinstance(expected, dict) and "$ne" in expected:
            if actual == expected["$ne"]:
                return False
        elif isinstance(actual, list) and not isinstance(expected, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


def _project(document: dict[str, Any], projection: dict[str, int] | None) -> dict[str, Any]:
    value = deepcopy(document)
    if not projection:
        return value
    included = [key for key, enabled in projection.items() if enabled and key != "_id"]
    if included:
        return {key: deepcopy(value[key]) for key in included if key in value}
    for key, enabled in projection.items():
        if not enabled:
            value.pop(key, None)
    return value


class MemoryCursor(list[dict[str, Any]]):
    def sort(self, key: str, direction: int) -> "MemoryCursor":
        reverse = direction < 0
        super().sort(key=lambda item: item.get(key) or "", reverse=reverse)
        return self


class MemoryCollection:
    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []

    def find_one(
        self,
        query: dict[str, Any],
        projection: dict[str, int] | None = None,
    ) -> dict[str, Any] | None:
        return next(
            (_project(item, projection) for item in self.documents if _matches(item, query)),
            None,
        )

    def find(
        self,
        query: dict[str, Any] | None = None,
        projection: dict[str, int] | None = None,
    ) -> MemoryCursor:
        return MemoryCursor(
            [_project(item, projection) for item in self.documents if _matches(item, query or {})]
        )

    def insert_one(self, document: dict[str, Any]) -> SimpleNamespace:
        self.documents.append(deepcopy(document))
        return SimpleNamespace(inserted_id=len(self.documents))

    def insert_many(self, documents: list[dict[str, Any]]) -> SimpleNamespace:
        self.documents.extend(deepcopy(documents))
        return SimpleNamespace(inserted_ids=list(range(len(documents))))

    def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> SimpleNamespace:
        for document in self.documents:
            if not _matches(document, query):
                continue
            before = deepcopy(document)
            document.update(deepcopy(update.get("$set") or {}))
            for key, value in (update.get("$inc") or {}).items():
                document[key] = document.get(key, 0) + value
            for key, value in (update.get("$push") or {}).items():
                document.setdefault(key, []).append(deepcopy(value))
            for key, value in (update.get("$pull") or {}).items():
                document[key] = [item for item in document.get(key) or [] if not _matches(item, value)]
            return SimpleNamespace(matched_count=1, modified_count=int(document != before), upserted_id=None)
        if upsert:
            document = {
                **deepcopy(query),
                **deepcopy(update.get("$setOnInsert") or {}),
                **deepcopy(update.get("$set") or {}),
            }
            self.documents.append(document)
            return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=len(self.documents))
        return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

    def delete_one(self, query: dict[str, Any]) -> SimpleNamespace:
        for index, document in enumerate(self.documents):
            if _matches(document, query):
                self.documents.pop(index)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def delete_many(self, query: dict[str, Any]) -> SimpleNamespace:
        before = len(self.documents)
        self.documents = [item for item in self.documents if not _matches(item, query)]
        return SimpleNamespace(deleted_count=before - len(self.documents))

    def replace_one(
        self,
        query: dict[str, Any],
        replacement: dict[str, Any],
        upsert: bool = False,
    ) -> SimpleNamespace:
        for index, document in enumerate(self.documents):
            if _matches(document, query):
                self.documents[index] = deepcopy(replacement)
                return SimpleNamespace(matched_count=1, modified_count=1, upserted_id=None)
        if upsert:
            self.documents.append(deepcopy(replacement))
            return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=len(self.documents))
        return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

    def count_documents(self, query: dict[str, Any]) -> int:
        return sum(_matches(item, query) for item in self.documents)


class MemoryDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, MemoryCollection] = {}

    def __getitem__(self, collection: str) -> MemoryCollection:
        return self.collections.setdefault(collection, MemoryCollection())

    def list_collection_names(self) -> list[str]:
        return list(self.collections)


class MemoryClient:
    def __init__(self) -> None:
        self.databases: dict[str, MemoryDatabase] = {}
        self.admin = SimpleNamespace(command=lambda name: {"ok": 1})

    def __enter__(self) -> "MemoryClient":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def __getitem__(self, database: str) -> MemoryDatabase:
        return self.databases.setdefault(database, MemoryDatabase())


def _manager(client: MemoryClient) -> WorldManager:
    manager = WorldManager(ROOT, ROOT, "mongodb://memory", docker_socket="/missing")
    manager._client = lambda: client  # type: ignore[method-assign]
    return manager


def _definition(name: str = "World A") -> dict[str, Any]:
    return {
        "name": name,
        "map": "rma",
        "notes": "",
        "feature_ids": [ROAD_ID],
        "agents": [
            {
                "agent_id": "robot-a",
                "name": "Robot A",
                "vehicle_type": "UGV",
                "current_location": [4.39, 50.84],
            }
        ],
        "map_view": {"center": [4.39, 50.84], "zoom": 15},
    }


def test_world_definition_crud_uses_server_ids_and_revision_compare_and_swap() -> None:
    client = MemoryClient()
    manager = _manager(client)

    created = manager.create_world(_definition())
    assert created["world_id"].startswith("world-")
    assert created["revision"] == 1

    updated = manager.update_world(
        created["world_id"],
        {**_definition("World A edited"), "revision": 1},
    )
    assert updated["revision"] == 2
    assert updated["name"] == "World A edited"

    with pytest.raises(WorldConflictError) as conflict:
        manager.update_world(created["world_id"], {**_definition("stale"), "revision": 1})
    assert conflict.value.current and conflict.value.current["revision"] == 2
    assert manager.list_worlds()[0]["world_id"] == created["world_id"]

    assert manager.delete_world(created["world_id"])["deleted"] is True
    assert manager.list_worlds() == []


def test_authoring_feature_delete_can_detach_from_its_acknowledged_world() -> None:
    client = MemoryClient()
    manager = _manager(client)
    feature_id = "workspace-a"
    client["MapDB"]["AuthoringFeatures"].insert_one(
        {
            "map": "rma",
            "feature_id": feature_id,
            "feature": {
                "type": "Feature",
                "id": feature_id,
                "properties": {
                    "feature_id": feature_id,
                    "feature_type": "workspace",
                    "source": "authoring",
                    "map": "rma",
                },
                "geometry": {"type": "Polygon", "coordinates": []},
            },
        }
    )
    created = manager.create_world({**_definition(), "feature_ids": [ROAD_ID, feature_id]})

    with pytest.raises(WorldConflictError, match="attached to a world definition"):
        manager.delete_authoring_feature("rma", feature_id)

    deleted = manager.delete_authoring_feature(
        "rma",
        feature_id,
        world_id=created["world_id"],
        revision=created["revision"],
    )

    assert deleted["deleted"] is True
    assert deleted["world"]["feature_ids"] == [ROAD_ID]
    assert deleted["world"]["revision"] == 2
    assert client["MapDB"]["AuthoringFeatures"].count_documents(
        {"map": "rma", "feature_id": feature_id}
    ) == 0


def test_active_hydration_never_joins_foreign_deployment_overlays() -> None:
    client = MemoryClient()
    manager = _manager(client)
    snapshot = client["MapDB"]["snapshot-a"]
    snapshot.insert_one({
        "type": "Feature",
        "id": "risk-a",
        "properties": {"feature_id": "risk-a", "feature_type": "risk"},
        "geometry": {"type": "Polygon", "coordinates": []},
    })
    live = client["WorldDB"]["LiveFeatures"]
    for deployment_id, feature_id in (("deployment-a", "objective-a"), ("deployment-b", "objective-b")):
        live.insert_one({
            "deployment_id": deployment_id,
            "feature_id": feature_id,
            "feature": {
                "type": "Feature",
                "id": feature_id,
                "properties": {"feature_id": feature_id, "deployment_id": deployment_id},
                "geometry": {"type": "Point", "coordinates": [4, 50]},
            },
        })

    hydrated = manager._hydrate_active({  # noqa: SLF001
        "world_id": "world-a",
        "world_version": "version-a",
        "deployment_id": "deployment-a",
        "launch_id": "launch-a",
        "map_collection": "snapshot-a",
        "map_snapshot_token": "token-a",
        "status": "stale",
        "ready": False,
    })

    assert [item["id"] for item in hydrated["snapshot"]["features"]] == ["risk-a"]
    assert [item["id"] for item in hydrated["live_features"]["features"]] == ["objective-a"]


def test_live_features_are_bound_to_the_current_deployment() -> None:
    client = MemoryClient()
    manager = _manager(client)
    active = {"world_id": "world-a", "deployment_id": "deployment-a"}
    manager.active = lambda: active  # type: ignore[method-assign]
    payload = {
        "type": "Feature",
        "properties": {"feature_id": "live-a", "feature_type": "objective", "name": "Live A"},
        "geometry": {"type": "Point", "coordinates": [4.1, 50.1]},
    }

    created = manager.create_live_feature(payload)
    stored = client["WorldDB"]["LiveFeatures"].documents[0]
    assert created["properties"]["deployment_id"] == "deployment-a"
    assert stored["deployment_id"] == "deployment-a"

    manager.active = lambda: {"world_id": "world-b", "deployment_id": "deployment-b"}  # type: ignore[method-assign]
    with pytest.raises(KeyError):
        manager.update_live_feature("live-a", payload)
    with pytest.raises(KeyError):
        manager.delete_live_feature("live-a")


def test_world_road_import_and_vehicle_model_state_are_durable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MemoryClient()
    manager = _manager(client)
    created = manager.create_world(_definition())
    monkeypatch.setattr(
        world_service,
        "query_osm_roads_for_bbox",
        lambda repo_root, map_name, bbox: {
            "bbox": list(bbox),
            "geojson": {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "id": "road-imported",
                    "properties": {"name": "Imported"},
                    "geometry": {"type": "LineString", "coordinates": [[4, 50], [4.1, 50.1]]},
                }],
            },
        },
    )

    imported = manager.query_road_import(
        created["world_id"],
        {"revision": 1, "bbox": [4, 50, 4.1, 50.1]},
    )
    assert imported["world"]["revision"] == 2
    assert imported["road_import"]["geojson"]["features"][0]["id"] == "road-imported"
    import_id = imported["road_import"]["import_id"]
    assert manager.get_road_import(created["world_id"], import_id)["feature_count"] == 1
    assert manager.delete_road_import(created["world_id"], import_id, 2)["revision"] == 3

    model = manager.create_vehicle_model({
        "label": "Scout",
        "vehicle_type": "UGV",
        "constraints": {"max_speed": 3},
        "capabilities": ["camera"],
    })
    assert manager.list_vehicle_models()[0]["model_id"] == model["model_id"]
    updated = manager.update_vehicle_model(model["model_id"], {**model, "label": "Scout 2"})
    assert updated["revision"] == 2
    assert manager.delete_vehicle_model(model["model_id"])["deleted"] is True


def test_world_domain_migration_is_idempotent_and_verifies_active_only_snapshot(
    tmp_path: Path,
) -> None:
    fixture = json.loads(
        (ROOT / "tests" / "fixtures" / "world_domain_v1_mongo.json").read_text(encoding="utf-8")
    )
    client = MemoryClient()
    for database_name, collections in fixture["databases"].items():
        for collection_name, documents in collections.items():
            client[database_name][collection_name].documents = deepcopy(documents)
    source_counts = {
        (database_name, collection_name): len(documents)
        for database_name, collections in fixture["databases"].items()
        for collection_name, documents in collections.items()
    }
    backup_marker = tmp_path / "BACKUP_COMPLETE.json"
    backup_marker.write_text("{}", encoding="utf-8")

    first = apply_migration(
        "mongodb://memory",
        tmp_path,
        backup_marker=backup_marker,
        client_factory=lambda *args, **kwargs: client,
    )
    second = apply_migration(
        "mongodb://memory",
        tmp_path,
        backup_marker=backup_marker,
        client_factory=lambda *args, **kwargs: client,
    )

    assert first["status"] == "complete"
    assert first["deduplicated_snapshots"] == 2
    assert second["idempotent_reuse"] is True
    active = client["WorldDB"]["ActiveWorld"].documents[0]
    assert active["map_collection"].startswith("snapshot_")
    assert client["MapDB"][active["map_collection"]].count_documents({}) == 1
    assert all(field not in active for field in fixture["retired_fields"])
    definition = client["WorldDB"]["WorldDefinitions"].documents[0]
    assert definition["road_imports"][0]["import_id"] == "import-a"
    migrated_road = client["WorldDB"]["WorldRoadFeatures"].documents[0]["feature"]
    assert migrated_road["properties"]["world_road_import_id"] == "import-a"
    assert migrated_road["properties"]["source_tool"] == "world_builder_osm_polygon"
    assert "scenario_road_import_id" not in migrated_road["properties"]
    migrated_launch = client["WorldDB"]["WorldLaunches"].documents[0]
    assert migrated_launch["map_collection"].startswith("snapshot_")
    assert migrated_launch["launch_id"] == "launch-alpha"
    assert migrated_launch["containers"] == []
    assert "scenario" not in json.dumps(migrated_launch).lower()
    assert "activation" not in json.dumps(migrated_launch).lower()
    for (database_name, collection_name), count in source_counts.items():
        assert client[database_name][collection_name].count_documents({}) == count
