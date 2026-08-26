from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .domain import MissionRequest
from .legacy_rest import LegacyRestClient
from .mission_config import MissionValidationError, load_and_validate_mission
from .scenario_runtime import ScenarioNotReadyError


class ScenarioRuntimePort(Protocol):
    def list_scenarios(self) -> list[dict[str, Any]]: ...

    def validated_active(self) -> dict[str, Any] | None: ...

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]: ...

    def activate(self, payload: dict[str, Any]) -> dict[str, Any]: ...


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
        scenario_runtime: ScenarioRuntimePort,
        inline_feature_refs: Callable[[dict[str, Any], Path], dict[str, Any]],
        normalize_mission_id: Callable[[Any], str],
        status_name: Callable[[Any], str],
        now: Callable[[], str],
        save_forgotten_missions: Callable[[Path, set[str]], None],
    ) -> None:
        self.repo_root = repo_root
        self.runtime = runtime
        self.rest_client = rest_client
        self.scenario_runtime = scenario_runtime
        self.inline_feature_refs = inline_feature_refs
        self.normalize_mission_id = normalize_mission_id
        self.status_name = status_name
        self.now = now
        self.save_forgotten_missions = save_forgotten_missions

    def initialize(self, mission_config: dict[str, Any]) -> dict[str, Any]:
        canonical, active_scenario = self.validate_draft(mission_config)
        try:
            compatibility_config = self.inline_feature_refs(canonical, self.repo_root)
        except MissionValidationError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc

        mission_id = canonical["mission_id"]
        self.runtime.forgotten_missions.discard(mission_id)
        self.save_forgotten_missions(self.repo_root, self.runtime.forgotten_missions)
        previous_target = getattr(self.runtime, "command_target_mission_id", None)
        response = self.rest_client.initialize_mission(compatibility_config)
        adjustments: list[str] = []
        if compatibility_config != canonical:
            adjustments.append(
                "translated feature references or polygon geometry for editable-backend ROS compatibility"
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
            "scenario_id": active_scenario["scenario_id"],
            "scenario_version": active_scenario["version"],
            "map_collection": active_scenario["map_collection"],
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
        """Canonicalize a draft and bind it to the currently ready scenario."""

        try:
            canonical = load_and_validate_mission(mission_config, repo_root=self.repo_root)
            canonical["mission_id"] = self.normalize_mission_id(canonical.get("mission_id"))
        except MissionValidationError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc

        try:
            active_scenario = self.scenario_runtime.require_ready(canonical.get("vehicles") or [])
        except ScenarioNotReadyError as exc:
            raise ApplicationServiceError(409, str(exc)) from exc
        return canonical, active_scenario

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
            self.scenario_runtime.require_ready()
        except ScenarioNotReadyError as exc:
            raise ApplicationServiceError(409, str(exc)) from exc

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


class ScenarioApplicationService:
    """Application boundary for catalog reads and destructive activation."""

    def __init__(self, runtime: AdapterRuntimeState, scenario_runtime: ScenarioRuntimePort) -> None:
        self.runtime = runtime
        self.scenario_runtime = scenario_runtime

    async def list_scenarios(self) -> dict[str, Any]:
        try:
            return {"scenarios": await asyncio.to_thread(self.scenario_runtime.list_scenarios)}
        except RuntimeError as exc:
            raise ApplicationServiceError(503, str(exc)) from exc

    def active(self) -> dict[str, Any]:
        active = self.scenario_runtime.validated_active()
        return active or {
            "status": "inactive",
            "ready": False,
            "message": "No scenario is active. Activate one from the Scenario tab before initializing a mission.",
        }

    async def activate(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await asyncio.to_thread(self.scenario_runtime.activate, payload)
        except ValueError as exc:
            raise ApplicationServiceError(422, str(exc)) from exc
        except ScenarioNotReadyError as exc:
            raise ApplicationServiceError(503, str(exc)) from exc
        # An idempotent reuse did not replace any backend process or runtime
        # authority, so its adapter mirrors remain valid.  Clear them only
        # after a real scenario transition invalidates the old observations.
        if result.get("idempotent_reuse") is not True:
            self.runtime.missions.clear()
            self.runtime.agent_updates.clear()
            self.runtime.planner_state = {}
            self.runtime.command_target_mission_id = None
        return result
