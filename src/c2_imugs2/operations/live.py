from __future__ import annotations

from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import re
import threading
from typing import Any, Mapping, Protocol
import uuid

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from ..core.models import Behavior, MissionIssue, MissionRequest, MissionStatus
from .models import (
    Freshness,
    OperationalItem,
    OperationalReadModel,
    OperationalSection,
    SectionMetadata,
    SourceReference,
)


RUNTIME_MONGO_SOURCES = (
    "RuntimeDB.ConnectedVehicles",
    "VehicleDB.Vehicles",
    "RuntimeDB.MissionConfig",
    "RuntimeDB.MissionFeedback",
    "RuntimeDB.Planning",
)
ACTIVE_MAP_SOURCE = "MapDB.active"
MISSION_RELEVANT_MAP_FEATURE_TYPES = (
    "objective",
    "geofence",
    "workspace",
    "risk",
)
MAX_FEEDBACK_TASK_SUMMARIES = 64
DEFAULT_MAP_FEATURE_LIMIT = 64
DEFAULT_MAP_COORDINATE_LIMIT = 128
DEFAULT_MAP_TOTAL_COORDINATE_LIMIT = 512
_SAFE_MONGO_COLLECTION = re.compile(r"^[A-Za-z0-9._-]+$")
_URI_CREDENTIALS = re.compile(
    r"(?P<scheme>(?:mongodb(?:\+srv)?|https?)://)[^\s/@]+(?::[^\s/@]*)?@",
    flags=re.IGNORECASE,
)


class AdapterRuntime(Protocol):
    missions: Mapping[str, Mapping[str, Any]]
    forgotten_missions: set[str]
    agent_updates: Mapping[str, Mapping[str, Any]]
    planner_state: Mapping[str, Any]
    storage_bootstrap: Mapping[str, Any]


class WorldRuntime(Protocol):
    def validated_active(self) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class MongoOperationalSnapshot:
    """Small, prompt-safe facts read from backend databases in one pass."""

    connected: frozenset[str] = frozenset()
    registration_counts: Mapping[str, int] = field(default_factory=dict)
    profiles: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    configs: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    feedback: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    planning: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    map_collection: str | None = None
    map_features: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    map_feature_rows: int = 0
    map_features_truncated: bool = False
    invalid_map_feature_rows: int = 0
    errors: Mapping[str, str] = field(default_factory=dict)


