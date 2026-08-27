from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from typing import Any
import uuid

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:  # Keep pure snapshot construction usable in lightweight test environments.
    MongoClient = None  # type: ignore[assignment,misc]

    class PyMongoError(Exception):
        pass

from .legacy_map import load_legacy_geojson_map
from .mongo_maintenance import MongoIndexManager, map_feature_index_specs
from .scenario_launch import _docker_request, launch_scenario


PLANNER_CONTAINER = "c2-imugs2-backend-planner"
COORDINATION_CONTAINER = "c2-imugs2-backend-centralized-coordination"
C2_REST_CONTAINER = "c2-imugs2-backend-c2-ros-rest"
ROSBRIDGE_CONTAINER = "c2-imugs2-backend-rosbridge"
DEFAULT_EDGE_CONTAINER = "c2-imugs2-backend-edge-agent-sim-1"
ACTIVE_STATE_FILE = "active_scenario.json"
PLANNER_CONFIG_FILE = "active_planner.yaml"
MAP_METADATA_COLLECTION = "_scenario_versions"
ACTIVE_SCENARIO_COLLECTION = "_active_scenario"
ACTIVATION_COLLECTION = "_scenario_activations"
SCENARIO_STATE_SCHEMA_VERSION = "1.0"


class ScenarioNotReadyError(RuntimeError):
    pass


@dataclass(frozen=True)
class _DurableActiveLookup:
    """Tri-state read of the MongoDB active-scenario singleton."""

    reachable: bool
    state: dict[str, Any] | None = None
    error: str | None = None


