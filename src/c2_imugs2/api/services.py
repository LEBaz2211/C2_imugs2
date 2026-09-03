from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Callable, Protocol

from ..core.mission_config import MissionValidationError, load_and_validate_mission
from ..core.models import MissionRequest
from ..infrastructure.legacy.rest import LegacyRestClient
from ..worlds.service import (
    WorldConflictError,
    WorldNotFoundError,
    WorldNotReadyError,
)


class WorldRuntimePort(Protocol):
    def list_worlds(self) -> list[dict[str, Any]]: ...

    def get_world(self, world_id: str) -> dict[str, Any]: ...

    def create_world(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def update_world(self, world_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def delete_world(self, world_id: str) -> dict[str, Any]: ...

    def validated_active(self) -> dict[str, Any] | None: ...

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]: ...

    def launch(self, world_id: str, revision: int) -> dict[str, Any]: ...


class AdapterRuntimeState(Protocol):
    missions: dict[str, dict[str, Any]]
    forgotten_missions: set[str]
    agent_updates: dict[str, dict[str, Any]]
    planner_state: dict[str, Any]
    command_target_mission_id: str | None


@dataclass(frozen=True)
class ApplicationServiceError(RuntimeError):
    status_code: int
    detail: Any

    def __str__(self) -> str:
        return str(self.detail)


class BackendMissionApplicationService:
    """Application boundary for the live editable-backend mission workflow.

    This service owns command sequencing and normalized adapter state.  HTTP
    routers translate its errors, while the old REST client remains a replaceable
    compatibility gateway rather than being called directly from route bodies.
    """

    def __init__(
        self,
        *,
        repo_root: Path,
        runtime: AdapterRuntimeState,
        rest_client: LegacyRestClient,
        world_runtime: WorldRuntimePort,
        inline_feature_refs: Callable[[dict[str, Any], Path], dict[str, Any]],
        normalize_mission_id: Callable[[Any], str],
        status_name: Callable[[Any], str],
        now: Callable[[], str],
        save_forgotten_missions: Callable[[Path, set[str]], None],
    ) -> None:
        self.repo_root = repo_root
        self.runtime = runtime
        self.rest_client = rest_client
        self.world_runtime = world_runtime
        self.inline_feature_refs = inline_feature_refs
        self.normalize_mission_id = normalize_mission_id
        self.status_name = status_name
        self.now = now
        self.save_forgotten_missions = save_forgotten_missions

    def initialize(self, mission_config: dict[str, Any]) -> dict[str, Any]:
        canonical, active_world = self.validate_draft(mission_config)
        world_binding = _mission_world_binding(active_world)
        try:
            # Compatibility shaping must never mutate the canonical mission
            # retained by the adapter or returned to the browser.
            compatibility_config = _inline_live_feature_refs(
                deepcopy(canonical), active_world
            )
            compatibility_config = self.inline_feature_refs(compatibility_config, self.repo_root)
        except MissionValidationError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc
        geometry_adjusted = compatibility_config != canonical
        injected_speed = _ensure_backend_mission_speed(
            compatibility_config,
            active_world,
            canonical.get("vehicles") or [],
        )
        injected_swaths = _ensure_backend_coverage_swaths(
            compatibility_config,
            active_world,
            canonical.get("vehicles") or [],
        )

        mission_id = canonical["mission_id"]
        self.runtime.forgotten_missions.discard(mission_id)
        self.save_forgotten_missions(self.repo_root, self.runtime.forgotten_missions)
        previous_target = getattr(self.runtime, "command_target_mission_id", None)
        response = self.rest_client.initialize_mission(compatibility_config)
        adjustments: list[str] = []
        if geometry_adjusted:
            adjustments.append(
                "translated feature references or polygon geometry for editable-backend ROS compatibility"
            )
        if injected_speed is not None:
            adjustments.append(
                f"added backend-only max_speed={injected_speed:g} m/s because canonical transit speed is optional"
            )
        if injected_swaths is not None:
            adjustments.append(
                "added backend-only coverage_swath_widths="
                + str(injected_swaths)
                + " from active-world vehicle sensor profiles"
            )

        state = {
            "mission_id": mission_id,
            "status": 0,
            "status_name": self.status_name(0),
            "status_source": (
                "adapter_acknowledgement"
                if response.ok
                else "backend_rest_failure"
            ),
            "command_phase": "init_acknowledged" if response.ok else "init_failed",
            "planner_status": "waiting_for_feedback" if response.ok else "not_requested",
            "last_command_ok": response.ok,
            "command_target": response.ok,
            "attempted_at": self.now(),
            "updated_at": self.now(),
            "config": canonical,
            "world_binding": world_binding,
            **{
                field: world_binding[field]
                for field in _WORLD_BINDING_IDENTITY_FIELDS
            },
            "adapter_adjustments": adjustments,
            "backend_rest": response.__dict__,
            # Preserve the stable UI response during the compatibility migration.
            "legacy_rest": response.__dict__,
        }
        if response.ok:
            state["initialized_at"] = self.now()
            # The inherited REST status command has no mission-id field. Keep
            # the exact mission targeted by the last successful initialize so
            # mission-shaped API routes cannot command a different backend
            # mission by accident.
            if previous_target and previous_target != mission_id:
                previous_state = self.runtime.missions.get(previous_target)
                if previous_state is not None:
                    previous_state["command_target"] = False
            self.runtime.command_target_mission_id = mission_id
        else:
            # A failed compatibility request may have failed before or after
            # the stateful backend changed its implicit target. Fail closed and
            # require a fresh successful Init before any status command.
            if previous_target:
                previous_state = self.runtime.missions.get(previous_target)
                if previous_state is not None:
                    previous_state["command_target"] = False
            self.runtime.command_target_mission_id = None
        self.runtime.missions[mission_id] = state
        if not response.ok:
            raise ApplicationServiceError(
                502,
                {"message": "backend REST mission init failed", "backend_rest": response.__dict__},
            )
        return state

    def validate_draft(
        self, mission_config: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Canonicalize a draft and bind it to the currently ready world."""

        canonical = self._canonicalize_mission(mission_config)

        try:
            active_world = self.world_runtime.require_ready(canonical.get("vehicles") or [])
        except WorldNotReadyError as exc:
            raise ApplicationServiceError(409, str(exc)) from exc
        _preflight_mission_against_world(canonical, active_world)
        return canonical, active_world

    def validate_assistant_proposal(
        self, mission_config: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Validate an editable proposal without pretending it can be initialized.

        Proposal editing is useful while an otherwise-identical runtime is
        temporarily stale.  Keep the environment identity and vehicle
        membership checks here, but leave the strict READY gate in
        :meth:`validate_draft`, which is called again by Init.
        """

        canonical = self._canonicalize_mission(mission_config)
        active_world = self.world_runtime.validated_active()
        if not active_world:
            raise ApplicationServiceError(
                409, "no active environment is available to ground the mission proposal"
            )

        if (
            active_world.get("ready") is True
            and str(active_world.get("status") or "").lower() == "ready"
        ):
            try:
                ready_world = self.world_runtime.require_ready(
                    canonical.get("vehicles") or []
                )
                _preflight_mission_against_world(canonical, ready_world)
                return canonical, ready_world
            except WorldNotReadyError as exc:
                raise ApplicationServiceError(409, str(exc)) from exc

        available = {
            str(agent.get("agent_id") or "")
            for agent in active_world.get("agents") or []
            if isinstance(agent, dict)
        }
        missing = sorted(set(canonical.get("vehicles") or []) - available)
        if missing:
            raise ApplicationServiceError(
                409,
                "mission vehicles are not part of the active environment: "
                + ", ".join(missing),
            )
        return canonical, active_world

    def _canonicalize_mission(self, mission_config: dict[str, Any]) -> dict[str, Any]:
        try:
            draft = deepcopy(mission_config)
            # The UI already assigns IDs, but the source ICD examples do not.
            # Generate/normalize at the API boundary before required-field
            # validation so pasted examples are accepted without weakening the
            # persisted canonical contract.
            draft["mission_id"] = self.normalize_mission_id(draft.get("mission_id"))
            canonical = load_and_validate_mission(draft, repo_root=self.repo_root)
        except MissionValidationError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc
        return canonical

    def get(self, mission_id: str) -> dict[str, Any]:
        mission = self.runtime.missions.get(mission_id)
        if not mission or mission_id in self.runtime.forgotten_missions:
            raise ApplicationServiceError(404, "mission is not in adapter runtime")
        return mission

    def change_status(self, mission_id: str, request: MissionRequest, optimistic_status: int) -> dict[str, Any]:
        mission = self.runtime.missions.get(mission_id)
        if mission is None or mission_id in self.runtime.forgotten_missions:
            raise ApplicationServiceError(404, "mission is not in adapter runtime")

        command_target = getattr(self.runtime, "command_target_mission_id", None)
        if command_target is None:
            raise ApplicationServiceError(
                409,
                "no mission is bound to the backend status command; initialize this mission again before changing its status",
            )
        if command_target != mission_id:
            raise ApplicationServiceError(
                409,
                "this mission is not the backend status-command target; initialize it again before changing its status",
            )

        try:
            current_status = int(mission.get("status"))
        except (TypeError, ValueError):
            current_status = None
        allowed_statuses = {
            MissionRequest.APPROVE: {1, 2},
            MissionRequest.START: {4},
        }.get(request)
        if allowed_statuses is not None and current_status not in allowed_statuses:
            allowed_names = (
                "PLANNED or PLANNED_ALTERNATIVE"
                if request is MissionRequest.APPROVE
                else "ACCEPTED"
            )
            current_name = str(mission.get("status_name") or "UNKNOWN")
            raise ApplicationServiceError(
                409,
                f"cannot {request.name.lower()} mission from {current_name}; expected {allowed_names}",
            )

        try:
            active_world = self.world_runtime.require_ready(
                (mission.get("config") or {}).get("vehicles") or []
            )
        except WorldNotReadyError as exc:
            raise ApplicationServiceError(409, str(exc)) from exc
        active_binding = _mission_world_binding(active_world)
        mission_binding = mission.get("world_binding")
        differing_fields = _world_binding_differences(mission_binding, active_binding)
        if differing_fields:
            raise ApplicationServiceError(
                409,
                "mission belongs to a different world deployment; re-initialize it "
                "in the active world (differing binding fields: "
                + ", ".join(differing_fields)
                + ")",
            )

        response = self.rest_client.change_status(request)
        command_update = {
            "requested_status": int(request),
            "requested_status_name": request.name,
            "command_phase": (
                request.name.lower()
                if response.ok
                else f"{request.name.lower()}_failed"
            ),
            "last_command_ok": response.ok,
            "updated_at": self.now(),
            "backend_rest": response.__dict__,
            "legacy_rest": response.__dict__,
        }
        if response.ok:
            command_update.update(
                {
                    "status": optimistic_status,
                    "status_name": self.status_name(optimistic_status),
                    "status_source": "adapter_acknowledgement",
                }
            )
        mission.update(command_update)
        if not response.ok:
            raise ApplicationServiceError(
                502,
                {"message": "backend REST status change failed", "backend_rest": response.__dict__},
            )
        return mission

    def forget(self, mission_id: str) -> dict[str, Any]:
        self.runtime.forgotten_missions.add(mission_id)
        self.save_forgotten_missions(self.repo_root, self.runtime.forgotten_missions)
        removed = self.runtime.missions.pop(mission_id, None)
        if getattr(self.runtime, "command_target_mission_id", None) == mission_id:
            self.runtime.command_target_mission_id = None
        planner_state = self.runtime.planner_state
        if isinstance(planner_state, dict) and planner_state.get("mission_id") == mission_id:
            self.runtime.planner_state = {}
        return {
            "mission_id": mission_id,
            "removed": bool(removed),
            "message": "Removed mission from adapter runtime only. Backend ROS and MongoDB are unchanged.",
        }


_WORLD_BINDING_IDENTITY_FIELDS = (
    "world_id",
    "world_version",
    "deployment_id",
    "map_collection",
    "content_hash",
    "map_feature_hash",
    "launch_id",
    "map_snapshot_token",
)


def _mission_world_binding(active_world: dict[str, Any]) -> dict[str, Any]:
    binding = {
        field: str(active_world.get(field) or "").strip()
        for field in _WORLD_BINDING_IDENTITY_FIELDS
    }
    missing = [field for field, value in binding.items() if not value]
    if missing:
        raise ApplicationServiceError(
            503,
            "active world identity is incomplete; missing: " + ", ".join(missing),
        )
    binding.update(
        {
            "status": str(active_world.get("status") or ""),
            "ready": active_world.get("ready") is True,
        }
    )
    return binding


def _world_binding_differences(
    mission_binding: Any,
    active_binding: dict[str, Any],
) -> list[str]:
    if not isinstance(mission_binding, dict):
        return list(_WORLD_BINDING_IDENTITY_FIELDS)
    return [
        field
        for field in _WORLD_BINDING_IDENTITY_FIELDS
        if str(mission_binding.get(field) or "") != str(active_binding.get(field) or "")
    ]


def _ensure_backend_mission_speed(
    compatibility_config: dict[str, Any],
    active_world: dict[str, Any],
    vehicle_ids: list[str],
) -> float | None:
    """Supply a speed required by the inherited planner without changing the contract.

    ``transit`` is optional in the canonical mission schema, while the ROS
    planner inherited from the compatibility runtime reads its nested
    ``max_speed`` unconditionally.  Derive a conservative speed from only the
    selected world vehicles and keep the addition in the backend-bound copy.
    """

    transit = compatibility_config.get("transit")
    if not isinstance(transit, dict):
        transit = {}
        compatibility_config["transit"] = transit
    constraints = transit.get("desired_vehicle_constraints")
    if not isinstance(constraints, dict):
        constraints = {}
        transit["desired_vehicle_constraints"] = constraints
    if "max_speed" in constraints:
        return None

    selected = {_normalized_vehicle_id(vehicle_id) for vehicle_id in vehicle_ids}
    speeds: list[float] = []
    for agent in active_world.get("agents") or []:
        if not isinstance(agent, dict):
            continue
        if _normalized_vehicle_id(agent.get("agent_id")) not in selected:
            continue
        profile = agent.get("constraints")
        speed = profile.get("max_speed") if isinstance(profile, dict) else None
        if (
            isinstance(speed, int | float)
            and not isinstance(speed, bool)
            and math.isfinite(speed)
            and speed > 0
        ):
            speeds.append(float(speed))

    derived_speed = min(speeds) if speeds else 1.0
    constraints["max_speed"] = derived_speed
    return derived_speed


def _ensure_backend_coverage_swaths(
    compatibility_config: dict[str, Any],
    active_world: dict[str, Any],
    vehicle_ids: list[str],
) -> list[float] | None:
    """Inject sensor swaths without reusing inter-vehicle separation fields."""

    if int(compatibility_config.get("behavior", 0)) != 1:
        return None
    objective = compatibility_config.get("objective")
    if not isinstance(objective, dict) or objective.get("maximize_coverage") is False:
        return None
    road_usage = (
        ((compatibility_config.get("transit") or {}).get("optimization") or {}).get(
            "road_usage"
        )
    )
    if isinstance(road_usage, int | float) and road_usage >= 0.999:
        # COVERAGE + road_usage=1 patrols the active-world road subgraph; lane
        # swath is unrelated to that task.
        return None
    geometries = objective.get("geometries") or []
    if geometries and all(
        isinstance(item, dict)
        and isinstance(item.get("geometry"), dict)
        and item["geometry"].get("geometry_type") == "LineString"
        for item in geometries
    ):
        return None
    if objective.get("coverage_swath_widths"):
        return None

    swaths: list[float] = []
    for vehicle_id in vehicle_ids:
        normalized_id = _normalized_vehicle_id(vehicle_id)
        profile = next(
            (
                agent
                for agent in active_world.get("agents") or []
                if isinstance(agent, dict)
                and _normalized_vehicle_id(agent.get("agent_id")) == normalized_id
            ),
            None,
        )
        constraints = profile.get("constraints") if isinstance(profile, dict) else None
        raw = constraints.get("coverage_width_m") if isinstance(constraints, dict) else None
        if not (
            isinstance(raw, int | float)
            and not isinstance(raw, bool)
            and math.isfinite(raw)
            and raw > 0
        ):
            swaths = []
            break
        swaths.append(float(raw))

    # During the migration, old UI payloads explicitly used the separation
    # field as a swath. Preserve their executable behavior only as a backend
    # compatibility fallback; canonical state keeps the original meaning.
    if not swaths:
        legacy_values = objective.get("maximum_coverage_distances")
        if isinstance(legacy_values, list) and legacy_values:
            expanded = legacy_values * len(vehicle_ids) if len(legacy_values) == 1 else legacy_values
            if len(expanded) == len(vehicle_ids):
                swaths = [float(value) for value in expanded]
    if not swaths:
        raise ApplicationServiceError(
            422,
            "coverage mission requires coverage_width_m for every selected active-world vehicle "
            "or explicit objective.coverage_swath_widths",
        )

    compact = [swaths[0]] if all(value == swaths[0] for value in swaths) else swaths
    objective["coverage_swath_widths"] = compact
    return compact


def _preflight_mission_against_world(
    mission: dict[str, Any], active_world: dict[str, Any]
) -> None:
    """Reject constraints that the selected immutable world cannot satisfy."""

    agents = {
        _normalized_vehicle_id(agent.get("agent_id")): agent
        for agent in active_world.get("agents") or []
        if isinstance(agent, dict) and agent.get("agent_id")
    }
    snapshot_features = ((active_world.get("snapshot") or {}).get("features") or [])
    live_features = _current_deployment_live_features(active_world)
    allowed_feature_ids = {
        str((feature.get("properties") or {}).get("feature_id") or feature.get("id") or "")
        for feature in [*snapshot_features, *live_features]
        if isinstance(feature, dict)
    }
    referenced_feature_ids = set(_iter_feature_ids(mission))
    foreign = sorted(referenced_feature_ids - allowed_feature_ids)
    if foreign:
        raise ApplicationServiceError(
            422,
            "mission references features outside the active snapshot/deployment: "
            + ", ".join(foreign),
        )
    required_capabilities = mission.get("required_capabilities") or []
    if isinstance(required_capabilities, list):
        for vehicle_id in mission.get("vehicles") or []:
            profile = agents.get(_normalized_vehicle_id(vehicle_id)) or {}
            available_capabilities = {
                str(value)
                for value in profile.get("capabilities") or []
                if isinstance(value, str)
            }
            missing_capabilities = sorted(
                {
                    str(value)
                    for value in required_capabilities
                    if isinstance(value, str)
                }
                - available_capabilities
            )
            if missing_capabilities:
                raise ApplicationServiceError(
                    422,
                    f"mission vehicle {vehicle_id} lacks required active-world capabilities: "
                    + ", ".join(missing_capabilities),
                )
    requested = ((mission.get("transit") or {}).get("desired_vehicle_constraints") or {})
    if isinstance(requested, dict):
        for vehicle_id in mission.get("vehicles") or []:
            profile = agents.get(_normalized_vehicle_id(vehicle_id)) or {}
            available = profile.get("constraints") if isinstance(profile, dict) else {}
            if not isinstance(available, dict):
                continue
            for key, desired in requested.items():
                supported = available.get(key)
                if (
                    isinstance(desired, int | float)
                    and not isinstance(desired, bool)
                    and isinstance(supported, int | float)
                    and not isinstance(supported, bool)
                    and desired > supported
                ):
                    raise ApplicationServiceError(
                        422,
                        f"mission requests {key}={desired:g} for {vehicle_id}, but the active-world profile supports at most {supported:g}",
                    )

    objective = mission.get("objective") or {}
    if not isinstance(objective, dict):
        return
    geometries = objective.get("geometries") or []
    if (
        int(mission.get("behavior", 0)) == 0
        and objective.get("maximize_coverage") is True
        and len(geometries) == 1
        and isinstance(geometries[0], dict)
    ):
        geometry = geometries[0].get("geometry")
        if isinstance(geometry, dict) and geometry.get("geometry_type") == "LineString":
            _preflight_relay_geometry(mission, objective, geometry)


def _inline_live_feature_refs(
    mission: dict[str, Any], active_world: dict[str, Any]
) -> dict[str, Any]:
    live_by_id = {
        str((feature.get("properties") or {}).get("feature_id") or feature.get("id") or ""): feature
        for feature in _current_deployment_live_features(active_world)
        if isinstance(feature, dict)
    }
    _replace_live_feature_refs(mission, live_by_id)
    return mission


def _current_deployment_live_features(active_world: dict[str, Any]) -> list[dict[str, Any]]:
    deployment_id = str(active_world.get("deployment_id") or "")
    return [
        feature
        for feature in ((active_world.get("live_features") or {}).get("features") or [])
        if isinstance(feature, dict)
        and str((feature.get("properties") or {}).get("deployment_id") or "")
        == deployment_id
    ]


def _iter_feature_ids(value: Any):
    if isinstance(value, dict):
        feature_id = value.get("feature_id")
        if isinstance(feature_id, str) and feature_id:
            yield feature_id
        for nested in value.values():
            yield from _iter_feature_ids(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_feature_ids(nested)


def _replace_live_feature_refs(value: Any, live_by_id: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, dict):
        feature = live_by_id.get(str(value.get("feature_id") or ""))
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if isinstance(geometry, dict):
            value.pop("feature_id", None)
            value["geometry"] = {
                "geometry_type": geometry.get("type"),
                "coordinates": deepcopy(geometry.get("coordinates")),
            }
        for nested in list(value.values()):
            _replace_live_feature_refs(nested, live_by_id)
    elif isinstance(value, list):
        for nested in value:
            _replace_live_feature_refs(nested, live_by_id)


def _preflight_relay_geometry(
    mission: dict[str, Any], objective: dict[str, Any], geometry: dict[str, Any]
) -> None:
    separations = objective.get("maximum_coverage_distances")
    endpoint_tolerance = objective.get("maximum_distance")
    coordinates = geometry.get("coordinates")
    if not (
        isinstance(separations, list)
        and separations
        and isinstance(endpoint_tolerance, int | float)
        and isinstance(coordinates, list)
        and len(coordinates) >= 2
    ):
        return
    length_m = sum(
        _distance_m(start, end) for start, end in zip(coordinates, coordinates[1:])
    )
    vehicle_count = len(mission.get("vehicles") or [])
    max_separation = max(float(value) for value in separations)
    reachable_span = max(0, vehicle_count - 1) * max_separation + 2.0 * float(endpoint_tolerance)
    if length_m > reachable_span + 1e-6:
        raise ApplicationServiceError(
            422,
            f"communication relay is infeasible: {vehicle_count} vehicles can span at most "
            f"{reachable_span:.1f} m with the requested spacing/end tolerances, but the line is {length_m:.1f} m",
        )


def _distance_m(start: Any, end: Any) -> float:
    lon1, lat1 = float(start[0]), float(start[1])
    lon2, lat2 = float(end[0]), float(end[1])
    mean_latitude = math.radians((lat1 + lat2) / 2.0)
    return math.hypot(
        (lon2 - lon1) * 111320.0 * math.cos(mean_latitude),
        (lat2 - lat1) * 110540.0,
    )


def _normalized_vehicle_id(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


class WorldApplicationService:
    """Application boundary for revisioned authoring and runtime launch."""

    def __init__(self, runtime: AdapterRuntimeState, world_runtime: WorldRuntimePort) -> None:
        self.runtime = runtime
        self.world_runtime = world_runtime

    async def list_worlds(self) -> dict[str, Any]:
        try:
            return {"worlds": await asyncio.to_thread(self.world_runtime.list_worlds)}
        except RuntimeError as exc:
            raise ApplicationServiceError(503, str(exc)) from exc

    async def get_world(self, world_id: str) -> dict[str, Any]:
        return await self.invoke(self.world_runtime.get_world, world_id)

    async def create_world(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.invoke(self.world_runtime.create_world, payload)

    async def update_world(self, world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.invoke(self.world_runtime.update_world, world_id, payload)

    async def delete_world(self, world_id: str) -> dict[str, Any]:
        return await self.invoke(self.world_runtime.delete_world, world_id)

    def active(self) -> dict[str, Any]:
        active = self.world_runtime.validated_active()
        return active or {
            "status": "inactive",
            "ready": False,
            "message": "No world is active. Launch one from World Builder before initializing a mission.",
        }

    async def launch(self, world_id: str, revision: int) -> dict[str, Any]:
        try:
            result = await asyncio.to_thread(self.world_runtime.launch, world_id, revision)
        except ValueError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc
        except WorldConflictError as exc:
            raise ApplicationServiceError(409, {"message": str(exc), "current": exc.current}) from exc
        except WorldNotFoundError as exc:
            raise ApplicationServiceError(404, f"world not found: {exc.args[0]}") from exc
        except WorldNotReadyError as exc:
            raise ApplicationServiceError(503, str(exc)) from exc
        # An idempotent reuse did not replace any backend process or runtime
        # authority, so its adapter mirrors remain valid.  Clear them only
        # after a real world transition invalidates the old observations.
        if result.get("idempotent_reuse") is not True:
            self.runtime.missions.clear()
            self.runtime.agent_updates.clear()
            self.runtime.planner_state = {}
            self.runtime.command_target_mission_id = None
        return result

    async def invoke(self, function: Callable[..., Any], *args: Any) -> Any:
        try:
            return await asyncio.to_thread(function, *args)
        except WorldConflictError as exc:
            raise ApplicationServiceError(409, {"message": str(exc), "current": exc.current}) from exc
        except WorldNotFoundError as exc:
            raise ApplicationServiceError(404, str(exc.args[0])) from exc
        except ValueError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc
        except RuntimeError as exc:
            raise ApplicationServiceError(503, str(exc)) from exc