class LiveOperationalReadModelProvider:
    """Build the bounded read model injected into every assistant invocation.

    Feedback and plans are reduced to counts by Mongo aggregation. Full plan
    geometry, objective payloads, waypoint arrays, and log bodies never cross
    this boundary. The exact active map contributes only bounded, validated
    Point or single-ring Polygon geometry for mission-relevant non-road
    features; oversized geometry remains an ID/type/count summary.
    """

    def __init__(
        self,
        runtime: AdapterRuntime,
        world_runtime: WorldRuntime,
        mongodb_url: str,
        *,
        mongo_timeout_ms: int = 400,
        mission_limit: int = 64,
        observation_limit: int = 256,
        agent_limit: int = 256,
        map_feature_limit: int = DEFAULT_MAP_FEATURE_LIMIT,
        map_coordinate_limit: int = DEFAULT_MAP_COORDINATE_LIMIT,
        map_total_coordinate_limit: int = DEFAULT_MAP_TOTAL_COORDINATE_LIMIT,
        mongo_client_factory: Callable[..., Any] = MongoClient,
    ) -> None:
        self.runtime = runtime
        self.world_runtime = world_runtime
        self.mongodb_url = mongodb_url
        self.mongo_timeout_ms = max(50, min(int(mongo_timeout_ms), 5_000))
        self.mission_limit = max(1, min(int(mission_limit), 256))
        self.observation_limit = max(
            self.mission_limit, min(int(observation_limit), 1_024)
        )
        self.agent_limit = max(1, min(int(agent_limit), 1_000))
        self.map_feature_limit = max(1, min(int(map_feature_limit), 256))
        self.map_coordinate_limit = max(4, min(int(map_coordinate_limit), 1_024))
        self.map_total_coordinate_limit = max(
            4, min(int(map_total_coordinate_limit), 4_096)
        )
        self.mongo_client_factory = mongo_client_factory
        self._stability_lock = threading.Lock()
        self._boundary_observations: dict[str, tuple[str, datetime]] = {}

    def read_operational_model(self) -> OperationalReadModel:
        observed_at = datetime.now(timezone.utc)
        active = self.world_runtime.validated_active()
        mongo = self._read_mongo_snapshot(active)
        model = OperationalReadModel(
            schema_version="1.0",
            observed_at=observed_at,
            sections={
                "world": self._world_section(observed_at, active, mongo),
                "agents": self._agents_section(observed_at, active, mongo),
                "missions": self._missions_section(observed_at, mongo),
                "plans": self._plans_section(observed_at, mongo),
                "health": self._health_section(observed_at, active, mongo),
                "warnings": self._warning_section(observed_at, active, mongo),
            },
            sources=self._sources(observed_at, active, mongo),
        )
        return self._with_stable_boundary_timestamps(model)

    def _read_mongo_snapshot(
        self, active: Mapping[str, Any] | None
    ) -> MongoOperationalSnapshot:
        errors: dict[str, str] = {}
        map_collection = _active_map_collection(active)
        try:
            context = self.mongo_client_factory(
                self.mongodb_url,
                serverSelectionTimeoutMS=self.mongo_timeout_ms,
                connectTimeoutMS=self.mongo_timeout_ms,
                socketTimeoutMS=self.mongo_timeout_ms,
            )
            with context as client:
                client.admin.command("ping")
                runtime = client["RuntimeDB"]
                vehicles = client["VehicleDB"]
                connected_rows = self._read_collection(
                    "RuntimeDB.ConnectedVehicles",
                    lambda: list(
                        runtime["ConnectedVehicles"]
                        .find({}, {"_id": 0, "agent_id": 1, "AgentId": 1})
                        .limit(self.agent_limit)
                    ),
                    errors,
                )
                profile_rows = self._read_collection(
                    "VehicleDB.Vehicles",
                    lambda: list(
                        vehicles["Vehicles"]
                        .find({}, _vehicle_profile_projection())
                        .limit(self.agent_limit)
                    ),
                    errors,
                )
                config_rows = self._read_collection(
                    "RuntimeDB.MissionConfig",
                    lambda: list(
                        runtime["MissionConfig"].aggregate(
                            _mission_config_pipeline(self.observation_limit),
                            maxTimeMS=self.mongo_timeout_ms,
                        )
                    ),
                    errors,
                )
                feedback_rows = self._read_collection(
                    "RuntimeDB.MissionFeedback",
                    lambda: list(
                        runtime["MissionFeedback"].aggregate(
                            _mission_feedback_pipeline(self.observation_limit),
                            maxTimeMS=self.mongo_timeout_ms,
                        )
                    ),
                    errors,
                )
                planning_rows = self._read_collection(
                    "RuntimeDB.Planning",
                    lambda: list(
                        runtime["Planning"].aggregate(
                            _planning_pipeline(self.observation_limit),
                            maxTimeMS=self.mongo_timeout_ms,
                        )
                    ),
                    errors,
                )
                map_rows: list[Mapping[str, Any]] = []
                if map_collection is not None:
                    map_rows = self._read_collection(
                        ACTIVE_MAP_SOURCE,
                        lambda: list(
                            client["MapDB"][map_collection].aggregate(
                                _active_map_feature_pipeline(
                                    self.map_feature_limit,
                                    self.map_coordinate_limit,
                                ),
                                maxTimeMS=self.mongo_timeout_ms,
                                allowDiskUse=False,
                            )
                        ),
                        errors,
                    )
        except (PyMongoError, OSError, TimeoutError) as exc:
            message = _bounded_error(exc)
            errors.update({source: message for source in RUNTIME_MONGO_SOURCES})
            if map_collection is not None:
                errors[ACTIVE_MAP_SOURCE] = message
            return MongoOperationalSnapshot(
                map_collection=map_collection,
                errors=errors,
            )

        registration_counts: dict[str, int] = {}
        for row in connected_rows:
            normalized = _normalize_agent_id(
                str(_alias(row, "agent_id", "AgentId") or "")
            )
            if normalized:
                registration_counts[normalized] = (
                    registration_counts.get(normalized, 0) + 1
                )
        connected = frozenset(registration_counts)
        profiles: dict[str, dict[str, Any]] = {}
        for row in profile_rows:
            agent_id = _normalize_agent_id(
                str(_alias(row, "agent_id", "AgentId") or "")
            )
            if agent_id and agent_id not in profiles:
                profiles[agent_id] = _profile_summary(row)
        map_features, map_rows_seen, map_truncated, invalid_map_rows = (
            _summarize_active_map_features(
                map_rows,
                self.map_feature_limit,
                self.map_coordinate_limit,
                self.map_total_coordinate_limit,
            )
        )
        return MongoOperationalSnapshot(
            connected=connected,
            registration_counts=registration_counts,
            profiles=profiles,
            configs=_latest_mission_summaries(
                config_rows, _summarize_config_document, self.mission_limit
            ),
            feedback=_latest_valid_feedback_summaries(
                feedback_rows, self.mission_limit
            ),
            planning=_latest_mission_summaries(
                planning_rows, _summarize_planning_document, self.mission_limit
            ),
            map_collection=map_collection,
            map_features=map_features,
            map_feature_rows=map_rows_seen,
            map_features_truncated=map_truncated,
            invalid_map_feature_rows=invalid_map_rows,
            errors=errors,
        )

    @staticmethod
    def _read_collection(
        source_id: str,
        reader: Callable[[], list[Mapping[str, Any]]],
        errors: dict[str, str],
    ) -> list[Mapping[str, Any]]:
        try:
            return reader()
        except (PyMongoError, OSError, TimeoutError) as exc:
            errors[source_id] = _bounded_error(exc)
            return []

    def _sources(
        self,
        observed_at: datetime,
        active: dict[str, Any] | None,
        mongo: MongoOperationalSnapshot,
    ) -> dict[str, SourceReference]:
        counts = {
            "RuntimeDB.ConnectedVehicles": sum(mongo.registration_counts.values()),
            "VehicleDB.Vehicles": len(mongo.profiles),
            "RuntimeDB.MissionConfig": len(mongo.configs),
            "RuntimeDB.MissionFeedback": len(mongo.feedback),
            "RuntimeDB.Planning": len(mongo.planning),
        }
        sources = {
            "adapter-runtime": SourceReference(
                "adapter-runtime", "fastapi_state", observed_at, Freshness.FRESH
            ),
            "world-runtime": SourceReference(
                "world-runtime",
                "validated_world_runtime",
                observed_at,
                _world_freshness(active),
                {"status": str((active or {}).get("status") or "inactive")},
            ),
            "planner-runtime": SourceReference(
                "planner-runtime", "normalized_planner_state", observed_at, Freshness.FRESH
            ),
            "storage-bootstrap": SourceReference(
                "storage-bootstrap",
                "mongo_index_bootstrap",
                observed_at,
                Freshness.FRESH,
                _json_mapping(self.runtime.storage_bootstrap),
            ),
        }
        for source_id in RUNTIME_MONGO_SOURCES:
            error = mongo.errors.get(source_id)
            registration_details: dict[str, Any] = {}
            if source_id == "RuntimeDB.ConnectedVehicles" and not error:
                registration_details = {
                    "unique_agent_ids": len(mongo.registration_counts),
                    "duplicate_registrations": sum(
                        max(0, count - 1)
                        for count in mongo.registration_counts.values()
                    ),
                }
            sources[source_id] = SourceReference(
                source_id,
                "mongodb_collection",
                observed_at,
                Freshness.MISSING if error else Freshness.FRESH,
                _without_none(
                    {
                        "error": error,
                        "bounded_rows": counts[source_id],
                        **registration_details,
                        "observation_limit": (
                            self.agent_limit
                            if source_id
                            in {"RuntimeDB.ConnectedVehicles", "VehicleDB.Vehicles"}
                            else self.observation_limit
                        ),
                    }
                ),
            )
        map_error = mongo.errors.get(ACTIVE_MAP_SOURCE)
        if mongo.map_collection is None:
            map_freshness = Freshness.MISSING
            map_details: dict[str, Any] = {
                "reason": "no active map binding",
                "bounded_rows": 0,
                "feature_limit": self.map_feature_limit,
                "geometry_coordinate_limit": self.map_coordinate_limit,
                "total_geometry_coordinate_limit": self.map_total_coordinate_limit,
            }
        else:
            map_freshness = (
                Freshness.MISSING
                if map_error
                else Freshness.STALE
                if mongo.invalid_map_feature_rows
                else Freshness.FRESH
            )
            map_details = _without_none(
                {
                    "database": "MapDB",
                    "collection": mongo.map_collection,
                    "error": map_error,
                    "bounded_rows": mongo.map_feature_rows,
                    "returned_features": len(mongo.map_features),
                    "invalid_rows": mongo.invalid_map_feature_rows,
                    "feature_limit": self.map_feature_limit,
                    "geometry_coordinate_limit": self.map_coordinate_limit,
                    "total_geometry_coordinate_limit": self.map_total_coordinate_limit,
                    "truncated": mongo.map_features_truncated,
                    "projection": "mission-relevant non-road feature summaries",
                    "allow_disk_use": False,
                }
            )
        sources[ACTIVE_MAP_SOURCE] = SourceReference(
            ACTIVE_MAP_SOURCE,
            "mongodb_active_map_projection",
            observed_at,
            map_freshness,
            map_details,
        )
        return sources

    def _world_section(
        self,
        observed_at: datetime,
        active: dict[str, Any] | None,
        mongo: MongoOperationalSnapshot,
    ) -> OperationalSection:
        binding_freshness = _world_freshness(active)
        map_expected = active is not None
        map_error = bool(
            map_expected
            and (
                mongo.map_collection is None
                or ACTIVE_MAP_SOURCE in mongo.errors
            )
        )
        map_stale = bool(mongo.invalid_map_feature_rows)
        freshness = (
            Freshness.STALE
            if binding_freshness is Freshness.FRESH and (map_error or map_stale)
            else binding_freshness
        )
        section_sources = (
            ("world-runtime", ACTIVE_MAP_SOURCE)
            if map_expected
            else ("world-runtime",)
        )
        items: dict[str, OperationalItem] = {}
        if active:
            world_id = str(active.get("world_id") or "active")
            version = str(active["world_version"]) if active.get("world_version") is not None else ""
            item_id = f"{world_id}@{version}" if version else world_id
            agents = active.get("agents") if isinstance(active.get("agents"), list) else []
            data = {
                "world_id": world_id,
                "name": active.get("name"),
                "status": active.get("status"),
                "ready": bool(active.get("ready")),
                "world_version": active.get("world_version"),
                "content_hash": active.get("content_hash"),
                "map": active.get("map"),
                "map_collection": active.get("map_collection"),
                "map_feature_hash": active.get("map_feature_hash"),
                "feature_count": active.get("feature_count"),
                "road_count": active.get("road_count"),
                "launch_id": active.get("launch_id"),
                "deployment_id": active.get("deployment_id"),
                "map_snapshot_token": active.get("map_snapshot_token"),
                "launch_phase": active.get("launch_phase"),
                "agent_ids": [
                    str(agent.get("agent_id"))
                    for agent in agents
                    if isinstance(agent, dict) and agent.get("agent_id")
                ],
                "message": active.get("message"),
                "error": active.get("error"),
                "map_features": _active_picture_features(
                    mongo.map_features,
                    active,
                    self.map_feature_limit,
                    self.map_coordinate_limit,
                ),
                "map_feature_observation": {
                    "freshness": (
                        Freshness.MISSING.value
                        if map_error
                        else Freshness.STALE.value
                        if map_stale
                        else Freshness.FRESH.value
                    ),
                    "returned_count": len(mongo.map_features),
                    "observed_row_count": mongo.map_feature_rows,
                    "invalid_row_count": mongo.invalid_map_feature_rows,
                    "feature_limit": self.map_feature_limit,
                    "geometry_coordinate_limit": self.map_coordinate_limit,
                    "total_geometry_coordinate_limit": self.map_total_coordinate_limit,
                    "truncated": mongo.map_features_truncated,
                },
            }
            items[item_id] = OperationalItem(
                item_id,
                "active_world",
                observed_at,
                freshness,
                _without_none(data),
                section_sources,
            )
        return OperationalSection(
            SectionMetadata(observed_at, freshness, section_sources), items
        )

    def _agents_section(
        self,
        observed_at: datetime,
        active: dict[str, Any] | None,
        mongo: MongoOperationalSnapshot,
    ) -> OperationalSection:
        declared = (
            active.get("agents")
            if active and isinstance(active.get("agents"), list)
            else []
        )
        items: dict[str, OperationalItem] = {}
        connectivity_missing = "RuntimeDB.ConnectedVehicles" in mongo.errors
        profiles_missing = "VehicleDB.Vehicles" in mongo.errors
        fleet_incomplete = connectivity_missing or profiles_missing
        for raw in declared[: self.agent_limit]:
            if not isinstance(raw, dict) or not raw.get("agent_id"):
                continue
            agent_id = str(raw["agent_id"])
            normalized = _normalize_agent_id(agent_id)
            update = next(
                (
                    value
                    for key, value in self.runtime.agent_updates.items()
                    if _normalize_agent_id(key) == normalized
                ),
                {},
            )
            data = {
                "agent_id": agent_id,
                "name": raw.get("name"),
                "vehicle_type": raw.get("vehicle_type"),
                "declared_status": raw.get("status"),
                "connected": (
                    None if connectivity_missing else normalized in mongo.connected
                ),
                "registration_count": (
                    None
                    if connectivity_missing
                    else mongo.registration_counts.get(normalized, 0)
                ),
                "current_location": update.get("current_location")
                or raw.get("current_location"),
                "runtime_status": update.get("status"),
                "constraints": raw.get("constraints") or {},
                "capabilities": raw.get("capabilities") or [],
                "advertised_profile": mongo.profiles.get(normalized),
            }
            items[agent_id] = OperationalItem(
                agent_id,
                "world_agent",
                observed_at,
                Freshness.STALE if fleet_incomplete else Freshness.FRESH,
                _json_mapping(_without_none(data)),
                (
                    "world-runtime",
                    "RuntimeDB.ConnectedVehicles",
                    "VehicleDB.Vehicles",
                    "adapter-runtime",
                ),
            )
        freshness = (
            Freshness.MISSING
            if fleet_incomplete and not items
            else Freshness.STALE
            if fleet_incomplete
            else Freshness.FRESH
        )
        return OperationalSection(
            SectionMetadata(
                observed_at,
                freshness,
                (
                    "world-runtime",
                    "RuntimeDB.ConnectedVehicles",
                    "VehicleDB.Vehicles",
                    "adapter-runtime",
                ),
            ),
            items,
        )

    def _missions_section(
        self, observed_at: datetime, mongo: MongoOperationalSnapshot
    ) -> OperationalSection:
        adapter = {
            _normalize_mission_id(mission_id): mission
            for mission_id, mission in self.runtime.missions.items()
            if _normalize_mission_id(mission_id)
        }
        forgotten = {
            _normalize_mission_id(value) for value in self.runtime.forgotten_missions
        }
        mission_ids = _bounded_union(
            (adapter, mongo.feedback, mongo.planning, mongo.configs), self.mission_limit
        )
        items: dict[str, OperationalItem] = {}
        mission_sources = (
            "adapter-runtime",
            "RuntimeDB.MissionConfig",
            "RuntimeDB.MissionFeedback",
            "RuntimeDB.Planning",
        )
        mongo_error = any(source in mongo.errors for source in mission_sources[1:])
        for mission_id in mission_ids:
            if mission_id in forgotten:
                continue
            runtime_mission = adapter.get(mission_id)
            config = mongo.configs.get(mission_id)
            feedback = mongo.feedback.get(mission_id)
            planning = mongo.planning.get(mission_id)
            adapter_summary = _adapter_mission_summary(runtime_mission)
            effective_status = (
                feedback.get("status")
                if feedback is not None
                else adapter_summary.get("status")
            )
            effective_status_name = (
                feedback.get("status_name")
                if feedback is not None
                else adapter_summary.get("status_name")
            )
            data = {
                "mission_id": mission_id,
                "adapter_state": adapter_summary or None,
                "backend_config": config,
                "backend_feedback": feedback,
                "backend_planning": planning,
                "effective_status": effective_status,
                "effective_status_name": effective_status_name,
                "effective_status_source": (
                    "RuntimeDB.MissionFeedback"
                    if feedback is not None
                    else "adapter-runtime"
                ),
            }
            sources = tuple(
                source
                for source, present in (
                    ("adapter-runtime", runtime_mission is not None),
                    ("RuntimeDB.MissionConfig", config is not None),
                    ("RuntimeDB.MissionFeedback", feedback is not None),
                    ("RuntimeDB.Planning", planning is not None),
                )
                if present
            )
            freshness = (
                Freshness.STALE
                if mongo_error and runtime_mission is not None
                else Freshness.FRESH
                if sources
                else Freshness.MISSING
            )
            items[mission_id] = OperationalItem(
                mission_id,
                "mission",
                observed_at,
                freshness,
                _json_mapping(_without_none(data)),
                sources or ("adapter-runtime",),
            )
        return OperationalSection(
            SectionMetadata(
                observed_at,
                Freshness.STALE if mongo_error else Freshness.FRESH,
                mission_sources,
            ),
            items,
        )

    def _plans_section(
        self, observed_at: datetime, mongo: MongoOperationalSnapshot
    ) -> OperationalSection:
        runtime_plans = _runtime_planner_summaries(self.runtime.planner_state)
        plan_ids = _bounded_union((runtime_plans, mongo.planning), self.mission_limit)
        items: dict[str, OperationalItem] = {}
        planning_error = "RuntimeDB.Planning" in mongo.errors
        for mission_id in plan_ids:
            runtime_plan = runtime_plans.get(mission_id)
            backend_plan = mongo.planning.get(mission_id)
            sources = tuple(
                source
                for source, present in (
                    ("planner-runtime", runtime_plan is not None),
                    ("RuntimeDB.Planning", backend_plan is not None),
                )
                if present
            )
            items[mission_id] = OperationalItem(
                mission_id,
                "planner_summary",
                observed_at,
                (
                    Freshness.STALE
                    if planning_error and runtime_plan is not None
                    else Freshness.FRESH
                ),
                _json_mapping(
                    _without_none(
                        {
                            "mission_id": mission_id,
                            "runtime_planner": runtime_plan,
                            "backend_planning": backend_plan,
                        }
                    )
                ),
                sources or ("planner-runtime",),
            )
        return OperationalSection(
            SectionMetadata(
                observed_at,
                Freshness.STALE if planning_error else Freshness.FRESH,
                ("planner-runtime", "RuntimeDB.Planning"),
            ),
            items,
        )

    def _health_section(
        self,
        observed_at: datetime,
        active: dict[str, Any] | None,
        mongo: MongoOperationalSnapshot,
    ) -> OperationalSection:
        mongo_ok = not mongo.errors
        items = {
            "world": OperationalItem(
                "world",
                "health_check",
                observed_at,
                _world_freshness(active),
                {
                    "ok": bool(active and active.get("ready")),
                    "status": str((active or {}).get("status") or "inactive"),
                },
                ("world-runtime",),
            ),
            "mongodb": OperationalItem(
                "mongodb",
                "health_check",
                observed_at,
                Freshness.FRESH if mongo_ok else Freshness.STALE,
                {"ok": mongo_ok, "unavailable_sources": sorted(mongo.errors)},
                RUNTIME_MONGO_SOURCES,
            ),
            "storage-indexes": OperationalItem(
                "storage-indexes",
                "health_check",
                observed_at,
                Freshness.FRESH,
                _json_mapping(self.runtime.storage_bootstrap),
                ("storage-bootstrap",),
            ),
        }
        return OperationalSection(
            SectionMetadata(
                observed_at,
                Freshness.FRESH if mongo_ok else Freshness.STALE,
                ("world-runtime", *RUNTIME_MONGO_SOURCES, "storage-bootstrap"),
            ),
            items,
        )

    def _warning_section(
        self,
        observed_at: datetime,
        active: dict[str, Any] | None,
        mongo: MongoOperationalSnapshot,
    ) -> OperationalSection:
        items: dict[str, OperationalItem] = {}
        if not active or not active.get("ready"):
            items["world-not-ready"] = _warning(
                "world-not-ready",
                observed_at,
                str(
                    (active or {}).get("error")
                    or (active or {}).get("message")
                    or "The current operating environment is not ready"
                ),
                ("world-runtime",),
            )
        for source_id, error in sorted(mongo.errors.items()):
            slug = source_id.lower().replace(".", "-")
            item_id = f"source-unavailable:{slug}"
            items[item_id] = _warning(
                item_id,
                observed_at,
                f"{source_id} is unavailable: {error}",
                (source_id,),
            )
        if mongo.map_features_truncated:
            items["active-map-features-truncated"] = _warning(
                "active-map-features-truncated",
                observed_at,
                (
                    "Operating-area feature facts reached the configured limit "
                    f"of {self.map_feature_limit}; additional features are omitted"
                ),
                (ACTIVE_MAP_SOURCE,),
            )
        if mongo.invalid_map_feature_rows:
            items["active-map-features-invalid"] = _warning(
                "active-map-features-invalid",
                observed_at,
                (
                    f"{mongo.invalid_map_feature_rows} operating-area feature "
                    "record(s) had invalid mission geometry"
                ),
                (ACTIVE_MAP_SOURCE,),
            )
        connectivity_error = "RuntimeDB.ConnectedVehicles" in mongo.errors
        if not connectivity_error:
            for agent_id, registration_count in sorted(
                mongo.registration_counts.items()
            ):
                if registration_count <= 1:
                    continue
                item_id = f"duplicate-agent-registration:{agent_id}"
                items[item_id] = _warning(
                    item_id,
                    observed_at,
                    (
                        f"Agent {agent_id} has {registration_count} active "
                        "ConnectedVehicles registration records in the bounded sample"
                    ),
                    ("RuntimeDB.ConnectedVehicles",),
                )
        if active and not connectivity_error:
            declared = {
                _normalize_agent_id(str(agent.get("agent_id") or ""))
                for agent in active.get("agents") or []
                if isinstance(agent, dict) and agent.get("agent_id")
            }
            missing = sorted(declared - mongo.connected)
            if missing:
                items["agents-not-registered"] = _warning(
                    "agents-not-registered",
                    observed_at,
                    f"Configured agents are not registered: {', '.join(missing)}",
                    ("world-runtime", "RuntimeDB.ConnectedVehicles"),
                )
        adapter = {
            _normalize_mission_id(mission_id): mission
            for mission_id, mission in self.runtime.missions.items()
            if _normalize_mission_id(mission_id)
        }
        for mission_id in _bounded_union(
            (adapter, mongo.feedback, mongo.planning), self.mission_limit
        ):
            runtime_mission = adapter.get(mission_id)
            feedback = mongo.feedback.get(mission_id)
            planning = mongo.planning.get(mission_id)
            if feedback and feedback.get("skipped_newer_invalid_candidates"):
                skipped = int(feedback["skipped_newer_invalid_candidates"])
                item_id = f"invalid-newer-feedback:{mission_id}"
                items[item_id] = _warning(
                    item_id,
                    observed_at,
                    (
                        f"Mission {mission_id} uses the next newest valid feedback "
                        f"after skipping {skipped} invalid candidate(s)"
                    ),
                    ("RuntimeDB.MissionFeedback",),
                )
            backend_command = _backend_command_summary(runtime_mission)
            if backend_command is not None and backend_command.get("ok") is False:
                item_id = f"backend-command-failed:{mission_id}"
                items[item_id] = _warning(
                    item_id,
                    observed_at,
                    (
                        f"The latest backend command for mission {mission_id} failed "
                        f"with status {backend_command.get('status_code', 'unknown')}"
                    ),
                    ("adapter-runtime",),
                )
            if runtime_mission is not None and feedback is not None:
                adapter_status = _integer_or_value(runtime_mission.get("status"))
                feedback_status = _integer_or_value(feedback.get("status"))
                if (
                    adapter_status is not None
                    and feedback_status is not None
                    and adapter_status != feedback_status
                ):
                    item_id = f"mission-status-divergence:{mission_id}"
                    items[item_id] = _warning(
                        item_id,
                        observed_at,
                        (
                            f"Mission {mission_id} adapter status {adapter_status} differs "
                            f"from authoritative feedback status {feedback_status}"
                        ),
                        ("adapter-runtime", "RuntimeDB.MissionFeedback"),
                    )
            if (
                planning
                and planning.get("has_paths")
                and feedback
                and not feedback.get("has_paths")
            ):
                item_id = f"plan-not-in-feedback:{mission_id}"
                items[item_id] = _warning(
                    item_id,
                    observed_at,
                    f"Mission {mission_id} has a stored plan but no paths in its latest feedback",
                    ("RuntimeDB.Planning", "RuntimeDB.MissionFeedback"),
                )
        freshness = Freshness.FRESH if not items else Freshness.STALE
        sources = tuple(
            sorted({source for item in items.values() for source in item.source_ids})
        )
        return OperationalSection(
            SectionMetadata(observed_at, freshness, sources), items
        )

    def _with_stable_boundary_timestamps(
        self, model: OperationalReadModel
    ) -> OperationalReadModel:
        """Retain timestamps for unchanged diffable object boundaries."""

        with self._stability_lock:
            next_cache: dict[str, tuple[str, datetime]] = {}

            def stable(path: str, payload: Mapping[str, Any]) -> datetime:
                signature = json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    default=str,
                )
                previous = self._boundary_observations.get(path)
                timestamp = (
                    previous[1]
                    if previous is not None and previous[0] == signature
                    else model.observed_at
                )
                next_cache[path] = (signature, timestamp)
                return timestamp

            sources: dict[str, SourceReference] = {}
            for source_id, source in model.sources.items():
                payload = {
                    "kind": source.kind,
                    "freshness": source.freshness.value,
                    "details": source.details,
                }
                sources[source_id] = SourceReference(
                    source.source_id,
                    source.kind,
                    stable(f"sources/{source_id}", payload),
                    source.freshness,
                    source.details,
                )

            sections: dict[str, OperationalSection] = {}
            for section_name, section in model.sections.items():
                metadata_payload = {
                    "freshness": section.metadata.freshness.value,
                    "source_ids": section.metadata.source_ids,
                }
                metadata = SectionMetadata(
                    stable(f"section_metadata/{section_name}", metadata_payload),
                    section.metadata.freshness,
                    section.metadata.source_ids,
                )
                items: dict[str, OperationalItem] = {}
                for item_id, item in section.items.items():
                    item_payload = {
                        "kind": item.kind,
                        "freshness": item.freshness.value,
                        "source_ids": item.source_ids,
                        "data": item.data,
                    }
                    items[item_id] = OperationalItem(
                        item.item_id,
                        item.kind,
                        stable(f"{section_name}/{item_id}", item_payload),
                        item.freshness,
                        item.data,
                        item.source_ids,
                    )
                sections[section_name] = OperationalSection(metadata, items)
            self._boundary_observations = next_cache
        return OperationalReadModel(
            model.schema_version, model.observed_at, sections, sources
        )