def build_scenario_snapshot(repo_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Build the exact, frozen GeoJSON input that one planner process will use."""
    scenario_id = _required_text(payload.get("scenario_id"), "scenario_id")
    map_name = _required_text(payload.get("map") or "rma", "map")
    agents = payload.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ValueError("scenario activation requires at least one vehicle")

    base = load_legacy_geojson_map(repo_root, map_name)
    feature_ids = payload.get("feature_ids") or []
    if not isinstance(feature_ids, list) or any(not isinstance(item, str) for item in feature_ids):
        raise ValueError("feature_ids must be a list of strings")
    available = {
        str((feature.get("properties") or {}).get("feature_id") or feature.get("id")): feature
        for feature in base.get("features", [])
    }
    missing = sorted(set(feature_ids) - set(available))
    if missing:
        raise ValueError(f"scenario references unknown map feature ids: {', '.join(missing)}")

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
            feature_id = f"osm-{import_id}-{_safe_name(source_id)}-{road_index}"
            properties.update(
                {
                    "feature_id": feature_id,
                    "feature_type": "road",
                    "name": properties.get("name") or f"OSM road {road_index + 1}",
                    "source": "frozen_openstreetmap",
                    "scenario_road_import_id": import_id,
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
        raise ValueError("scenario must contain at least one selected or downloaded road LineString")

    canonical_payload = {
        "scenario_id": scenario_id,
        "name": str(payload.get("name") or scenario_id),
        "map": map_name,
        "notes": str(payload.get("notes") or ""),
        "agents": agents,
        "feature_ids": feature_ids,
        "road_imports": payload.get("road_imports") or [],
    }
    digest = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    version = digest[:16]
    collection = f"scenario_{_safe_name(scenario_id)[:32]}_{version}"
    return {
        "scenario_id": scenario_id,
        "name": canonical_payload["name"],
        "map": map_name,
        "notes": canonical_payload["notes"],
        "version": version,
        "content_hash": digest,
        "map_collection": collection,
        "feature_count": len(unique_features),
        "road_count": road_count,
        "map_feature_hash": _feature_content_hash(unique_features),
        "feature_ids": deepcopy(feature_ids),
        "features": unique_features,
        "agents": deepcopy(agents),
    }


class ScenarioRuntimeManager:
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
                self._save_state(lookup.state)
                return lookup.state
            # A successful authoritative read with no singleton means there is
            # no active scenario.  A stale local file must not override that.
            return None

        cached = self._cached_active()
        detail = lookup.error or "MongoDB active-scenario authority is unavailable"
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
                "error": f"active scenario authority is unavailable: {detail}",
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
                value = client["MapDB"][ACTIVE_SCENARIO_COLLECTION].find_one(
                    {"singleton": "active"},
                    {"_id": 0, "singleton": 0},
                )
        except PyMongoError as exc:
            return _DurableActiveLookup(False, error=str(exc))
        return _DurableActiveLookup(
            True, state=value if isinstance(value, dict) else None
        )

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]:
        state = self.validated_active()
        if not state or state.get("status") != "ready":
            detail = (state or {}).get("error") or "activate a scenario in the Scenario tab first"
            raise ScenarioNotReadyError(f"scenario runtime is not ready: {detail}")
        requested = {_normalize_agent_id(item) for item in vehicle_ids or []}
        available = {_normalize_agent_id(str(agent.get("agent_id") or "")) for agent in state.get("agents") or []}
        missing = sorted(requested - available)
        if missing:
            raise ScenarioNotReadyError(f"mission vehicles are not part of the active scenario: {', '.join(missing)}")
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

        if state.get("status") == "stale" and state.get("error") == "active scenario runtime is stale: " + "; ".join(issues):
            return state
        stale = deepcopy(state)
        stale.update(
            {
                "status": "stale",
                "ready": False,
                "error": "active scenario runtime is stale: " + "; ".join(issues),
                "stale_at": _utc_now(),
            }
        )
        self._publish_observed_state(stale)
        return stale

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return the latest immutable version of every activated scenario."""
        if MongoClient is None:
            raise RuntimeError("pymongo is required for the scenario catalog")
        active = self.validated_active() or {}
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client.admin.command("ping")
                database = client["MapDB"]
                versions = list(database[MAP_METADATA_COLLECTION].find({}, {"_id": 0}).sort("created_at", -1))
                scenarios: list[dict[str, Any]] = []
                seen: set[str] = set()
                for version in versions:
                    scenario_id = str(version.get("scenario_id") or "")
                    collection_name = str(version.get("map_collection") or "")
                    if not scenario_id or not collection_name or scenario_id in seen:
                        continue
                    seen.add(scenario_id)
                    is_active = (
                        active.get("scenario_id") == scenario_id
                        and active.get("map_collection") == collection_name
                    )
                    definition = {**version, **(active if is_active else {})}
                    frozen_roads = list(
                        database[collection_name].find(
                            {"properties.source": "frozen_openstreetmap", "geometry.type": "LineString"},
                            {"_id": 0},
                        )
                    )
                    road_groups: dict[str, list[dict[str, Any]]] = {}
                    for road in frozen_roads:
                        properties = road.get("properties") if isinstance(road.get("properties"), dict) else {}
                        import_id = str(properties.get("scenario_road_import_id") or "frozen-osm")
                        road_groups.setdefault(import_id, []).append(road)
                    road_imports = []
                    for import_id, roads in road_groups.items():
                        road_imports.append(
                            {
                                "import_id": import_id,
                                "name": f"Frozen OSM roads ({import_id})",
                                "bbox": _feature_bbox(roads),
                                "feature_count": len(roads),
                                "geojson": {"type": "FeatureCollection", "features": roads},
                                "created_at": str(version.get("created_at") or ""),
                            }
                        )
                    agents = deepcopy(definition.get("agents") or [])
                    scenarios.append(
                        {
                            "scenario_id": scenario_id,
                            "name": str(definition.get("name") or scenario_id),
                            "map": str(definition.get("map") or "rma"),
                            "notes": str(definition.get("notes") or ""),
                            "feature_ids": deepcopy(definition.get("feature_ids") or []),
                            "selected_agent_id": str(agents[0].get("agent_id") or "") if agents else "",
                            "agents": agents,
                            "road_imports": road_imports,
                            "version": str(version.get("version") or ""),
                            "map_collection": collection_name,
                            "feature_count": int(version.get("feature_count") or 0),
                            "road_count": int(version.get("road_count") or 0),
                            "runtime_active": is_active,
                            "runtime_status": str(active.get("status") or "unknown") if is_active else "saved",
                            "created_at": str(version.get("created_at") or ""),
                            "updated_at": str((active if is_active else version).get("verified_at") or version.get("created_at") or ""),
                        }
                    )
                return scenarios
        except PyMongoError as exc:
            raise RuntimeError(f"could not read scenario catalog: {exc}") from exc

    def activate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._lock.acquire(blocking=False):
            raise ScenarioNotReadyError("another scenario activation is already running")
        snapshot: dict[str, Any] | None = None
        state: dict[str, Any] = {}
        previous = self.active()
        reality_changed = False
        try:
            snapshot = build_scenario_snapshot(self.repo_root, payload)
            if (
                previous
                and previous.get("content_hash") == snapshot["content_hash"]
                and previous.get("status") == "ready"
                and not self._ready_runtime_issues(previous)
            ):
                return {**previous, "idempotent_reuse": True}
            activated_at = _utc_now()
            state = {
                **{key: value for key, value in snapshot.items() if key != "features"},
                "state_schema_version": SCENARIO_STATE_SCHEMA_VERSION,
                "activation_id": uuid.uuid4().hex,
                "activation_phase": "validated",
                "phase_updated_at": activated_at,
                "phase_history": [
                    {"phase": "validated", "recorded_at": activated_at}
                ],
                "status": "activating",
                "ready": False,
                "activated_at": activated_at,
                "containers": [],
                "activation_token": uuid.uuid4().hex,
            }
            self._publish_transition(state)
            self._persist_immutable_snapshot(snapshot)
            self._advance_activation(state, "snapshot_persisted")
            self._write_planner_config(snapshot["map_collection"], state["activation_token"])
            self._advance_activation(state, "planner_configured")
            reality_changed = True
            self._replace_previous_runtime(previous)
            self._advance_activation(state, "previous_runtime_stopped")
            self._clear_scenario_runtime_records()
            self._advance_activation(state, "runtime_records_cleared")
            self._restart_container(COORDINATION_CONTAINER, "centralized coordination")
            self._restart_planner()
            # The REST bridge and rosbridge are ROS participants even while
            # their HTTP/WebSocket listeners remain healthy. Restarting them
            # with the runtime prevents a stale DDS socket from silently
            # acknowledging Init without publishing it to coordination.
            self._restart_container(C2_REST_CONTAINER, "C2 REST bridge")
            self._restart_container(ROSBRIDGE_CONTAINER, "rosbridge")
            self._advance_activation(state, "backend_restarted")
            launched = launch_scenario(
                self.repo_root,
                payload,
                host_repo_root=self.host_repo_root,
                docker_socket=self.docker_socket,
            )
            if not launched.get("docker_started"):
                raise RuntimeError(str(launched.get("message") or "scenario robot containers did not start"))
            state["containers"] = launched.get("containers") or []
            self._advance_activation(state, "robots_launched")
            self._wait_until_ready(snapshot, state["containers"], state["activation_token"])
            self._advance_activation(state, "runtime_verified")
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
                        f"Scenario {snapshot['name']} is active. Planner uses immutable "
                        f"MapDB.{snapshot['map_collection']} and {len(state['agents'])} robot(s) are registered."
                    ),
                    "docker_started": True,
                }
            )
            self._advance_activation(state, "ready")
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
                    self._set_activation_phase(failed_attempt, "failed")
                    self._record_activation_best_effort(failed_attempt)
                if not previous.get("cache_diagnostic_only"):
                    self._publish_observed_state(previous)
                raise ScenarioNotReadyError(str(exc)) from exc
            state = state or {
                "scenario_id": str(payload.get("scenario_id") or "unknown"),
                "name": str(payload.get("name") or payload.get("scenario_id") or "unknown"),
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
            self._set_activation_phase(state, "failed")
            self._publish_observed_state(state)
            raise ScenarioNotReadyError(str(exc)) from exc
        finally:
            self._lock.release()

    def _persist_immutable_snapshot(self, snapshot: dict[str, Any]) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for scenario activation")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client.admin.command("ping")
                database = client["MapDB"]
                metadata = database[MAP_METADATA_COLLECTION]
                existing = metadata.find_one({"map_collection": snapshot["map_collection"]})
                collection = database[snapshot["map_collection"]]
                if existing:
                    if existing.get("content_hash") != snapshot["content_hash"]:
                        raise RuntimeError("immutable scenario collection hash mismatch")
                    if collection.count_documents({}) != snapshot["feature_count"]:
                        raise RuntimeError("immutable scenario collection contents were modified")
                    stored_features = list(collection.find({}, {"_id": 0}))
                    if _feature_content_hash(stored_features) != snapshot["map_feature_hash"]:
                        raise RuntimeError("immutable scenario collection contents were modified")
                    metadata.update_one(
                        {"map_collection": snapshot["map_collection"]},
                        {
                            "$set": {
                                "name": snapshot["name"],
                                "map": snapshot["map"],
                                "notes": snapshot["notes"],
                                "agents": deepcopy(snapshot["agents"]),
                                "feature_ids": deepcopy(snapshot["feature_ids"]),
                            }
                        },
                    )
                    self._ensure_snapshot_indexes(client, snapshot["map_collection"])
                    return
                if snapshot["map_collection"] in database.list_collection_names():
                    raise RuntimeError("scenario map collection exists without immutable version metadata")
                if snapshot["features"]:
                    collection.insert_many(deepcopy(snapshot["features"]))
                metadata.insert_one(
                    {
                        "scenario_id": snapshot["scenario_id"],
                        "name": snapshot["name"],
                        "map": snapshot["map"],
                        "notes": snapshot["notes"],
                        "agents": deepcopy(snapshot["agents"]),
                        "feature_ids": deepcopy(snapshot["feature_ids"]),
                        "version": snapshot["version"],
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
            raise RuntimeError(f"immutable scenario indexes are not ready: {details}")

    def _write_planner_config(self, collection: str, activation_token: str) -> None:
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
            r'(?m)^(\s*scenario_activation_token:\s*)[^#\n]+',
            rf'\1"{activation_token}"',
            text,
        )
        if token_replacements != 1:
            raise RuntimeError("planner config does not contain exactly one scenario_activation_token parameter")
        target = self.repo_root / "data" / "runtime" / PLANNER_CONFIG_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def _replace_previous_runtime(self, previous: dict[str, Any] | None) -> None:
        for container in previous.get("containers", []) if previous else []:
            name = str(container.get("container_name") or "")
            if name.startswith(("c2-imugs2-backend-scenario-", "c2-imugs2-scenario-")):
                _docker_request(self.docker_socket, "DELETE", f"/containers/{name}?force=true")
        _docker_request(self.docker_socket, "POST", f"/containers/{DEFAULT_EDGE_CONTAINER}/stop?t=10")

    def _clear_scenario_runtime_records(self) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for scenario activation")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client.admin.command("ping")
                for name in ("MissionFeedback", "Planning", "MissionConfig", "Logs", "ConnectedVehicles"):
                    client["RuntimeDB"][name].delete_many({})
                client["VehicleDB"]["Vehicles"].delete_many({})
        except PyMongoError as exc:
            raise RuntimeError(f"could not clear previous scenario runtime: {exc}") from exc

    def _clear_mission_runtime_records(self) -> None:
        if MongoClient is None:
            raise RuntimeError("pymongo is required for scenario activation")
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
        activation_token: str,
    ) -> None:
        expected = {_normalize_agent_id(str(agent.get("agent_id") or "")) for agent in snapshot["agents"]}
        marker = (
            f"MAP IS LOADED collection=MapDB.{snapshot['map_collection']} "
            f"activation={activation_token}"
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
            f"scenario readiness timed out; planner_marker={marker!r}, missing_registered_robots={missing}"
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
                issues.append("no scenario robot containers are recorded")
            for container in robot_containers:
                name = str(container.get("container_name") or "")
                if not self._container_running(name):
                    issues.append(f"scenario robot container {name or '<unnamed>'} is not running")
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
            activation_token = str(state.get("activation_token") or "")
            if collection_name and f'map_feature_collection: "{collection_name}"' not in config_text:
                issues.append("active planner configuration targets a different MapDB collection")
            if activation_token and f'scenario_activation_token: "{activation_token}"' not in config_text:
                issues.append("active planner configuration has a different activation token")
        return issues

    def _planner_readiness_issue(self, state: dict[str, Any]) -> str | None:
        """Require an exact planner proof without depending on an endless log tail.

        Activation records ``verified_at`` only after observing the exact
        collection/token marker.  Large planner JSON logs can later push that
        marker beyond Docker's bounded tail, so the proof remains valid while
        the same planner process (identified by ``StartedAt``) is still
        running.  A process started after verification must emit the marker
        again before it is trusted.
        """
        collection_name = str(state.get("map_collection") or "")
        activation_token = str(state.get("activation_token") or "")
        if not collection_name or not activation_token:
            return "planner collection or activation token is not recorded"
        marker = f"MAP IS LOADED collection=MapDB.{collection_name} activation={activation_token}"
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
        return "planner has not reported the active MapDB collection and activation token"

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
            raise RuntimeError("pymongo is required for scenario activation")
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client["MapDB"][ACTIVE_SCENARIO_COLLECTION].replace_one(
                    {"singleton": "active"},
                    {"singleton": "active", **deepcopy(state)},
                    upsert=True,
                )
        except PyMongoError as exc:
            raise RuntimeError(f"could not publish active scenario marker: {exc}") from exc

    def _record_activation(self, state: dict[str, Any]) -> None:
        activation_id = str(state.get("activation_id") or "")
        if not activation_id:
            return
        if MongoClient is None:
            raise RuntimeError("pymongo is required for scenario activation")
        record = deepcopy(state)
        record["recorded_at"] = _utc_now()
        try:
            with MongoClient(self.mongodb_url, serverSelectionTimeoutMS=3000) as client:
                client["MapDB"][ACTIVATION_COLLECTION].replace_one(
                    {"activation_id": activation_id},
                    record,
                    upsert=True,
                )
        except PyMongoError as exc:
            raise RuntimeError(f"could not persist scenario activation record: {exc}") from exc

    def _record_activation_best_effort(self, state: dict[str, Any]) -> None:
        try:
            self._record_activation(state)
        except RuntimeError:
            pass

    def _publish_transition(self, state: dict[str, Any]) -> None:
        """Durably publish a transition before updating the generated file cache."""
        self._record_activation(state)
        self._mark_active_in_mongo(state)
        self._save_state(state)

    def _publish_observed_state(self, state: dict[str, Any]) -> None:
        """Publish readiness observations, retaining diagnostics if Mongo is down."""
        try:
            self._record_activation(state)
            self._mark_active_in_mongo(state)
        except RuntimeError:
            pass
        self._save_state(state)

    def _advance_activation(self, state: dict[str, Any], phase: str) -> None:
        self._set_activation_phase(state, phase)
        self._publish_transition(state)

    @staticmethod
    def _set_activation_phase(state: dict[str, Any], phase: str) -> None:
        recorded_at = _utc_now()
        state["activation_phase"] = phase
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
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")[:48] or "scenario"


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
