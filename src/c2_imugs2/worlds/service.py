from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time
from typing import Any
import uuid

try:
    from pymongo import MongoClient
    from pymongo.errors import DuplicateKeyError, PyMongoError
except ImportError:  # Keep pure snapshot construction usable in lightweight test environments.
    MongoClient = None  # type: ignore[assignment,misc]

    class PyMongoError(Exception):
        pass

    class DuplicateKeyError(PyMongoError):
        pass

from ..infrastructure.legacy.map import (
    load_static_geojson_map,
    normalize_user_geojson_feature,
    query_osm_roads_for_bbox,
    query_osm_roads_for_polygon,
)
from ..infrastructure.mongo import MongoIndexManager, map_feature_index_specs
from ..runtime.deployment import _docker_request, launch_deployment


PLANNER_CONTAINER = "c2-imugs2-backend-planner"
COORDINATION_CONTAINER = "c2-imugs2-backend-centralized-coordination"
C2_REST_CONTAINER = "c2-imugs2-backend-c2-ros-rest"
ROSBRIDGE_CONTAINER = "c2-imugs2-backend-rosbridge"
DEFAULT_EDGE_CONTAINER = "c2-imugs2-backend-edge-agent-sim-1"
ACTIVE_STATE_FILE = "active_world.json"
PLANNER_CONFIG_FILE = "active_planner.yaml"
WORLD_DATABASE = "WorldDB"
DEFINITIONS_COLLECTION = "WorldDefinitions"
VERSIONS_COLLECTION = "WorldVersions"
LAUNCHES_COLLECTION = "WorldLaunches"
ACTIVE_WORLD_COLLECTION = "ActiveWorld"
ROAD_FEATURES_COLLECTION = "WorldRoadFeatures"
LIVE_FEATURES_COLLECTION = "LiveFeatures"
AUTHORING_FEATURES_COLLECTION = "AuthoringFeatures"
VEHICLE_MODELS_COLLECTION = "VehicleModels"
WORLD_STATE_SCHEMA_VERSION = "2.0"


class WorldNotReadyError(RuntimeError):
    pass


class WorldNotFoundError(KeyError):
    pass