def _active_map_feature_pipeline(
    limit: int, coordinate_limit: int
) -> list[dict[str, Any]]:
    """Project exact small mission features without returning arbitrary geometry."""

    safe_coordinates = {
        "$cond": [
            {"$isArray": "$geometry.coordinates"},
            "$geometry.coordinates",
            [],
        ]
    }
    first_ring = {
        "$cond": [
            {"$gt": [{"$size": safe_coordinates}, 0]},
            {"$arrayElemAt": [safe_coordinates, 0]},
            [],
        ]
    }
    safe_first_ring = {
        "$cond": [{"$isArray": first_ring}, first_ring, []]
    }

    def position_valid(position: Any) -> dict[str, Any]:
        safe_position = {
            "$cond": [{"$isArray": position}, position, []]
        }
        return {
            "$and": [
                {"$eq": [{"$size": safe_position}, 2]},
                {
                    "$allElementsTrue": [
                        {
                            "$map": {
                                "input": safe_position,
                                "as": "coordinate",
                                "in": {
                                    "$in": [
                                        {"$type": "$$coordinate"},
                                        ["double", "int", "long", "decimal"],
                                    ]
                                },
                            }
                        }
                    ]
                },
            ]
        }

    point_valid = {
        "$and": [
            {"$eq": ["$geometry.type", "Point"]},
            position_valid(safe_coordinates),
        ]
    }
    polygon_valid = {
        "$and": [
            {"$eq": ["$geometry.type", "Polygon"]},
            {"$eq": [{"$size": safe_coordinates}, 1]},
            {"$gte": [{"$size": safe_first_ring}, 4]},
            {"$lte": [{"$size": safe_first_ring}, coordinate_limit]},
            {
                "$allElementsTrue": [
                    {
                        "$map": {
                            "input": {
                                "$slice": [
                                    safe_first_ring,
                                    coordinate_limit,
                                ]
                            },
                            "as": "position",
                            "in": position_valid("$$position"),
                        }
                    }
                ]
            },
        ]
    }
    geometry_complete = {"$or": [point_valid, polygon_valid]}
    return [
        {
            "$match": {
                "properties.feature_type": {
                    "$in": list(MISSION_RELEVANT_MAP_FEATURE_TYPES)
                }
            }
        },
        {
            "$sort": {
                "properties.feature_type": 1,
                "properties.feature_id": 1,
                "id": 1,
            }
        },
        {"$limit": limit + 1},
        {
            "$project": {
                "_id": 0,
                "feature_id": {
                    "$ifNull": ["$properties.feature_id", "$id"]
                },
                "name": "$properties.name",
                "feature_type": "$properties.feature_type",
                "feature_source": "$properties.source",
                "geometry_type": "$geometry.type",
                "coordinate_count": {
                    "$switch": {
                        "branches": [
                            {
                                "case": {"$eq": ["$geometry.type", "Point"]},
                                "then": {"$size": safe_coordinates},
                            },
                            {
                                "case": {"$eq": ["$geometry.type", "Polygon"]},
                                "then": {"$size": safe_first_ring},
                            },
                        ],
                        "default": 0,
                    }
                },
                "geometry_complete": geometry_complete,
                "geometry_coordinates": {
                    "$cond": [geometry_complete, safe_coordinates, None]
                },
            }
        },
    ]


def _mission_config_pipeline(limit: int) -> list[dict[str, Any]]:
    return [
        {"$sort": {"_id": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 1,
                "mission_id": {"$ifNull": ["$mission_id", "$MissionId"]},
                "name": {"$ifNull": ["$name", "$Name"]},
                "behavior": {"$ifNull": ["$behavior", "$Behavior"]},
                "vehicle_ids": {
                    "$ifNull": ["$vehicles", {"$ifNull": ["$Vehicles", []]}]
                },
                "date": {
                    "$ifNull": ["$updated_at", {"$ifNull": ["$date", "$Date"]}]
                },
            }
        },
    ]


def _mission_feedback_pipeline(limit: int) -> list[dict[str, Any]]:
    tasks = {
        "$cond": [
            {"$isArray": "$tasks"},
            "$tasks",
            {"$cond": [{"$isArray": "$Tasks"}, "$Tasks", []]},
        ]
    }
    waypoints = {
        "$cond": [
            {"$isArray": "$$task.waypoints"},
            "$$task.waypoints",
            {
                "$cond": [
                    {"$isArray": "$$task.Waypoints"},
                    "$$task.Waypoints",
                    [],
                ]
            },
        ]
    }
    agent_id = {
        "$ifNull": [
            "$$task.vehicle_id",
            {
                "$ifNull": [
                    "$$task.VehicleId",
                    {"$ifNull": ["$$task.agent_id", "$$task.AgentId"]},
                ]
            },
        ]
    }
    no_task_field = {
        "$and": [
            {"$in": [{"$type": "$tasks"}, ["missing", "null"]]},
            {"$in": [{"$type": "$Tasks"}, ["missing", "null"]]},
        ]
    }
    no_waypoint_field = {
        "$and": [
            {
                "$in": [
                    {"$type": "$$task.waypoints"},
                    ["missing", "null"],
                ]
            },
            {
                "$in": [
                    {"$type": "$$task.Waypoints"},
                    ["missing", "null"],
                ]
            },
        ]
    }
    task_shape_valid = {
        "$and": [
            {"$eq": [{"$type": "$$task"}, "object"]},
            {"$eq": [{"$type": agent_id}, "string"]},
            {"$ne": [agent_id, ""]},
            {
                "$or": [
                    {"$isArray": "$$task.waypoints"},
                    {"$isArray": "$$task.Waypoints"},
                    no_waypoint_field,
                ]
            },
        ]
    }
    tasks_shape_valid = {
        "$and": [
            {
                "$or": [
                    {"$isArray": "$tasks"},
                    {"$isArray": "$Tasks"},
                    no_task_field,
                ]
            },
            {
                "$allElementsTrue": [
                    {
                        "$map": {
                            "input": {
                                "$slice": [tasks, MAX_FEEDBACK_TASK_SUMMARIES]
                            },
                            "as": "task",
                            "in": task_shape_valid,
                        }
                    }
                ]
            },
        ]
    }
    return [
        {"$sort": {"_id": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 1,
                "mission_id": {"$ifNull": ["$mission_id", "$MissionId"]},
                "behavior": {"$ifNull": ["$behavior", "$Behavior"]},
                "status": {"$ifNull": ["$status", "$Status"]},
                "requested_status": {
                    "$ifNull": ["$requested_status", "$RequestedStatus"]
                },
                "issue": {"$ifNull": ["$issue", "$Issue"]},
                "date": {"$ifNull": ["$date", "$Date"]},
                "task_count": {"$size": tasks},
                "tasks_truncated": {
                    "$gt": [{"$size": tasks}, MAX_FEEDBACK_TASK_SUMMARIES]
                },
                "tasks_shape_valid": tasks_shape_valid,
                "task_summaries": {
                    "$map": {
                        "input": {
                            "$slice": [tasks, MAX_FEEDBACK_TASK_SUMMARIES]
                        },
                        "as": "task",
                        "in": {
                            "agent_id": agent_id,
                            "waypoint_count": {"$size": waypoints},
                        },
                    }
                },
            }
        },
    ]