class WorldConflictError(RuntimeError):
    def __init__(self, message: str, current: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.current = current


@dataclass(frozen=True)
class _DurableActiveLookup:
    """Tri-state read of the MongoDB active-world singleton."""

    reachable: bool
    state: dict[str, Any] | None = None
    error: str | None = None


def build_world_snapshot(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    authoring_features: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the exact, frozen GeoJSON input that one planner process will use."""
    world_id = _required_text(payload.get("world_id"), "world_id")
    map_name = _required_text(payload.get("map") or "rma", "map")
    agents = payload.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("world launch requires at least one vehicle")

    base_features = (
        deepcopy(authoring_features)
        if authoring_features is not None
        else load_static_geojson_map(repo_root, map_name).get("features", [])
    )
    feature_ids = payload.get("feature_ids") or []
    if not isinstance(feature_ids, list) or any(not isinstance(item, str) for item in feature_ids):
        raise ValueError("feature_ids must be a list of strings")
    available = {
        str((feature.get("properties") or {}).get("feature_id") or feature.get("id")): feature
        for feature in base_features
    }
    missing = sorted(set(feature_ids) - set(available))
    if missing:
        raise ValueError(f"world references unknown map feature ids: {', '.join(missing)}")

    features: list[dict[str, Any]] = [deepcopy(available[feature_id]) for feature_id in feature_ids]
    for import_index, road_import in enumerate(payload.get("road_imports") or []):
        if not isinstance(road_import, dict):
            raise ValueError("road_imports entries must be objects")
        import_id = _safe_name(str(road_import.get("import_id") or f"roads-{import_index + 1}"))
        geojson = road_import.get("geojson")
        if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection":
            raise ValueError(f"road import {import_id} must contain a GeoJSON FeatureCollection")
        for road_index, source in enumerate(geojson.get("features") or []):
            if not isinstance(source, dict) or (source.get("geometry") or {}).get("type") != "LineString":
                continue
            road = deepcopy(source)
            properties = dict(road.get("properties") or {})
            source_id = str(properties.get("feature_id") or road.get("id") or road_index)
            migrated_frozen_feature = (
                properties.get("source") == "frozen_openstreetmap"
                and properties.get("world_road_import_id") == import_id
                and bool(source_id)
            )
            feature_id = (
                source_id
                if migrated_frozen_feature
                else f"osm-{import_id}-{_safe_name(source_id)}-{road_index}"
            )
            properties.update(
                {
                    "feature_id": feature_id,
                    "feature_type": "road",
                    "name": properties.get("name") or f"OSM road {road_index + 1}",
                    "source": "frozen_openstreetmap",
                    "world_road_import_id": import_id,
                }
            )
            road["id"] = feature_id
            road["properties"] = properties
            features.append(road)

    seen: set[str] = set()
    unique_features = []
    for feature in features:
        feature_id = str((feature.get("properties") or {}).get("feature_id") or feature.get("id"))
        if feature_id in seen:
            continue
        seen.add(feature_id)
        unique_features.append(feature)

    road_count = sum(
        1
        for feature in unique_features
        if (feature.get("properties") or {}).get("feature_type") == "road"
        and (feature.get("geometry") or {}).get("type") == "LineString"
    )
    if road_count == 0:
        raise ValueError("world must contain at least one selected or downloaded road LineString")

    canonical_payload = {
        "world_id": world_id,
        "name": str(payload.get("name") or world_id),
        "map": map_name,
        "notes": str(payload.get("notes") or ""),
        "agents": agents,
        "feature_ids": feature_ids,
        "road_imports": payload.get("road_imports") or [],
        "map_view": deepcopy(payload.get("map_view")),
    }
    digest = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    version = digest[:16]
    feature_hash = _feature_content_hash(unique_features)
    collection = f"snapshot_{feature_hash[:32]}"
    return {
        "world_id": world_id,
        "name": canonical_payload["name"],
        "map": map_name,
        "notes": canonical_payload["notes"],
        "world_version": version,
        "content_hash": digest,
        "map_collection": collection,
        "feature_count": len(unique_features),
        "road_count": road_count,
        "map_feature_hash": feature_hash,
        "feature_ids": deepcopy(feature_ids),
        "features": unique_features,
        "agents": deepcopy(agents),
        "map_view": deepcopy(canonical_payload["map_view"]),
    }


class WorldManager:
    def __init__(
        self,
        repo_root: Path,
        host_repo_root: Path,
        mongodb_url: str,
        docker_socket: str = "/var/run/docker.sock",
        readiness_timeout: float = 45.0,
    ) -> None:
        self.repo_root = repo_root
        self.host_repo_root = host_repo_root
        self.mongodb_url = mongodb_url
        self.docker_socket = docker_socket
        self.readiness_timeout = readiness_timeout
        self._lock = threading.Lock()

    # World authoring is durable and revisioned.  Runtime launch methods below
    # consume a saved definition; callers cannot launch an arbitrary payload.
    def list_worlds(self) -> list[dict[str, Any]]:
        with self._client() as client:
            active = client[WORLD_DATABASE][ACTIVE_WORLD_COLLECTION].find_one(
                {"singleton": "active"}, {"_id": 0, "singleton": 0}
            ) or {}
            documents = list(
                client[WORLD_DATABASE][DEFINITIONS_COLLECTION]
                .find({"archived": {"$ne": True}}, {"_id": 0})
                .sort("updated_at", -1)
            )
            worlds = []
            for item in documents:
                hydrated = self._hydrate_definition(client, item)
                is_active = hydrated.get("world_id") == active.get("world_id")
                hydrated.update(
                    {
                        "runtime_active": is_active,
                        "runtime_status": active.get("status") if is_active else "saved",
                        "map_collection": active.get("map_collection") if is_active else None,
                    }
                )
                worlds.append(hydrated)
            return worlds

    def get_world(self, world_id: str) -> dict[str, Any]:
        with self._client() as client:
            document = client[WORLD_DATABASE][DEFINITIONS_COLLECTION].find_one(
                {"world_id": world_id, "archived": {"$ne": True}}, {"_id": 0}
            )
            if not document:
                raise WorldNotFoundError(world_id)
            return self._hydrate_definition(client, document)

    def create_world(self, payload: dict[str, Any]) -> dict[str, Any]:
        world_id = f"world-{uuid.uuid4().hex}"
        now = _utc_now()
        document = _validated_definition(payload, world_id=world_id)
        self._validate_authoring_membership(document)
        document.update(
            {
                "revision": 1,
                "created_at": now,
                "updated_at": now,
                "archived": False,
                "road_imports": [],
            }
        )
        with self._client() as client:
            client[WORLD_DATABASE][DEFINITIONS_COLLECTION].insert_one(deepcopy(document))
        return document

    def update_world(self, world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        expected_revision = _required_revision(payload)
        with self._client() as client:
            definitions = client[WORLD_DATABASE][DEFINITIONS_COLLECTION]
            current = definitions.find_one(
                {"world_id": world_id, "archived": {"$ne": True}}, {"_id": 0}
            )
            if not current:
                raise WorldNotFoundError(world_id)
            merged = {
                key: deepcopy(payload.get(key, current.get(key)))
                for key in ("name", "map", "notes", "feature_ids", "agents", "map_view")
            }
            validated = _validated_definition(merged, world_id=world_id)
            self._validate_authoring_membership(validated)
            update = {
                **validated,
                "updated_at": _utc_now(),
            }
            result = definitions.update_one(
                {
                    "world_id": world_id,
                    "revision": expected_revision,
                    "archived": {"$ne": True},
                },
                {"$set": update, "$inc": {"revision": 1}},
            )
            if result.modified_count != 1:
                latest = definitions.find_one({"world_id": world_id}, {"_id": 0})
                raise WorldConflictError(
                    "world definition revision conflict", self._hydrate_definition(client, latest) if latest else None
                )
            saved = definitions.find_one({"world_id": world_id}, {"_id": 0})
            return self._hydrate_definition(client, saved)

    def delete_world(self, world_id: str) -> dict[str, Any]:
        with self._client() as client:
            active = client[WORLD_DATABASE][ACTIVE_WORLD_COLLECTION].find_one(
                {"singleton": "active", "world_id": world_id}, {"_id": 0}
            )
            if active:
                raise WorldConflictError("the active world cannot be deleted")
            result = client[WORLD_DATABASE][DEFINITIONS_COLLECTION].update_one(
                {"world_id": world_id, "archived": {"$ne": True}},
                {"$set": {"archived": True, "updated_at": _utc_now()}},
            )
            if result.modified_count != 1:
                raise WorldNotFoundError(world_id)
        return {"world_id": world_id, "deleted": True}

    def query_road_import(self, world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        expected_revision = _required_revision(payload)
        definition = self.get_world(world_id)
        if definition["revision"] != expected_revision:
            raise WorldConflictError("world definition revision conflict", definition)
        if isinstance(payload.get("polygon"), list):
            result = query_osm_roads_for_polygon(
                self.repo_root, definition["map"], payload["polygon"]
            )
        elif isinstance(payload.get("bbox"), list) and len(payload["bbox"]) == 4:
            result = query_osm_roads_for_bbox(
                self.repo_root,
                definition["map"],
                tuple(float(value) for value in payload["bbox"]),
            )
        else:
            raise ValueError("road import query requires polygon or bbox")
        import_id = f"roads-{uuid.uuid4().hex[:12]}"
        features = deepcopy((result.get("geojson") or {}).get("features") or result.get("features") or [])
        now = _utc_now()
        metadata = {
            "import_id": import_id,
            "name": str(payload.get("name") or f"OSM roads {import_id[-6:]}"),
            "bbox": deepcopy(result.get("bbox") or payload.get("bbox") or _feature_bbox(features)),
            "feature_count": len(features),
            "created_at": now,
        }
        with self._client() as client:
            roads = client[WORLD_DATABASE][ROAD_FEATURES_COLLECTION]
            if features:
                roads.insert_many(
                    [
                        {
                            "world_id": world_id,
                            "import_id": import_id,
                            "feature_index": index,
                            "feature": feature,
                        }
                        for index, feature in enumerate(features)
                    ]
                )
            definitions = client[WORLD_DATABASE][DEFINITIONS_COLLECTION]
            updated = definitions.update_one(
                {"world_id": world_id, "revision": expected_revision, "archived": {"$ne": True}},
                {
                    "$push": {"road_imports": metadata},
                    "$set": {"updated_at": now},
                    "$inc": {"revision": 1},
                },
            )
            if updated.modified_count != 1:
                roads.delete_many({"world_id": world_id, "import_id": import_id})
                latest = definitions.find_one({"world_id": world_id}, {"_id": 0})
                raise WorldConflictError("world definition revision conflict", latest)
            saved = definitions.find_one({"world_id": world_id}, {"_id": 0})
            return {
                "road_import": self._hydrate_road_import(client, world_id, metadata),
                "world": self._hydrate_definition(client, saved),
            }

    def get_road_import(self, world_id: str, import_id: str) -> dict[str, Any]:
        definition = self.get_world(world_id)
        metadata = next(
            (item for item in definition.get("road_imports", []) if item.get("import_id") == import_id),
            None,
        )
        if not metadata:
            raise WorldNotFoundError(import_id)
        return metadata

    def delete_road_import(self, world_id: str, import_id: str, revision: int) -> dict[str, Any]:
        with self._client() as client:
            definitions = client[WORLD_DATABASE][DEFINITIONS_COLLECTION]
            updated = definitions.update_one(
                {
                    "world_id": world_id,
                    "revision": revision,
                    "road_imports.import_id": import_id,
                    "archived": {"$ne": True},
                },
                {
                    "$pull": {"road_imports": {"import_id": import_id}},
                    "$set": {"updated_at": _utc_now()},
                    "$inc": {"revision": 1},
                },
            )
            if updated.modified_count != 1:
                latest = definitions.find_one({"world_id": world_id}, {"_id": 0})
                if not latest:
                    raise WorldNotFoundError(world_id)
                raise WorldConflictError("world definition revision conflict or road import not found", latest)
            client[WORLD_DATABASE][ROAD_FEATURES_COLLECTION].delete_many(
                {"world_id": world_id, "import_id": import_id}
            )
            saved = definitions.find_one({"world_id": world_id}, {"_id": 0})
            return self._hydrate_definition(client, saved)

    def list_vehicle_models(self) -> list[dict[str, Any]]:
        with self._client() as client:
            return list(
                client["VehicleDB"][VEHICLE_MODELS_COLLECTION]
                .find({}, {"_id": 0})
                .sort("updated_at", -1)
            )

    def create_vehicle_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        model_id = f"vehicle-model-{uuid.uuid4().hex}"
        model = _validated_vehicle_model(payload, model_id)
        now = _utc_now()
        model.update({"revision": 1, "created_at": now, "updated_at": now})
        with self._client() as client:
            client["VehicleDB"][VEHICLE_MODELS_COLLECTION].insert_one(deepcopy(model))
        return model

    def update_vehicle_model(self, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        revision = _required_revision(payload)
        model = _validated_vehicle_model(payload, model_id)
        with self._client() as client:
            collection = client["VehicleDB"][VEHICLE_MODELS_COLLECTION]
            result = collection.update_one(
                {"model_id": model_id, "revision": revision},
                {"$set": {**model, "updated_at": _utc_now()}, "$inc": {"revision": 1}},
            )
            if result.modified_count != 1:
                current = collection.find_one({"model_id": model_id}, {"_id": 0})
                if not current:
                    raise WorldNotFoundError(model_id)
                raise WorldConflictError("vehicle model revision conflict", current)
            return collection.find_one({"model_id": model_id}, {"_id": 0})

    def delete_vehicle_model(self, model_id: str) -> dict[str, Any]:
        with self._client() as client:
            result = client["VehicleDB"][VEHICLE_MODELS_COLLECTION].delete_one({"model_id": model_id})
            if result.deleted_count != 1:
                raise WorldNotFoundError(model_id)
        return {"model_id": model_id, "deleted": True}

    def create_live_feature(self, payload: dict[str, Any]) -> dict[str, Any]:
        active = self._require_authoritative_active()
        feature = normalize_user_geojson_feature(payload)
        properties = dict(feature["properties"])
        properties.update(
            {
                "source": "live_overlay",
                "deployment_id": active["deployment_id"],
                "world_id": active["world_id"],
            }
        )
        feature["properties"] = properties
        document = {
            "deployment_id": active["deployment_id"],
            "world_id": active["world_id"],
            "feature_id": properties["feature_id"],
            "feature": feature,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        with self._client() as client:
            try:
                client[WORLD_DATABASE][LIVE_FEATURES_COLLECTION].insert_one(deepcopy(document))
            except DuplicateKeyError as exc:
                raise WorldConflictError(
                    "a live feature with this ID already exists in the active deployment"
                ) from exc
        return feature

    def update_live_feature(self, feature_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        active = self._require_authoritative_active()
        feature = normalize_user_geojson_feature(payload)
        feature["id"] = feature_id
        feature["properties"].update(
            {
                "feature_id": feature_id,
                "source": "live_overlay",
                "deployment_id": active["deployment_id"],
                "world_id": active["world_id"],
            }
        )
        with self._client() as client:
            result = client[WORLD_DATABASE][LIVE_FEATURES_COLLECTION].update_one(
                {"deployment_id": active["deployment_id"], "feature_id": feature_id},
                {"$set": {"feature": feature, "updated_at": _utc_now()}},
            )
            if result.matched_count != 1:
                raise WorldNotFoundError(feature_id)
        return feature

    def delete_live_feature(self, feature_id: str) -> dict[str, Any]:
        active = self._require_authoritative_active()
        with self._client() as client:
            result = client[WORLD_DATABASE][LIVE_FEATURES_COLLECTION].delete_one(
                {"deployment_id": active["deployment_id"], "feature_id": feature_id}
            )
            if result.deleted_count != 1:
                raise WorldNotFoundError(feature_id)
        return {"feature_id": feature_id, "deleted": True}

    def _client(self):
        if MongoClient is None:
            raise RuntimeError("pymongo is required for world storage")
        client = MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000)
        try:
            client.admin.command("ping")
        except PyMongoError as exc:
            client.close()
            raise RuntimeError(f"world storage is unavailable: {exc}") from exc
        return client

    def _hydrate_definition(self, client: Any, document: dict[str, Any]) -> dict[str, Any]:
        hydrated = deepcopy(document)
        hydrated["road_imports"] = [
            self._hydrate_road_import(client, hydrated["world_id"], metadata)
            for metadata in hydrated.get("road_imports") or []
        ]
        return hydrated

    @staticmethod
    def _hydrate_road_import(client: Any, world_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        import_id = str(metadata.get("import_id") or "")
        rows = list(
            client[WORLD_DATABASE][ROAD_FEATURES_COLLECTION]
            .find({"world_id": world_id, "import_id": import_id}, {"_id": 0, "feature": 1, "feature_index": 1})
            .sort("feature_index", 1)
        )
        return {
            **deepcopy(metadata),
            "geojson": {"type": "FeatureCollection", "features": [row["feature"] for row in rows]},
        }

    def active(self) -> dict[str, Any] | None:
        """Load durable active state, using the file cache for diagnostics only.

        MongoDB is the production authority.  The JSON file is retained as a
        generated cache so an unavailable database can still produce a useful
        stale/failed diagnostic, but it must never be sufficient proof of
        readiness by itself.
        """
        lookup = self._active_from_mongo()
        if lookup.reachable:
            if lookup.state is not None:
                hydrated = self._hydrate_active(lookup.state)
                self._save_state(hydrated)
                return hydrated
            # A successful authoritative read with no singleton means there is
            # no active world.  A stale local file must not override that.
            return None

        cached = self._cached_active()
        detail = lookup.error or "MongoDB active-world authority is unavailable"
        if not cached:
            return {
                "status": "unavailable",
                "ready": False,
                "durable_authority": "unavailable",
                "cache_diagnostic_only": True,
                "error": detail,
            }
        diagnostic = deepcopy(cached)
        diagnostic.update(
            {
                "status": "stale",
                "ready": False,
                "durable_authority": "unavailable",
                "cache_diagnostic_only": True,
                "cached_status": cached.get("status"),
                "error": f"active world authority is unavailable: {detail}",
            }
        )
        return diagnostic

    def _cached_active(self) -> dict[str, Any] | None:
        path = self.repo_root / "data" / "runtime" / ACTIVE_STATE_FILE
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _active_from_mongo(self) -> _DurableActiveLookup:
        if MongoClient is None:
            return _DurableActiveLookup(False, error="pymongo is not installed")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=300) as client:
                client.admin.command("ping")
                value = client[WORLD_DATABASE][ACTIVE_WORLD_COLLECTION].find_one(
                    {"singleton": "active"},
                    {"_id": 0, "singleton": 0},
                )
        except PyMongoError as exc:
            return _DurableActiveLookup(False, error=str(exc))
        return _DurableActiveLookup(
            True, state=value if isinstance(value, dict) else None
        )

    def _hydrate_active(self, state: dict[str, Any]) -> dict[str, Any]:
        hydrated = deepcopy(state)
        collection_name = str(hydrated.get("map_collection") or "")
        deployment_id = str(hydrated.get("deployment_id") or "")
        if not collection_name or not deployment_id:
            hydrated["snapshot"] = {"type": "FeatureCollection", "features": []}
            hydrated["live_features"] = {"type": "FeatureCollection", "features": []}
            return hydrated
        try:
            with self._client() as client:
                snapshot_features = list(
                    client["MapDB"][collection_name].find({}, {"_id": 0})
                )
                live_documents = list(
                    client[WORLD_DATABASE][LIVE_FEATURES_COLLECTION].find(
                        {"deployment_id": deployment_id}, {"_id": 0, "feature": 1}
                    )
                )
        except (PyMongoError, RuntimeError):
            # Keep the last exact hydrated cache during a transient authority
            # failure; never substitute authoring-library features.
            cached = self._cached_active()
            if (
                cached
                and cached.get("deployment_id") == deployment_id
                and cached.get("map_collection") == collection_name
            ):
                for key in ("snapshot", "live_features", "world_binding"):
                    if key in cached:
                        hydrated[key] = deepcopy(cached[key])
            hydrated.setdefault("snapshot", {"type": "FeatureCollection", "features": []})
            hydrated.setdefault("live_features", {"type": "FeatureCollection", "features": []})
            return hydrated
        hydrated["snapshot"] = {
            "type": "FeatureCollection",
            "features": snapshot_features,
        }
        hydrated["live_features"] = {
            "type": "FeatureCollection",
            "features": [row["feature"] for row in live_documents],
        }
        hydrated["world_binding"] = {
            "world_id": hydrated.get("world_id"),
            "world_version": hydrated.get("world_version"),
            "deployment_id": deployment_id,
            "launch_id": hydrated.get("launch_id"),
            "content_hash": hydrated.get("content_hash"),
            "map_collection": collection_name,
            "map_feature_hash": hydrated.get("map_feature_hash"),
            "map_snapshot_token": hydrated.get("map_snapshot_token"),
            "status": hydrated.get("status"),
            "ready": hydrated.get("ready") is True,
        }
        return hydrated

    def _require_authoritative_active(self) -> dict[str, Any]:
        state = self.active()
        if not state or state.get("cache_diagnostic_only") or not state.get("deployment_id"):
            raise WorldNotReadyError("no authoritative active deployment exists")
        return state

    def _authoring_features(self, map_name: str) -> list[dict[str, Any]]:
        features = deepcopy(load_static_geojson_map(self.repo_root, map_name).get("features", []))
        with self._client() as client:
            features.extend(
                row["feature"]
                for row in client["MapDB"][AUTHORING_FEATURES_COLLECTION].find(
                    {"map": map_name}, {"_id": 0, "feature": 1}
                )
            )
        return features

    def _validate_authoring_membership(self, definition: dict[str, Any]) -> None:
        available = {
            str((feature.get("properties") or {}).get("feature_id") or feature.get("id") or "")
            for feature in self._authoring_features(str(definition.get("map") or "rma"))
        }
        missing = sorted(set(definition.get("feature_ids") or []) - available)
        if missing:
            raise ValueError("world references unknown authoring feature ids: " + ", ".join(missing))

    def authoring_feature_collection(self, map_name: str) -> dict[str, Any]:
        return {"type": "FeatureCollection", "features": self._authoring_features(map_name)}

    def create_authoring_feature(self, map_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        feature = normalize_user_geojson_feature(payload)
        feature["properties"].update({"source": "authoring", "map": map_name})
        document = {
            "map": map_name,
            "feature_id": feature["properties"]["feature_id"],
            "feature": feature,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        with self._client() as client:
            try:
                client["MapDB"][AUTHORING_FEATURES_COLLECTION].insert_one(deepcopy(document))
            except DuplicateKeyError as exc:
                raise WorldConflictError(
                    "an authoring feature with this ID already exists on this map"
                ) from exc
        return feature

    def update_authoring_feature(self, map_name: str, feature_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        feature = normalize_user_geojson_feature(payload)
        feature["id"] = feature_id
        feature["properties"].update(
            {"feature_id": feature_id, "source": "authoring", "map": map_name}
        )
        with self._client() as client:
            result = client["MapDB"][AUTHORING_FEATURES_COLLECTION].update_one(
                {"map": map_name, "feature_id": feature_id},
                {"$set": {"feature": feature, "updated_at": _utc_now()}},
            )
            if result.matched_count != 1:
                raise WorldNotFoundError(feature_id)
        return feature

    def delete_authoring_feature(
        self,
        map_name: str,
        feature_id: str,
        *,
        world_id: str | None = None,
        revision: int | None = None,
    ) -> dict[str, Any]:
        with self._client() as client:
            definitions = client[WORLD_DATABASE][DEFINITIONS_COLLECTION]
            referenced = list(
                definitions.find(
                    {"feature_ids": feature_id, "archived": {"$ne": True}},
                    {"_id": 0},
                )
            )
            if referenced:
                if not world_id or revision is None:
                    raise WorldConflictError("authoring feature is attached to a world definition")
                foreign_worlds = [
                    str(item.get("world_id") or "")
                    for item in referenced
                    if item.get("world_id") != world_id
                ]
                if foreign_worlds:
                    raise WorldConflictError(
                        "authoring feature is also attached to another world definition"
                    )
                current = referenced[0]
                if current.get("revision") != revision:
                    raise WorldConflictError("world definition revision conflict", current)
                remaining_feature_ids = [
                    item for item in current.get("feature_ids") or [] if item != feature_id
                ]
                detached = definitions.update_one(
                    {
                        "world_id": world_id,
                        "revision": revision,
                        "archived": {"$ne": True},
                    },
                    {
                        "$set": {
                            "feature_ids": remaining_feature_ids,
                            "updated_at": _utc_now(),
                        },
                        "$inc": {"revision": 1},
                    },
                )
                if detached.modified_count != 1:
                    latest = definitions.find_one({"world_id": world_id}, {"_id": 0})
                    raise WorldConflictError("world definition revision conflict", latest)
            result = client["MapDB"][AUTHORING_FEATURES_COLLECTION].delete_one(
                {"map": map_name, "feature_id": feature_id}
            )
            if result.deleted_count != 1:
                raise WorldNotFoundError(feature_id)
            saved_world = (
                definitions.find_one({"world_id": world_id}, {"_id": 0})
                if referenced and world_id
                else None
            )
            hydrated_world = (
                self._hydrate_definition(client, saved_world) if saved_world else None
            )
        return {
            "feature_id": feature_id,
            "deleted": True,
            "world": hydrated_world,
        }

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]:
        state = self.validated_active()
        if not state or state.get("status") != "ready":
            detail = (state or {}).get("error") or "launch a world in the World tab first"
            raise WorldNotReadyError(f"world runtime is not ready: {detail}")
        requested = {_normalize_agent_id(item) for item in vehicle_ids or []}
        available = {_normalize_agent_id(str(agent.get("agent_id") or "")) for agent in state.get("agents") or []}
        missing = sorted(requested - available)
        if missing:
            raise WorldNotReadyError(f"mission vehicles are not part of the active world: {', '.join(missing)}")
        return state

    def validated_active(self) -> dict[str, Any] | None:
        """Return active state after checking that its external reality still exists."""
        state = self.active()
        if state and state.get("cache_diagnostic_only"):
            return state
        if not state or state.get("status") not in {"ready", "stale"}:
            return state
        issues = self._ready_runtime_issues(state)
        if not issues and state.get("status") == "ready":
            return state
        if not issues:
            recovered = deepcopy(state)
            recovered.update(
                {
                    "status": "ready",
                    "ready": True,
                    "recovered_at": _utc_now(),
                }
            )
            recovered.pop("error", None)
            recovered.pop("stale_at", None)
            self._publish_observed_state(recovered)
            return recovered

        if state.get("status") == "stale" and state.get("error") == "active world runtime is stale: " + "; ".join(issues):
            return state
        stale = deepcopy(state)
        stale.update(
            {
                "status": "stale",
                "ready": False,
                "error": "active world runtime is stale: " + "; ".join(issues),
                "stale_at": _utc_now(),
            }
        )
        self._publish_observed_state(stale)
        return stale

    def launch(self, world_id: str, revision: int) -> dict[str, Any]:
        definition = self.get_world(world_id)
        if definition["revision"] != revision:
            raise WorldConflictError("launch revision is not the last acknowledged definition", definition)
        payload = definition
        if not self._lock.acquire(blocking=False):
            raise WorldNotReadyError("another world launch is already running")
        snapshot: dict[str, Any] | None = None
        state: dict[str, Any] = {}
        previous = self.active()
        reality_changed = False
        try:
            snapshot = build_world_snapshot(
                self.repo_root,
                payload,
                authoring_features=self._authoring_features(payload["map"]),
            )
            if (
                previous
                and previous.get("content_hash") == snapshot["content_hash"]
                and previous.get("status") == "ready"
                and not self._ready_runtime_issues(previous)
            ):
                return {**previous, "idempotent_reuse": True}
            launched_at = _utc_now()
            deployment_id = f"deployment-{uuid.uuid4().hex}"
            state = {
                **{key: value for key, value in snapshot.items() if key != "features"},
                "state_schema_version": WORLD_STATE_SCHEMA_VERSION,
                "launch_id": uuid.uuid4().hex,
                "launch_phase": "validated",
                "deployment_id": deployment_id,
                "managed_runtime": True,
                "definition_revision": revision,
                "phase_updated_at": launched_at,
                "phase_history": [
                    {"phase": "validated", "recorded_at": launched_at}
                ],
                "status": "launching",
                "ready": False,
                "launched_at": launched_at,
                "containers": [],
                "map_snapshot_token": uuid.uuid4().hex,
            }
            self._persist_immutable_snapshot(snapshot)
            # Do not publish a new authoritative identity until its exact
            # content-addressed snapshot is durable and can be hydrated.
            self._publish_transition(state)
            self._advance_launch(state, "snapshot_persisted")
            self._write_planner_config(snapshot["map_collection"], state["map_snapshot_token"])
            self._advance_launch(state, "planner_configured")
            reality_changed = True
            self._replace_previous_runtime(previous)
            self._advance_launch(state, "previous_runtime_stopped")
            self._clear_world_runtime_records()
            self._advance_launch(state, "runtime_records_cleared")
            self._restart_container(COORDINATION_CONTAINER, "centralized coordination")
            self._restart_planner()
            # The REST bridge and rosbridge are ROS participants even while
            # their HTTP/WebSocket listeners remain healthy. Restarting them
            # with the runtime prevents a stale DDS socket from silently
            # acknowledging Init without publishing it to coordination.
            self._restart_container(C2_REST_CONTAINER, "C2 REST bridge")
            self._restart_container(ROSBRIDGE_CONTAINER, "rosbridge")
            self._advance_launch(state, "backend_restarted")
            launched = launch_deployment(
                self.repo_root,
                {
                    "deployment_id": deployment_id,
                    "name": "generic runtime deployment",
                    "agents": deepcopy(snapshot["agents"]),
                },
                host_repo_root=self.host_repo_root,
                docker_socket=self.docker_socket,
            )
            if not launched.get("docker_started"):
                raise RuntimeError(str(launched.get("message") or "world robot containers did not start"))
            state["containers"] = launched.get("containers") or []
            self._advance_launch(state, "robots_launched")
            self._wait_until_ready(snapshot, state["containers"], state["map_snapshot_token"])
            self._advance_launch(state, "runtime_verified")
            # Mission nodes from the old coordination process may publish one
            # final feedback sample while Docker is stopping it. Remove those
            # stragglers only after the replacement runtime is verified.
            self._clear_mission_runtime_records()
            state.update(
                {
                    "status": "ready",
                    "ready": True,
                    "verified_at": _utc_now(),
                    "message": (
                        f"World {snapshot['name']} is active. Planner uses immutable "
                        f"MapDB.{snapshot['map_collection']} and {len(state['agents'])} robot(s) are registered."
                    ),
                    "docker_started": True,
                }
            )
            self._advance_launch(state, "ready")
            return state
        except Exception as exc:
            if not reality_changed and previous:
                if state:
                    failed_attempt = {
                        **state,
                        "status": "failed",
                        "ready": False,
                        "error": str(exc),
                        "failed_at": _utc_now(),
                        "retryable": True,
                    }
                    self._set_launch_phase(failed_attempt, "failed")
                    self._record_launch_best_effort(failed_attempt)
                if not previous.get("cache_diagnostic_only"):
                    self._publish_observed_state(previous)
                raise WorldNotReadyError(str(exc)) from exc
            state = state or {
                "world_id": str(payload.get("world_id") or "unknown"),
                "name": str(payload.get("name") or payload.get("world_id") or "unknown"),
            }
            state.update(
                {
                    "status": "failed",
                    "ready": False,
                    "error": str(exc),
                    "failed_at": _utc_now(),
                    "retryable": True,
                }
            )
            self._set_launch_phase(state, "failed")
            self._publish_observed_state(state)
            raise WorldNotReadyError(str(exc)) from exc
        finally:
            self._lock.release()

    def _persist_immutable_snapshot(self, snapshot: dict[str, Any]) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for world launch")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client.admin.command("ping")
                map_database = client["MapDB"]
                versions = client[WORLD_DATABASE][VERSIONS_COLLECTION]
                existing = versions.find_one(
                    {
                        "world_id": snapshot["world_id"],
                        "world_version": snapshot["world_version"],
                    }
                )
                collection = map_database[snapshot["map_collection"]]
                if existing:
                    if existing.get("content_hash") != snapshot["content_hash"]:
                        raise RuntimeError("immutable world version hash mismatch")
                    if collection.count_documents({}) != snapshot["feature_count"]:
                        raise RuntimeError("immutable world collection contents were modified")
                    stored_features = list(collection.find({}, {"_id": 0}))
                    if _feature_content_hash(stored_features) != snapshot["map_feature_hash"]:
                        raise RuntimeError("immutable world collection contents were modified")
                    self._ensure_snapshot_indexes(client, snapshot["map_collection"])
                    return
                if snapshot["map_collection"] in map_database.list_collection_names():
                    stored_features = list(collection.find({}, {"_id": 0}))
                    if _feature_content_hash(stored_features) != snapshot["map_feature_hash"]:
                        raise RuntimeError("content-addressed map snapshot hash mismatch")
                elif snapshot["features"]:
                    collection.insert_many(deepcopy(snapshot["features"]))
                versions.insert_one(
                    {
                        "world_id": snapshot["world_id"],
                        "name": snapshot["name"],
                        "map": snapshot["map"],
                        "notes": snapshot["notes"],
                        "agents": deepcopy(snapshot["agents"]),
                        "feature_ids": deepcopy(snapshot["feature_ids"]),
                        "map_view": deepcopy(snapshot["map_view"]),
                        "world_version": snapshot["world_version"],
                        "content_hash": snapshot["content_hash"],
                        "map_collection": snapshot["map_collection"],
                        "feature_count": snapshot["feature_count"],
                        "road_count": snapshot["road_count"],
                        "map_feature_hash": snapshot["map_feature_hash"],
                        "created_at": _utc_now(),
                        "immutable": True,
                    }
                )
                self._ensure_snapshot_indexes(client, snapshot["map_collection"])
        except PyMongoError as exc:
            raise RuntimeError(f"could not create immutable MapDB snapshot: {exc}") from exc

    @staticmethod
    def _ensure_snapshot_indexes(client: Any, collection_name: str) -> None:
        outcomes = MongoIndexManager(client).ensure(map_feature_index_specs(collection_name))
        failures = [outcome for outcome in outcomes if outcome.status not in {"created", "existing"}]
        if failures:
            details = "; ".join(f"{item.name}: {item.detail}" for item in failures)
            raise RuntimeError(f"immutable world indexes are not ready: {details}")

    def _write_planner_config(self, collection: str, map_snapshot_token: str) -> None:
        source = self.repo_root / "backend" / "config" / "config_planner.yaml"
        text = source.read_text(encoding="utf-8")
        text, replacements = re.subn(
            r'(?m)^(\s*map_feature_collection:\s*)[^#\n]+',
            rf'\1"{collection}"',
            text,
        )
        if replacements != 1:
            raise RuntimeError("planner config does not contain exactly one map_feature_collection parameter")
        text, token_replacements = re.subn(
            r'(?m)^(\s*map_snapshot_token:\s*)[^#\n]+',
            rf'\1"{map_snapshot_token}"',
            text,
        )
        if token_replacements != 1:
            raise RuntimeError("planner config does not contain exactly one map_snapshot_token parameter")
        target = self.repo_root / "data" / "runtime" / PLANNER_CONFIG_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def _replace_previous_runtime(self, previous: dict[str, Any] | None) -> None:
        for container in previous.get("containers", []) if previous else []:
            name = str(container.get("container_name") or "")
            if (
                previous.get("managed_runtime") is True
                and name.startswith("c2-imugs2-backend-")
                and name
                not in {
                    PLANNER_CONTAINER,
                    COORDINATION_CONTAINER,
                    C2_REST_CONTAINER,
                    ROSBRIDGE_CONTAINER,
                    DEFAULT_EDGE_CONTAINER,
                }
            ):
                _docker_request(self.docker_socket, "DELETE", f"/containers/{name}?force=true")
        _docker_request(self.docker_socket, "POST", f"/containers/{DEFAULT_EDGE_CONTAINER}/stop?t=10")

    def _clear_world_runtime_records(self) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for world launch")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client.admin.command("ping")
                for name in ("MissionFeedback", "Planning", "MissionConfig", "Logs", "ConnectedVehicles"):
                    client["RuntimeDB"][name].delete_many({})
                client["VehicleDB"]["Vehicles"].delete_many({})
        except PyMongoError as exc:
            raise RuntimeError(f"could not clear previous world runtime: {exc}") from exc

    def _clear_mission_runtime_records(self) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for world launch")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client.admin.command("ping")
                for name in ("MissionFeedback", "Planning", "MissionConfig", "Logs"):
                    client["RuntimeDB"][name].delete_many({})
        except PyMongoError as exc:
            raise RuntimeError(f"could not finalize previous mission cleanup: {exc}") from exc

    def _restart_planner(self) -> None:
        self._restart_container(PLANNER_CONTAINER, "planner")

    def _restart_container(self, container: str, label: str) -> None:
        status, payload = _docker_request(self.docker_socket, "POST", f"/containers/{container}/restart?t=20")
        if status not in (204, 304):
            raise RuntimeError(f"{label} restart failed: {payload}")

    def _wait_until_ready(
        self,
        snapshot: dict[str, Any],
        containers: list[dict[str, Any]],
        map_snapshot_token: str,
    ) -> None:
        expected = {_normalize_agent_id(str(agent.get("agent_id") or "")) for agent in snapshot["agents"]}
        marker = (
            f"MAP IS LOADED collection=MapDB.{snapshot['map_collection']} "
            f"snapshot={map_snapshot_token}"
        )
        deadline = time.monotonic() + self.readiness_timeout
        last_registered: set[str] = set()
        while time.monotonic() < deadline:
            logs_status, logs = _docker_request(
                self.docker_socket,
                "GET",
                f"/containers/{PLANNER_CONTAINER}/logs?stdout=1&stderr=1&tail=300",
            )
            planner_ready = logs_status == 200 and marker in str(logs)
            coordination_ready = self._container_running(COORDINATION_CONTAINER)
            gateways_ready = all(
                self._container_running(name)
                for name in (C2_REST_CONTAINER, ROSBRIDGE_CONTAINER)
            )
            containers_ready = all(self._container_running(str(item.get("container_name") or "")) for item in containers)
            try:
                if MongoClient is None:
                    raise PyMongoError("pymongo is not installed")
                with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=1000) as client:
                    last_registered = {
                        _normalize_agent_id(str(item.get("agent_id") or ""))
                        for item in client["RuntimeDB"]["ConnectedVehicles"].find({}, {"agent_id": 1})
                    }
            except PyMongoError:
                last_registered = set()
            if (
                planner_ready
                and coordination_ready
                and gateways_ready
                and containers_ready
                and expected <= last_registered
            ):
                return
            time.sleep(1)
        missing = sorted(expected - last_registered)
        raise RuntimeError(
            f"deployment readiness timed out; planner_marker={marker!r}, missing_registered_robots={missing}"
        )

    def _container_running(self, name: str) -> bool:
        if not name:
            return False
        status, payload = _docker_request(self.docker_socket, "GET", f"/containers/{name}/json")
        return status == 200 and bool((payload.get("State") or {}).get("Running"))

    def _active_runtime_issues(self, state: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        collection_name = str(state.get("map_collection") or "")
        expected_count = int(state.get("feature_count") or 0)
        expected_agents = {
            _normalize_agent_id(str(agent.get("agent_id") or ""))
            for agent in state.get("agents") or []
            if agent.get("agent_id")
        }
        registered_agents: set[str] = set()
        if not collection_name:
            issues.append("active MapDB collection is not recorded")
        elif MongoClient is None:
            issues.append("MongoDB validation is unavailable")
        else:
            try:
                with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=2000) as client:
                    client.admin.command("ping")
                    database = client["MapDB"]
                    if collection_name not in database.list_collection_names():
                        issues.append(f"MapDB.{collection_name} is missing")
                    else:
                        actual_count = database[collection_name].count_documents({})
                        if actual_count == 0:
                            issues.append(f"MapDB.{collection_name} is empty")
                        elif expected_count and actual_count != expected_count:
                            issues.append(
                                f"MapDB.{collection_name} has {actual_count} features; expected {expected_count}"
                            )
                    registered_agents = {
                        _normalize_agent_id(str(item.get("agent_id") or ""))
                        for item in client["RuntimeDB"]["ConnectedVehicles"].find({}, {"agent_id": 1})
                    }
            except PyMongoError as exc:
                issues.append(f"MongoDB readiness check failed: {exc}")

        try:
            if not self._container_running(COORDINATION_CONTAINER):
                issues.append(f"container {COORDINATION_CONTAINER} is not running")
            if not self._container_running(PLANNER_CONTAINER):
                issues.append(f"container {PLANNER_CONTAINER} is not running")
            if not self._container_running(C2_REST_CONTAINER):
                issues.append(f"container {C2_REST_CONTAINER} is not running")
            if not self._container_running(ROSBRIDGE_CONTAINER):
                issues.append(f"container {ROSBRIDGE_CONTAINER} is not running")
            robot_containers = state.get("containers") or []
            if expected_agents and not robot_containers:
                issues.append("no deployment robot containers are recorded")
            for container in robot_containers:
                name = str(container.get("container_name") or "")
                if not self._container_running(name):
                    issues.append(f"deployment robot container {name or '<unnamed>'} is not running")
        except OSError as exc:
            issues.append(f"Docker readiness check failed: {exc}")

        missing_agents = sorted(expected_agents - registered_agents)
        if missing_agents:
            issues.append(f"robots are not registered: {', '.join(missing_agents)}")

        planner_config = self.repo_root / "data" / "runtime" / PLANNER_CONFIG_FILE
        try:
            config_text = planner_config.read_text(encoding="utf-8")
        except OSError:
            issues.append("active planner configuration is missing")
        else:
            map_snapshot_token = str(state.get("map_snapshot_token") or "")
            if collection_name and f'map_feature_collection: "{collection_name}"' not in config_text:
                issues.append("active planner configuration targets a different MapDB collection")
            if map_snapshot_token and f'map_snapshot_token: "{map_snapshot_token}"' not in config_text:
                issues.append("active planner configuration has a different map snapshot token")
        return issues

    def _planner_readiness_issue(self, state: dict[str, Any]) -> str | None:
        """Require an exact planner proof without depending on an endless log tail.

        Launch records ``verified_at`` only after observing the exact
        collection/token marker.  Large planner JSON logs can later push that
        marker beyond Docker's bounded tail, so the proof remains valid while
        the same planner process (identified by ``StartedAt``) is still
        running.  A process started after verification must emit the marker
        again before it is trusted.
        """
        collection_name = str(state.get("map_collection") or "")
        map_snapshot_token = str(state.get("map_snapshot_token") or "")
        if not collection_name or not map_snapshot_token:
            return "planner collection or map snapshot token is not recorded"
        marker = f"MAP IS LOADED collection=MapDB.{collection_name} snapshot={map_snapshot_token}"
        try:
            status, logs = _docker_request(
                self.docker_socket,
                "GET",
                f"/containers/{PLANNER_CONTAINER}/logs?stdout=1&stderr=1&tail=1000",
            )
        except OSError as exc:
            return f"planner readiness check failed: {exc}"
        if status == 200 and marker in str(logs):
            return None
        if self._verified_planner_process_is_unchanged(state):
            return None
        return "planner has not reported the active MapDB collection and map snapshot token"

    def _verified_planner_process_is_unchanged(self, state: dict[str, Any]) -> bool:
        verified_at = _parse_runtime_datetime(state.get("verified_at"))
        if verified_at is None:
            return False
        try:
            status, payload = _docker_request(
                self.docker_socket,
                "GET",
                f"/containers/{PLANNER_CONTAINER}/json",
            )
        except OSError:
            return False
        if status != 200 or not isinstance(payload, dict):
            return False
        container_state = payload.get("State")
        if not isinstance(container_state, dict) or not container_state.get("Running"):
            return False
        started_at = _parse_runtime_datetime(container_state.get("StartedAt"))
        return started_at is not None and started_at <= verified_at

    def _ready_runtime_issues(self, state: dict[str, Any]) -> list[str]:
        """Apply one readiness proof to both observation and idempotent reuse."""
        issues = self._active_runtime_issues(state)
        if not issues:
            planner_issue = self._planner_readiness_issue(state)
            if planner_issue:
                issues.append(planner_issue)
        return issues

    def _mark_active_in_mongo(self, state: dict[str, Any]) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for world launch")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client[WORLD_DATABASE][ACTIVE_WORLD_COLLECTION].replace_one(
                    {"singleton": "active"},
                    {"singleton": "active", **_durable_state(state)},
                    upsert=True,
                )
        except PyMongoError as exc:
            raise RuntimeError(f"could not publish active world marker: {exc}") from exc

    def _record_launch(self, state: dict[str, Any]) -> None:
        launch_id = str(state.get("launch_id") or "")
        if not launch_id:
            return
        if MongoClient is None:
            raise RuntimeError("pymongo is required for world launch")
        record = _durable_state(state)
        record["recorded_at"] = _utc_now()
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client[WORLD_DATABASE][LAUNCHES_COLLECTION].replace_one(
                    {"launch_id": launch_id},
                    record,
                    upsert=True,
                )
        except PyMongoError as exc:
            raise RuntimeError(f"could not persist world launch record: {exc}") from exc

    def _record_launch_best_effort(self, state: dict[str, Any]) -> None:
        try:
            self._record_launch(state)
        except RuntimeError:
            pass

    def _publish_transition(self, state: dict[str, Any]) -> None:
        """Durably publish a transition before updating the generated file cache."""
        self._record_launch(state)
        self._mark_active_in_mongo(state)
        self._save_state(state)

    def _publish_observed_state(self, state: dict[str, Any]) -> None:
        """Publish readiness observations, retaining diagnostics if Mongo is down."""
        try:
            self._record_launch(state)
            self._mark_active_in_mongo(state)
        except RuntimeError:
            pass
        self._save_state(state)

    def _advance_launch(self, state: dict[str, Any], phase: str) -> None:
        self._set_launch_phase(state, phase)
        self._publish_transition(state)

    @staticmethod
    def _set_launch_phase(state: dict[str, Any], phase: str) -> None:
        recorded_at = _utc_now()
        state["launch_phase"] = phase
        state["phase_updated_at"] = recorded_at
        history = state.setdefault("phase_history", [])
        if not isinstance(history, list):
            history = []
            state["phase_history"] = history
        last_phase = (
            history[-1].get("phase")
            if history and isinstance(history[-1], dict)
            else None
        )
        if last_phase != phase:
            history.append({"phase": phase, "recorded_at": recorded_at})

    def _save_state(self, state: dict[str, Any]) -> None:
        path = self.repo_root / "data" / "runtime" / ACTIVE_STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temporary.replace(path)


def _feature_bbox(features: list[dict[str, Any]]) -> list[float]:
    points: list[tuple[float, float]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(item, int | float) for item in value[:2]):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for item in value:
                collect(item)

    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
        collect(geometry.get("coordinates"))
    if not points:
        return [0.0, 0.0, 0.0, 0.0]
    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]
    return [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]


def _validated_definition(payload: dict[str, Any], *, world_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("world definition must be an object")
    name = _required_text(payload.get("name"), "name")
    map_name = _required_text(payload.get("map") or "rma", "map")
    feature_ids = payload.get("feature_ids") or []
    if not isinstance(feature_ids, list) or any(not isinstance(item, str) or not item.strip() for item in feature_ids):
        raise ValueError("feature_ids must be a list of non-empty strings")
    agents = payload.get("agents") or []
    if not isinstance(agents, list) or any(not isinstance(item, dict) for item in agents):
        raise ValueError("agents must be a list of objects")
    agent_ids = [str(item.get("agent_id") or "").strip() for item in agents]
    if any(not item for item in agent_ids) or len(set(agent_ids)) != len(agent_ids):
        raise ValueError("every world agent must have a unique agent_id")
    for agent in agents:
        _required_text(agent.get("name"), "agent name")
        _required_text(agent.get("vehicle_type"), "agent vehicle_type")
        constraints = agent.get("constraints")
        capabilities = agent.get("capabilities")
        location = agent.get("current_location")
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError("agent constraints must be an object")
        if capabilities is not None and (
            not isinstance(capabilities, list)
            or any(not isinstance(item, str) for item in capabilities)
        ):
            raise ValueError("agent capabilities must be a list of strings")
        if location is not None and (
            not isinstance(location, list)
            or len(location) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(float(value))
                for value in location
            )
        ):
            raise ValueError("agent current_location must be finite [lon, lat]")
    map_view = payload.get("map_view")
    if map_view is not None:
        if not isinstance(map_view, dict):
            raise ValueError("map_view must be an object")
        center = map_view.get("center")
        zoom = map_view.get("zoom")
        if (
            not isinstance(center, list)
            or len(center) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(float(value))
                for value in center
            )
            or isinstance(zoom, bool)
            or not isinstance(zoom, int | float)
            or not math.isfinite(float(zoom))
        ):
            raise ValueError("map_view requires numeric center [lon, lat] and zoom")
        map_view = {"center": [float(center[0]), float(center[1])], "zoom": float(zoom)}
    return {
        "world_id": world_id,
        "name": name,
        "map": map_name,
        "notes": str(payload.get("notes") or ""),
        "feature_ids": list(dict.fromkeys(item.strip() for item in feature_ids)),
        "agents": deepcopy(agents),
        "map_view": deepcopy(map_view),
    }


def _validated_vehicle_model(payload: dict[str, Any], model_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("vehicle model must be an object")
    label = _required_text(payload.get("label") or payload.get("name"), "label")
    vehicle_type = _required_text(payload.get("vehicle_type"), "vehicle_type")
    constraints = payload.get("constraints") or {}
    capabilities = payload.get("capabilities") or []
    if not isinstance(constraints, dict):
        raise ValueError("vehicle model constraints must be an object")
    if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
        raise ValueError("vehicle model capabilities must be a list of strings")
    return {
        "model_id": model_id,
        "label": label,
        "vehicle_type": vehicle_type,
        "constraints": deepcopy(constraints),
        "capabilities": list(dict.fromkeys(capabilities)),
        "default_name": str(payload.get("default_name") or ""),
    }


def _required_revision(payload: dict[str, Any]) -> int:
    value = payload.get("revision")
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("revision must be a positive integer")
    return value


def _durable_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value)
        for key, value in state.items()
        if key not in {"snapshot", "live_features", "world_binding"}
    }


def _parse_runtime_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_agent_id(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")[:48] or "world"


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _feature_content_hash(features: list[dict[str, Any]]) -> str:
    ordered = sorted(
        features,
        key=lambda feature: str((feature.get("properties") or {}).get("feature_id") or feature.get("id") or ""),
    )
    return hashlib.sha256(
        json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