def _planning_pipeline(limit: int) -> list[dict[str, Any]]:
    tasks = {
        "$cond": [
            {"$eq": [{"$type": "$tasks"}, "object"]},
            {"$objectToArray": "$tasks"},
            {
                "$cond": [
                    {"$eq": [{"$type": "$Tasks"}, "object"]},
                    {"$objectToArray": "$Tasks"},
                    [],
                ]
            },
        ]
    }
    objectives = {
        "$cond": [
            {"$isArray": "$$task.v.objectives"},
            "$$task.v.objectives",
            {
                "$cond": [
                    {"$isArray": "$$task.v.Objectives"},
                    "$$task.v.Objectives",
                    [],
                ]
            },
        ]
    }
    primitives = {
        "$cond": [
            {"$isArray": "$$this.primitives"},
            "$$this.primitives",
            {
                "$cond": [
                    {"$isArray": "$$this.Primitives"},
                    "$$this.Primitives",
                    [],
                ]
            },
        ]
    }
    waypoint_primitives = {
        "$filter": {
            "input": primitives,
            "as": "primitive",
            "cond": {
                "$or": [
                    {"$isArray": "$$primitive.parameters.coordinates"},
                    {"$isArray": "$$primitive.Parameters.Coordinates"},
                ]
            },
        }
    }
    return [
        {"$sort": {"_id": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 1,
                "mission_id": {"$ifNull": ["$mission_id", "$MissionId"]},
                "status": {"$ifNull": ["$status", "$Status"]},
                "date": {
                    "$ifNull": ["$updated_at", {"$ifNull": ["$date", "$Date"]}]
                },
                "task_summaries": {
                    "$map": {
                        "input": tasks,
                        "as": "task",
                        "in": {
                            "agent_id": "$$task.k",
                            "waypoint_count": {
                                "$reduce": {
                                    "input": objectives,
                                    "initialValue": 0,
                                    "in": {
                                        "$add": [
                                            "$$value",
                                            {"$size": waypoint_primitives},
                                        ]
                                    },
                                }
                            },
                        },
                    }
                },
            }
        },
    ]


def _vehicle_profile_projection() -> dict[str, int]:
    return {
        "_id": 0,
        "agent_id": 1,
        "AgentId": 1,
        "name": 1,
        "Name": 1,
        "vehicle_type": 1,
        "VehicleType": 1,
        "status": 1,
        "Status": 1,
        "current_location": 1,
        "localization": 1,
        "constraints": 1,
        "capabilities": 1,
    }


def _active_map_collection(active: Mapping[str, Any] | None) -> str | None:
    if not isinstance(active, Mapping):
        return None
    value = active.get("map_collection")
    if not isinstance(value, str):
        return None
    collection = value.strip()
    if not collection or not _SAFE_MONGO_COLLECTION.fullmatch(collection):
        return None
    return collection


def _active_picture_features(
    stored: Mapping[str, Mapping[str, Any]],
    active: Mapping[str, Any],
    limit: int,
    coordinate_limit: int,
) -> list[dict[str, Any]]:
    """Project only the immutable active snapshot and this deployment's overlays."""
    merged = {str(key): dict(value) for key, value in stored.items()}
    deployment_id = str(active.get("deployment_id") or "")
    live_features = [
        row
        for row in (active.get("live_features") or {}).get("features") or []
        if isinstance(row, Mapping)
        and str((row.get("properties") or {}).get("deployment_id") or "") == deployment_id
    ]
    sources = [(active.get("snapshot") or {}).get("features") or [], live_features]
    for rows in sources:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            summary, _valid = _summarize_active_map_feature(row, coordinate_limit)
            if summary is None:
                continue
            merged[str(summary["feature_id"])] = summary
    return [merged[key] for key in sorted(merged)[:limit]]


def _summarize_active_map_features(
    rows: Iterable[Mapping[str, Any]],
    limit: int,
    coordinate_limit: int,
    total_coordinate_limit: int,
) -> tuple[dict[str, dict[str, Any]], int, bool, int]:
    features: dict[str, dict[str, Any]] = {}
    observed_rows = 0
    invalid_rows = 0
    truncated = False
    included_coordinates = 0
    for row in rows:
        observed_rows += 1
        if observed_rows > limit:
            truncated = True
            break
        summary, valid = _summarize_active_map_feature(row, coordinate_limit)
        if summary is None:
            invalid_rows += 1
            continue
        if "geometry" in summary:
            coordinate_count = int(summary["coordinate_count"])
            if included_coordinates + coordinate_count > total_coordinate_limit:
                summary.pop("geometry")
                summary["geometry_status"] = "omitted_picture_budget"
            else:
                included_coordinates += coordinate_count
        feature_id = str(summary["feature_id"])
        if feature_id in features:
            invalid_rows += 1
            continue
        features[feature_id] = summary
        if not valid:
            invalid_rows += 1
    return (
        {feature_id: features[feature_id] for feature_id in sorted(features)},
        observed_rows,
        truncated,
        invalid_rows,
    )


def _summarize_active_map_feature(
    document: Mapping[str, Any], coordinate_limit: int
) -> tuple[dict[str, Any] | None, bool]:
    properties = (
        document.get("properties")
        if isinstance(document.get("properties"), Mapping)
        else {}
    )
    raw_id = _alias(document, "feature_id", "id") or properties.get("feature_id")
    if not isinstance(raw_id, str) or not raw_id.strip() or len(raw_id.strip()) > 256:
        return None, False
    feature_id = raw_id.strip()
    raw_type = _alias(document, "feature_type") or properties.get("feature_type")
    feature_type = str(raw_type or "").strip().lower()
    if feature_type not in MISSION_RELEVANT_MAP_FEATURE_TYPES:
        return None, False
    raw_name = _alias(document, "name") or properties.get("name") or feature_id
    name = str(raw_name).strip()[:160] or feature_id
    raw_origin = _alias(document, "feature_source") or properties.get("source")
    origin = str(raw_origin).strip()[:80] if raw_origin is not None else None

    geometry = (
        document.get("geometry")
        if isinstance(document.get("geometry"), Mapping)
        else {}
    )
    geometry_type = _alias(document, "geometry_type") or geometry.get("type")
    coordinates = (
        document.get("geometry_coordinates")
        if "geometry_coordinates" in document
        else geometry.get("coordinates")
    )
    projected_complete = document.get("geometry_complete")
    projected_count = _strict_nonnegative_int(document.get("coordinate_count"))
    exact_geometry, coordinate_count = _canonical_map_geometry(
        feature_type,
        geometry_type,
        coordinates,
        coordinate_limit,
    )
    if projected_count is not None:
        coordinate_count = projected_count
    if exact_geometry is not None and projected_complete is not False:
        geometry_status = "exact"
        valid = True
    elif coordinate_count > coordinate_limit:
        geometry_status = "omitted_coordinate_limit"
        exact_geometry = None
        valid = True
    else:
        geometry_status = "invalid"
        exact_geometry = None
        valid = False
    return (
        _without_none(
            {
                "feature_id": feature_id,
                "name": name,
                "feature_type": feature_type,
                "origin": origin or None,
                "geometry_status": geometry_status,
                "coordinate_count": coordinate_count,
                "geometry": exact_geometry,
                "freshness": (
                    Freshness.FRESH.value if valid else Freshness.STALE.value
                ),
                "provenance": "active operating map",
                "source_id": ACTIVE_MAP_SOURCE,
            }
        ),
        valid,
    )


def _canonical_map_geometry(
    feature_type: str,
    geometry_type: Any,
    coordinates: Any,
    coordinate_limit: int,
) -> tuple[dict[str, Any] | None, int]:
    expected_geometry = {
        "objective": "Point",
        "geofence": "Polygon",
        "workspace": "Polygon",
        "risk": "Polygon",
    }.get(feature_type)
    if geometry_type != expected_geometry:
        return None, _map_coordinate_count(geometry_type, coordinates)
    if geometry_type == "Point":
        position = _valid_position(coordinates)
        if position is None:
            return None, _map_coordinate_count(geometry_type, coordinates)
        return {"geometry_type": "Point", "coordinates": position}, 2
    if not isinstance(coordinates, list) or len(coordinates) != 1:
        return None, _map_coordinate_count(geometry_type, coordinates)
    ring = coordinates[0]
    if not isinstance(ring, list):
        return None, 0
    coordinate_count = len(ring)
    if coordinate_count > coordinate_limit:
        return None, coordinate_count
    positions = [_valid_position(position) for position in ring]
    if (
        coordinate_count < 4
        or any(position is None for position in positions)
        or positions[0] != positions[-1]
    ):
        return None, coordinate_count
    normalized = [position for position in positions if position is not None]
    if len({tuple(position) for position in normalized[:-1]}) < 3:
        return None, coordinate_count
    return {
        "geometry_type": "Polygon",
        "coordinates": [normalized],
    }, coordinate_count


def _map_coordinate_count(geometry_type: Any, coordinates: Any) -> int:
    if geometry_type == "Point" and isinstance(coordinates, list):
        return len(coordinates)
    if (
        geometry_type == "Polygon"
        and isinstance(coordinates, list)
        and coordinates
        and isinstance(coordinates[0], list)
    ):
        return len(coordinates[0])
    return 0


def _valid_position(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        return None
    longitude, latitude = float(value[0]), float(value[1])
    if (
        not math.isfinite(longitude)
        or not math.isfinite(latitude)
        or not -180 <= longitude <= 180
        or not -90 <= latitude <= 90
    ):
        return None
    return [longitude, latitude]


def _latest_mission_summaries(
    rows: Iterable[Mapping[str, Any]],
    summarizer: Callable[[Mapping[str, Any]], dict[str, Any] | None],
    limit: int,
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        summary = summarizer(row)
        if not summary:
            continue
        mission_id = str(summary["mission_id"])
        if mission_id not in latest:
            latest[mission_id] = summary
        if len(latest) >= limit:
            break
    return latest


def _latest_valid_feedback_summaries(
    rows: Iterable[Mapping[str, Any]], limit: int
) -> dict[str, dict[str, Any]]:
    """Select the newest valid bounded summary for each mission.

    Rows arrive newest first from the bounded Mongo aggregation. Invalid rows
    are never promoted to authoritative feedback; the first later valid row
    for that same mission is retained with an explicit skipped-candidate count.
    """

    latest: dict[str, dict[str, Any]] = {}
    invalid_counts: dict[str, int] = {}
    for row in rows:
        mission_id = _normalize_mission_id(_alias(row, "mission_id", "MissionId"))
        if not mission_id or mission_id in latest:
            continue
        summary = _summarize_feedback_document(row)
        if summary is None:
            invalid_counts[mission_id] = invalid_counts.get(mission_id, 0) + 1
            continue
        skipped = invalid_counts.get(mission_id, 0)
        if skipped:
            summary["skipped_newer_invalid_candidates"] = skipped
        latest[mission_id] = summary
        if len(latest) >= limit:
            break
    return latest


def _summarize_config_document(
    document: Mapping[str, Any],
) -> dict[str, Any] | None:
    mission_id = _normalize_mission_id(_alias(document, "mission_id", "MissionId"))
    if not mission_id:
        return None
    vehicle_ids = _alias(document, "vehicle_ids", "vehicles", "Vehicles")
    if not isinstance(vehicle_ids, list):
        vehicle_ids = []
    return _without_none(
        {
            "mission_id": mission_id,
            "name": _alias(document, "name", "Name"),
            "behavior": _alias(document, "behavior", "Behavior"),
            "vehicle_ids": [str(value) for value in vehicle_ids[:64]],
            "recorded_at": _document_timestamp(document),
            "document_id": _document_id(document),
        }
    )


def _summarize_feedback_document(
    document: Mapping[str, Any],
) -> dict[str, Any] | None:
    mission_id = _normalize_mission_id(_alias(document, "mission_id", "MissionId"))
    if not mission_id:
        return None
    status = _enum_int(_alias(document, "status", "Status"), MissionStatus)
    requested_status = _enum_int(
        _alias(document, "requested_status", "RequestedStatus"), MissionRequest
    )
    behavior = _enum_int(_alias(document, "behavior", "Behavior"), Behavior)
    issue_value = _alias(document, "issue", "Issue")
    issue = None if issue_value is None else _enum_int(issue_value, MissionIssue)
    recorded_at = _alias(document, "date", "Date")
    if (
        status is None
        or requested_status is None
        or behavior is None
        or (issue_value is not None and issue is None)
        or not _valid_utc_timestamp(recorded_at)
    ):
        return None

    if "task_summaries" in document:
        task_summaries = document.get("task_summaries")
        if document.get("tasks_shape_valid") is not True or not _valid_task_summaries(
            task_summaries
        ):
            return None
        assert isinstance(task_summaries, list)
        task_count = _strict_nonnegative_int(document.get("task_count"))
        tasks_truncated = document.get("tasks_truncated")
        if (
            task_count is None
            or not isinstance(tasks_truncated, bool)
            or len(task_summaries)
            != min(task_count, MAX_FEEDBACK_TASK_SUMMARIES)
            or tasks_truncated is not (task_count > MAX_FEEDBACK_TASK_SUMMARIES)
        ):
            return None
    else:
        raw_summary = _feedback_task_summary_data(
            _alias(document, "tasks", "Tasks")
        )
        if raw_summary is None:
            return None
        task_summaries, task_count, tasks_truncated = raw_summary
    path_summary = _path_count_summary(task_summaries)
    return _without_none(
        {
            "mission_id": mission_id,
            "status": status,
            "status_name": _mission_status_name(status),
            "requested_status": requested_status,
            "issue": issue,
            "issue_name": _mission_issue_name(issue),
            "behavior": behavior,
            "task_count": task_count,
            "tasks_truncated": tasks_truncated,
            "has_paths": path_summary["path_count"] > 0,
            "path_summary": path_summary,
            "recorded_at": str(recorded_at),
            "document_id": _document_id(document),
        }
    )


def _summarize_planning_document(
    document: Mapping[str, Any],
) -> dict[str, Any] | None:
    mission_id = _normalize_mission_id(_alias(document, "mission_id", "MissionId"))
    if not mission_id:
        return None
    task_summaries = document.get("task_summaries")
    if not isinstance(task_summaries, list):
        task_summaries = _planning_task_summaries(_alias(document, "tasks", "Tasks"))
    path_summary = _path_count_summary(task_summaries)
    return _without_none(
        {
            "mission_id": mission_id,
            "status": _alias(document, "status", "Status"),
            "task_count": len(task_summaries),
            "has_paths": path_summary["path_count"] > 0,
            "path_summary": path_summary,
            "recorded_at": _document_timestamp(document),
            "document_id": _document_id(document),
        }
    )


def _feedback_task_summary_data(
    tasks: Any,
) -> tuple[list[dict[str, Any]], int, bool] | None:
    if tasks is None:
        return [], 0, False
    if not isinstance(tasks, list):
        return None
    summaries: list[dict[str, Any]] = []
    for task in tasks[:MAX_FEEDBACK_TASK_SUMMARIES]:
        if not isinstance(task, Mapping):
            return None
        agent_id = _alias(
            task, "vehicle_id", "VehicleId", "agent_id", "AgentId"
        )
        if not isinstance(agent_id, str) or not agent_id.strip():
            return None
        waypoints = _alias(task, "waypoints", "Waypoints")
        if waypoints is not None and not isinstance(waypoints, list):
            return None
        summaries.append(
            {
                "agent_id": agent_id,
                "waypoint_count": len(waypoints) if isinstance(waypoints, list) else 0,
            }
        )
    return summaries, len(tasks), len(tasks) > MAX_FEEDBACK_TASK_SUMMARIES


def _valid_task_summaries(value: Any) -> bool:
    if not isinstance(value, list) or len(value) > MAX_FEEDBACK_TASK_SUMMARIES:
        return False
    for task in value:
        if not isinstance(task, Mapping):
            return False
        agent_id = task.get("agent_id")
        count = _strict_nonnegative_int(task.get("waypoint_count"))
        if not isinstance(agent_id, str) or not agent_id.strip() or count is None:
            return False
    return True


def _planning_task_summaries(tasks: Any) -> list[dict[str, Any]]:
    if not isinstance(tasks, Mapping):
        return []
    summaries = []
    for agent_id, task in list(tasks.items())[:64]:
        objectives = (
            _alias(task, "objectives", "Objectives")
            if isinstance(task, Mapping)
            else []
        )
        waypoint_count = 0
        if isinstance(objectives, list):
            for objective in objectives[:512]:
                primitives = (
                    _alias(objective, "primitives", "Primitives")
                    if isinstance(objective, Mapping)
                    else []
                )
                if isinstance(primitives, list):
                    waypoint_count += sum(
                        1
                        for primitive in primitives
                        if _primitive_has_coordinates(primitive)
                    )
        summaries.append(
            {"agent_id": str(agent_id), "waypoint_count": waypoint_count}
        )
    return summaries


def _primitive_has_coordinates(primitive: Any) -> bool:
    if not isinstance(primitive, Mapping):
        return False
    parameters = _alias(primitive, "parameters", "Parameters")
    if not isinstance(parameters, Mapping):
        return False
    coordinates = _alias(parameters, "coordinates", "Coordinates")
    return isinstance(coordinates, list) and len(coordinates) >= 2


def _path_count_summary(task_summaries: Iterable[Any]) -> dict[str, Any]:
    by_agent: dict[str, int] = {}
    anonymous_count = 0
    for task in task_summaries:
        if not isinstance(task, Mapping):
            continue
        count = _nonnegative_int(task.get("waypoint_count"))
        agent_id = _normalize_agent_id(str(task.get("agent_id") or ""))
        if agent_id:
            by_agent[agent_id] = by_agent.get(agent_id, 0) + count
        else:
            anonymous_count += count
    counts = list(by_agent.values())
    return {
        "path_count": sum(1 for count in counts if count > 0)
        + (1 if anonymous_count > 0 else 0),
        "waypoint_count": sum(counts) + anonymous_count,
        "waypoints_by_agent": by_agent,
    }


def _adapter_mission_summary(mission: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission, Mapping):
        return {}
    config = (
        mission.get("config") if isinstance(mission.get("config"), Mapping) else {}
    )
    objective = (
        config.get("objective")
        if isinstance(config.get("objective"), Mapping)
        else {}
    )
    geometries = (
        objective.get("geometries")
        if isinstance(objective.get("geometries"), list)
        else []
    )
    vehicles = config.get("vehicles")
    return _without_none(
        {
            "name": config.get("name"),
            "behavior": config.get("behavior"),
            "vehicle_ids": list(vehicles)[:64] if isinstance(vehicles, list) else [],
            "objective_count": len(geometries),
            "status": mission.get("status"),
            "status_name": mission.get("status_name"),
            "status_source": mission.get("status_source"),
            "requested_status": mission.get("requested_status"),
            "requested_status_name": mission.get("requested_status_name"),
            "command_phase": mission.get("command_phase"),
            "planner_status": mission.get("planner_status"),
            "path_status": mission.get("path_status"),
            "issue": mission.get("issue"),
            "issue_name": mission.get("issue_name"),
            "world_id": mission.get("world_id"),
            "world_version": mission.get("world_version"),
            "deployment_id": mission.get("deployment_id"),
            "map_collection": mission.get("map_collection"),
            "launch_id": mission.get("launch_id"),
            "map_snapshot_token": mission.get("map_snapshot_token"),
            "world_binding": mission.get("world_binding"),
            "backend_command": _backend_command_summary(mission),
            "updated_at": mission.get("updated_at"),
        }
    )


def _backend_command_summary(
    mission: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(mission, Mapping):
        return None
    response = mission.get("backend_rest")
    if not isinstance(response, Mapping):
        response = mission.get("legacy_rest")
    if not isinstance(response, Mapping) or "ok" not in response:
        return None
    return _without_none(
        {
            "ok": bool(response.get("ok")),
            "status_code": _integer_or_value(response.get("status_code")),
        }
    )


def _runtime_planner_summaries(
    planner: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if not isinstance(planner, Mapping) or not planner:
        return {}
    summaries: dict[str, dict[str, Any]] = {}
    state = planner.get("state")
    planner_rows = state.get("planners") if isinstance(state, Mapping) else None
    if isinstance(planner_rows, list):
        for row in planner_rows[:256]:
            if not isinstance(row, Mapping):
                continue
            mission_id = _normalize_mission_id(row.get("mission_id"))
            if not mission_id:
                continue
            summaries[mission_id] = _without_none(
                {
                    "state": row.get("state"),
                    "state_name": row.get("state_name"),
                    "status": row.get("status"),
                    "source": planner.get("source"),
                    "received_at": planner.get("received_at"),
                }
            )
    mission_id = _normalize_mission_id(planner.get("mission_id"))
    if mission_id:
        summaries[mission_id] = _without_none(
            {
                "state": (
                    planner.get("state")
                    if not isinstance(planner.get("state"), Mapping)
                    else None
                ),
                "state_name": planner.get("state_name"),
                "status": planner.get("status"),
                "source": planner.get("source"),
                "path_summary": _sanitize_path_summary(planner.get("path_summary")),
                "received_at": planner.get("received_at"),
            }
        )
    elif not summaries:
        summaries["planner"] = _without_none(
            {
                "state": state if not isinstance(state, Mapping) else None,
                "state_name": planner.get("state_name"),
                "status": planner.get("status"),
                "source": planner.get("source"),
                "received_at": planner.get("received_at"),
            }
        )
    return summaries


def _sanitize_path_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    by_agent = value.get("waypoints_by_agent")
    if not isinstance(by_agent, Mapping):
        by_agent = {}
    return {
        "path_count": _nonnegative_int(value.get("path_count")),
        "waypoint_count": _nonnegative_int(value.get("waypoint_count")),
        "waypoints_by_agent": {
            str(agent_id): _nonnegative_int(count)
            for agent_id, count in list(by_agent.items())[:64]
        },
    }


def _profile_summary(profile: Mapping[str, Any]) -> dict[str, Any]:
    return _json_mapping(
        _without_none(
            {
                "agent_id": _alias(profile, "agent_id", "AgentId"),
                "name": _alias(profile, "name", "Name"),
                "vehicle_type": _alias(
                    profile, "vehicle_type", "VehicleType"
                ),
                "status": _alias(profile, "status", "Status"),
                "current_location": _alias(
                    profile, "current_location", "localization"
                ),
                "constraints": profile.get("constraints"),
                "capabilities": profile.get("capabilities"),
            }
        )
    )


def _bounded_union(mappings: Iterable[Mapping[str, Any]], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for mapping in mappings:
        for value in mapping:
            mission_id = _normalize_mission_id(value)
            if mission_id and mission_id not in seen:
                seen.add(mission_id)
                result.append(mission_id)
                if len(result) >= limit:
                    return result
    return result


def _warning(
    item_id: str,
    observed_at: datetime,
    message: str,
    sources: tuple[str, ...],
) -> OperationalItem:
    return OperationalItem(
        item_id,
        "warning",
        observed_at,
        Freshness.STALE,
        {"message": message},
        sources,
    )


def _world_freshness(active: dict[str, Any] | None) -> Freshness:
    if not active:
        return Freshness.MISSING
    return (
        Freshness.FRESH
        if active.get("status") == "ready" and active.get("ready")
        else Freshness.STALE
    )


def _mission_status_name(status: Any) -> str:
    try:
        return MissionStatus(int(status)).name
    except (TypeError, ValueError):
        return "UNKNOWN"


def _mission_issue_name(issue: Any) -> str:
    if issue is None:
        return "NONE"
    try:
        return MissionIssue(int(issue)).name
    except (TypeError, ValueError):
        return "UNKNOWN"


def _normalize_mission_id(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    candidate = raw.removeprefix("mission_").replace("_", "-")
    try:
        return str(uuid.UUID(candidate))
    except ValueError:
        return raw


def _normalize_agent_id(value: str) -> str:
    return value.strip().lower().removeprefix("agent_").replace("_", "-")


def _alias(value: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in value:
            return value[key]
    return None


def _document_id(document: Mapping[str, Any]) -> str | None:
    value = document.get("_id")
    return str(value) if value is not None else None


def _document_timestamp(document: Mapping[str, Any]) -> str | None:
    value = _alias(document, "date", "Date", "updated_at", "created_at")
    if value is not None:
        return str(value)
    generation_time = getattr(document.get("_id"), "generation_time", None)
    return str(generation_time) if generation_time is not None else None


def _integer_or_value(value: Any) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _strict_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return int(value) if value.is_integer() and value >= 0 else None
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate or not candidate.isdecimal():
            return None
        return int(candidate)
    return None


def _enum_int(value: Any, enum_type: type[Any]) -> int | None:
    candidate = _strict_nonnegative_int(value)
    if candidate is None:
        return None
    try:
        enum_type(candidate)
    except (TypeError, ValueError):
        return None
    return candidate


def _valid_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return (
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None
        and parsed.utcoffset() == timezone.utc.utcoffset(parsed)
    )


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _bounded_error(error: BaseException) -> str:
    message = str(error).replace("\n", " ").strip() or type(error).__name__
    message = _URI_CREDENTIALS.sub(r"\g<scheme><redacted>@", message)
    return message[:240]


def _without_none(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(deepcopy(dict(value)), default=str))
