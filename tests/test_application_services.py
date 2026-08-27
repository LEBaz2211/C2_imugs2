from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import c2_imugs2.scenario_runtime as scenario_runtime
from c2_imugs2.application_services import (
    ApplicationServiceError,
    BackendMissionApplicationService,
    ScenarioApplicationService,
)
from c2_imugs2.domain import MissionRequest
from c2_imugs2.legacy_rest import LegacyRestResponse
from c2_imugs2.scenario_runtime import ScenarioRuntimeManager, build_scenario_snapshot


ROOT = Path(__file__).resolve().parents[1]


class RestGateway:
    def __init__(self) -> None:
        self.initialized: list[dict[str, Any]] = []
        self.requests: list[MissionRequest] = []
        self.initialize_response = LegacyRestResponse(True, 200, "ok")
        self.status_response = LegacyRestResponse(True, 200, "ok")

    def initialize_mission(self, config: dict[str, Any]) -> LegacyRestResponse:
        self.initialized.append(config)
        return self.initialize_response

    def change_status(self, request: MissionRequest) -> LegacyRestResponse:
        self.requests.append(request)
        return self.status_response


class ReadyScenario:
    def __init__(self, agents: list[dict[str, Any]] | None = None) -> None:
        self.agents = deepcopy(agents or [])

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]:
        return {
            "scenario_id": "scenario-a",
            "version": "version-a",
            "map_collection": "scenario_a_version_a",
            "status": "ready",
            "agents": deepcopy(self.agents),
        }

    def validated_active(self) -> dict[str, Any]:
        return self.require_ready()

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [self.require_ready()]

    def activate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {**self.require_ready(), "agents": payload.get("agents") or []}


def _service(
    tmp_path: Path,
    scenario: ReadyScenario | None = None,
) -> tuple[BackendMissionApplicationService, SimpleNamespace, RestGateway]:
    runtime = SimpleNamespace(
        missions={},
        forgotten_missions=set(),
        agent_updates={},
        planner_state={},
        command_target_mission_id=None,
    )
    rest = RestGateway()
    service = BackendMissionApplicationService(
        repo_root=ROOT,
        runtime=runtime,
        rest_client=rest,  # type: ignore[arg-type]
        scenario_runtime=scenario or ReadyScenario(),
        inline_feature_refs=lambda config, root: config,
        normalize_mission_id=lambda value: str(value),
        status_name=lambda value: {0: "NONE", 4: "ACCEPTED", 5: "STARTED"}[int(value)],
        now=lambda: "2026-08-22T00:00:00Z",
        save_forgotten_missions=lambda root, ids: None,
    )
    return service, runtime, rest


def test_live_mission_application_owns_command_sequence(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)
    mission = {
        "mission_id": "mission-a",
        "behavior": 0,
        "vehicles": ["robot-a"],
        "objective": {
            "geometries": [
                {"geometry": {"geometry_type": "Point", "coordinates": [4.0, 50.0]}}
            ]
        },
    }

    initialized = service.initialize(mission)
    runtime.missions["mission-a"].update(
        {"status": 1, "status_name": "PLANNED", "status_source": "mission_feedback"}
    )
    accepted = service.change_status("mission-a", MissionRequest.APPROVE, 4)

    assert initialized["scenario_version"] == "version-a"
    assert accepted["status_name"] == "ACCEPTED"
    assert rest.initialized[0]["mission_id"] == "mission-a"
    assert rest.requests == [MissionRequest.APPROVE]
    assert runtime.missions["mission-a"] is accepted
    assert runtime.missions["mission-a"]["command_target"] is True


def test_live_mission_application_maps_validation_to_unprocessable(tmp_path: Path) -> None:
    service, _, rest = _service(tmp_path)

    with pytest.raises(ApplicationServiceError) as error:
        service.initialize({"mission_id": "bad"})

    assert error.value.status_code == 422
    assert rest.initialized == []


def test_init_adds_backend_only_speed_from_selected_scenario_vehicles(
    tmp_path: Path,
) -> None:
    scenario = ReadyScenario(
        [
            {"agent_id": "robot-a", "constraints": {"max_speed": 4.5}},
            {"agent_id": "robot_b", "constraints": {"max_speed": 2.5}},
            {"agent_id": "robot-c", "constraints": {"max_speed": 0.5}},
        ]
    )
    service, runtime, rest = _service(tmp_path, scenario)
    mission = {
        "mission_id": "mission-a",
        "behavior": 0,
        "vehicles": ["robot-a", "robot-b"],
        "objective": {
            "geometries": [
                {"geometry": {"geometry_type": "Point", "coordinates": [4.0, 50.0]}}
            ]
        },
    }
    original = deepcopy(mission)

    initialized = service.initialize(mission)

    assert rest.initialized[0]["transit"]["desired_vehicle_constraints"]["max_speed"] == 2.5
    assert "transit" not in initialized["config"]
    assert "transit" not in runtime.missions["mission-a"]["config"]
    assert mission == original
    assert any(
        "backend-only max_speed=2.5" in item
        for item in initialized["adapter_adjustments"]
    )


def test_init_preserves_explicit_transit_speed(tmp_path: Path) -> None:
    scenario = ReadyScenario(
        [{"agent_id": "robot-a", "constraints": {"max_speed": 4.5}}]
    )
    service, _, rest = _service(tmp_path, scenario)
    mission = {
        "mission_id": "mission-a",
        "behavior": 0,
        "vehicles": ["robot-a"],
        "transit": {"desired_vehicle_constraints": {"max_speed": 1.3}},
        "objective": {
            "geometries": [
                {"geometry": {"geometry_type": "Point", "coordinates": [4.0, 50.0]}}
            ]
        },
    }

    initialized = service.initialize(mission)

    assert rest.initialized[0]["transit"]["desired_vehicle_constraints"]["max_speed"] == 1.3
    assert initialized["config"]["transit"]["desired_vehicle_constraints"]["max_speed"] == 1.3
    assert not any(
        "backend-only max_speed" in item
        for item in initialized["adapter_adjustments"]
    )


def test_init_uses_safe_speed_fallback_when_scenario_profiles_have_none(
    tmp_path: Path,
) -> None:
    service, _, rest = _service(tmp_path, ReadyScenario([{"agent_id": "robot-a"}]))
    mission = {
        "mission_id": "mission-a",
        "behavior": 0,
        "vehicles": ["robot-a"],
        "objective": {
            "geometries": [
                {"geometry": {"geometry_type": "Point", "coordinates": [4.0, 50.0]}}
            ]
        },
    }

    service.initialize(mission)

    assert rest.initialized[0]["transit"]["desired_vehicle_constraints"]["max_speed"] == 1.0


def test_failed_init_is_recorded_as_failure_not_acknowledgement(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)
    rest.initialize_response = LegacyRestResponse(False, 503, "unavailable")
    mission = {
        "mission_id": "mission-a",
        "behavior": 0,
        "vehicles": ["robot-a"],
        "objective": {
            "geometries": [
                {"geometry": {"geometry_type": "Point", "coordinates": [4.0, 50.0]}}
            ]
        },
    }

    with pytest.raises(ApplicationServiceError) as error:
        service.initialize(mission)

    state = runtime.missions["mission-a"]
    assert error.value.status_code == 502
    assert state["command_phase"] == "init_failed"
    assert state["status_source"] == "backend_rest_failure"
    assert state["last_command_ok"] is False
    assert state["command_target"] is False
    assert runtime.command_target_mission_id is None
    assert "initialized_at" not in state


def test_failed_init_invalidates_the_previous_implicit_backend_target(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)

    def mission(mission_id: str) -> dict[str, Any]:
        return {
            "mission_id": mission_id,
            "behavior": 0,
            "vehicles": ["robot-a"],
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Point",
                            "coordinates": [4.0, 50.0],
                        }
                    }
                ]
            },
        }

    service.initialize(mission("mission-a"))
    rest.initialize_response = LegacyRestResponse(False, 503, "unavailable")

    with pytest.raises(ApplicationServiceError):
        service.initialize(mission("mission-b"))

    assert runtime.command_target_mission_id is None
    assert runtime.missions["mission-a"]["command_target"] is False
    assert runtime.missions["mission-b"]["command_target"] is False
    with pytest.raises(ApplicationServiceError) as status_error:
        service.change_status("mission-a", MissionRequest.APPROVE, 4)
    assert status_error.value.status_code == 409
    assert rest.requests == []


def test_failed_status_command_preserves_the_previous_mission_status(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)
    service.initialize(
        {
            "mission_id": "mission-a",
            "behavior": 0,
            "vehicles": ["robot-a"],
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Point",
                            "coordinates": [4.0, 50.0],
                        }
                    }
                ]
            },
        }
    )
    runtime.missions["mission-a"] = {
        "mission_id": "mission-a",
        "status": 1,
        "status_name": "PLANNED",
        "status_source": "mission_feedback",
        "config": {},
    }
    rest.status_response = LegacyRestResponse(False, 503, "unavailable")

    with pytest.raises(ApplicationServiceError) as error:
        service.change_status("mission-a", MissionRequest.APPROVE, 4)

    state = runtime.missions["mission-a"]
    assert error.value.status_code == 502
    assert state["status"] == 1
    assert state["status_name"] == "PLANNED"
    assert state["status_source"] == "mission_feedback"
    assert state["command_phase"] == "approve_failed"
    assert state["last_command_ok"] is False


def test_status_command_rejects_unknown_mission_without_calling_rest(tmp_path: Path) -> None:
    service, _, rest = _service(tmp_path)

    with pytest.raises(ApplicationServiceError) as error:
        service.change_status("missing", MissionRequest.APPROVE, 4)

    assert error.value.status_code == 404
    assert rest.requests == []


def test_status_command_cannot_target_an_older_initialized_mission(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)

    def mission(mission_id: str) -> dict[str, Any]:
        return {
            "mission_id": mission_id,
            "behavior": 0,
            "vehicles": ["robot-a"],
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Point",
                            "coordinates": [4.0, 50.0],
                        }
                    }
                ]
            },
        }

    service.initialize(mission("mission-a"))
    service.initialize(mission("mission-b"))

    with pytest.raises(ApplicationServiceError) as error:
        service.change_status("mission-a", MissionRequest.APPROVE, 4)

    assert error.value.status_code == 409
    assert runtime.command_target_mission_id == "mission-b"
    assert runtime.missions["mission-a"]["command_target"] is False
    assert runtime.missions["mission-b"]["command_target"] is True
    assert rest.requests == []

    runtime.missions["mission-b"].update({"status": 1, "status_name": "PLANNED"})
    accepted = service.change_status("mission-b", MissionRequest.APPROVE, 4)
    assert accepted["status_name"] == "ACCEPTED"
    assert rest.requests == [MissionRequest.APPROVE]


def test_status_command_requires_reinitialize_after_command_target_is_lost(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)
    runtime.missions["mission-a"] = {
        "mission_id": "mission-a",
        "status": 1,
        "status_name": "PLANNED",
        "config": {},
    }

    with pytest.raises(ApplicationServiceError) as error:
        service.change_status("mission-a", MissionRequest.APPROVE, 4)

    assert error.value.status_code == 409
    assert rest.requests == []


def test_status_command_enforces_mission_lifecycle_without_calling_rest(tmp_path: Path) -> None:
    service, runtime, rest = _service(tmp_path)
    service.initialize(
        {
            "mission_id": "mission-a",
            "behavior": 0,
            "vehicles": ["robot-a"],
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Point",
                            "coordinates": [4.0, 50.0],
                        }
                    }
                ]
            },
        }
    )

    with pytest.raises(ApplicationServiceError) as approve_error:
        service.change_status("mission-a", MissionRequest.APPROVE, 4)
    assert approve_error.value.status_code == 409
    assert "expected PLANNED or PLANNED_ALTERNATIVE" in str(approve_error.value)

    runtime.missions["mission-a"].update({"status": 1, "status_name": "PLANNED"})
    with pytest.raises(ApplicationServiceError) as start_error:
        service.change_status("mission-a", MissionRequest.START, 5)
    assert start_error.value.status_code == 409
    assert "expected ACCEPTED" in str(start_error.value)
    assert rest.requests == []


def test_scenario_application_replaces_adapter_state_after_activation() -> None:
    runtime = SimpleNamespace(
        missions={"old": {}},
        forgotten_missions=set(),
        agent_updates={"robot": {}},
        planner_state={"state": 2},
        command_target_mission_id="old",
    )
    service = ScenarioApplicationService(runtime, ReadyScenario())

    result = asyncio.run(service.activate({"agents": [{"agent_id": "robot-a"}]}))

    assert result["agents"] == [{"agent_id": "robot-a"}]
    assert runtime.missions == {}
    assert runtime.agent_updates == {}
    assert runtime.planner_state == {}
    assert runtime.command_target_mission_id is None


def test_scenario_application_preserves_adapter_state_on_idempotent_reuse() -> None:
    runtime = SimpleNamespace(
        missions={"current": {"status": 5}},
        forgotten_missions=set(),
        agent_updates={"robot-a": {"status": "active"}},
        planner_state={"mission_id": "current", "state": 2},
        command_target_mission_id="current",
    )
    original_missions = runtime.missions
    original_agents = runtime.agent_updates
    original_planner = runtime.planner_state
    scenario = ReadyScenario()
    scenario.activate = lambda payload: {  # type: ignore[method-assign]
        **scenario.require_ready(),
        "idempotent_reuse": True,
    }
    service = ScenarioApplicationService(runtime, scenario)

    result = asyncio.run(service.activate({"scenario_id": "scenario-a"}))

    assert result["idempotent_reuse"] is True
    assert runtime.missions is original_missions
    assert runtime.agent_updates is original_agents
    assert runtime.planner_state is original_planner
    assert runtime.command_target_mission_id == "current"


class _FakeMongoAdmin:
    def command(self, name: str) -> dict[str, int]:
        assert name == "ping"
        return {"ok": 1}


class _FakeActiveCollection:
    def __init__(self, marker: dict[str, Any] | None) -> None:
        self.marker = marker

    def find_one(self, query: dict[str, Any], projection: dict[str, int]) -> dict[str, Any] | None:
        assert query == {"singleton": "active"}
        assert projection == {"_id": 0, "singleton": 0}
        return deepcopy(self.marker)


class _FakeMapDatabase:
    def __init__(self, marker: dict[str, Any] | None) -> None:
        self.marker = marker

    def __getitem__(self, collection: str) -> _FakeActiveCollection:
        assert collection == scenario_runtime.ACTIVE_SCENARIO_COLLECTION
        return _FakeActiveCollection(self.marker)


class _FakeMongoClient:
    def __init__(self, marker: dict[str, Any] | None) -> None:
        self.marker = marker
        self.admin = _FakeMongoAdmin()

    def __enter__(self) -> "_FakeMongoClient":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def __getitem__(self, database: str) -> _FakeMapDatabase:
        assert database == "MapDB"
        return _FakeMapDatabase(self.marker)


def test_reachable_mongo_without_active_marker_ignores_ready_file_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_dir = tmp_path / "data" / "runtime"
    runtime_dir.mkdir(parents=True)
    cached = {
        "scenario_id": "cached-only",
        "status": "ready",
        "ready": True,
        "map_collection": "scenario_cached_only_v1",
    }
    (runtime_dir / scenario_runtime.ACTIVE_STATE_FILE).write_text(
        json.dumps(cached), encoding="utf-8"
    )
    monkeypatch.setattr(
        scenario_runtime,
        "MongoClient",
        lambda *args, **kwargs: _FakeMongoClient(None),
    )
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://reachable")

    assert manager.active() is None
    assert manager.validated_active() is None
    with pytest.raises(scenario_runtime.ScenarioNotReadyError):
        manager.require_ready()


def test_unavailable_mongo_exposes_cache_as_non_authoritative_stale_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_dir = tmp_path / "data" / "runtime"
    runtime_dir.mkdir(parents=True)
    cached = {
        "scenario_id": "cached-only",
        "status": "ready",
        "ready": True,
        "map_collection": "scenario_cached_only_v1",
    }
    cache_path = runtime_dir / scenario_runtime.ACTIVE_STATE_FILE
    cache_path.write_text(json.dumps(cached), encoding="utf-8")

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise scenario_runtime.PyMongoError("database offline")

    monkeypatch.setattr(scenario_runtime, "MongoClient", unavailable)
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://offline")
    manager._active_runtime_issues = lambda state: []  # type: ignore[method-assign]
    manager._planner_readiness_issue = lambda state: None  # type: ignore[method-assign]

    diagnostic = manager.validated_active()

    assert diagnostic is not None
    assert diagnostic["status"] == "stale"
    assert diagnostic["ready"] is False
    assert diagnostic["cached_status"] == "ready"
    assert diagnostic["cache_diagnostic_only"] is True
    assert diagnostic["durable_authority"] == "unavailable"
    assert "database offline" in diagnostic["error"]
    assert json.loads(cache_path.read_text(encoding="utf-8")) == cached
    with pytest.raises(scenario_runtime.ScenarioNotReadyError):
        manager.require_ready()


def test_identical_healthy_scenario_activation_is_idempotent() -> None:
    payload = {
        "scenario_id": "same-scenario",
        "name": "Same scenario",
        "map": "rma",
        "agents": [{"agent_id": "robot-a"}],
        "feature_ids": ["60bae762-6c7a-4b11-8803-556fdfee4425"],
        "road_imports": [],
    }
    snapshot = build_scenario_snapshot(ROOT, payload)
    current = {
        **{key: value for key, value in snapshot.items() if key != "features"},
        "status": "ready",
        "ready": True,
    }
    manager = ScenarioRuntimeManager(ROOT, ROOT, "mongodb://unused", docker_socket="/missing")
    manager.active = lambda: current  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: []  # type: ignore[method-assign]
    manager._planner_readiness_issue = lambda state: None  # type: ignore[method-assign]

    result = manager.activate(payload)

    assert result["idempotent_reuse"] is True
    assert result["map_collection"] == snapshot["map_collection"]


def test_planner_readiness_survives_marker_log_rollout_for_same_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = ScenarioRuntimeManager(ROOT, ROOT, "mongodb://unused", docker_socket="/missing")
    state = {
        "map_collection": "scenario_a_v1",
        "activation_token": "token-a",
        "verified_at": "2026-08-27T12:30:56+00:00",
    }
    planner_started_at = "2026-08-27T12:30:11Z"

    def docker_request(socket: str, method: str, path: str) -> tuple[int, Any]:
        if path.endswith("/logs?stdout=1&stderr=1&tail=1000"):
            return 200, "large plan output pushed the startup marker out of this tail"
        if path.endswith("/json"):
            return 200, {
                "State": {"Running": True, "StartedAt": planner_started_at}
            }
        raise AssertionError(path)

    monkeypatch.setattr(scenario_runtime, "_docker_request", docker_request)

    assert manager._planner_readiness_issue(state) is None  # noqa: SLF001

    planner_started_at = "2026-08-27T12:31:11Z"
    assert "has not reported" in manager._planner_readiness_issue(state)  # type: ignore[operator]  # noqa: SLF001


def test_identical_scenario_activation_does_not_reuse_wrong_planner_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "scenario_id": "same-scenario",
        "name": "Same scenario",
        "map": "rma",
        "agents": [{"agent_id": "robot-a"}],
        "feature_ids": ["60bae762-6c7a-4b11-8803-556fdfee4425"],
        "road_imports": [],
    }
    snapshot = build_scenario_snapshot(ROOT, payload)
    current = {
        **{key: value for key, value in snapshot.items() if key != "features"},
        "status": "ready",
        "ready": True,
        "activation_token": "activation-1",
    }
    manager = ScenarioRuntimeManager(ROOT, ROOT, "mongodb://unused", docker_socket="/missing")
    transitions: list[dict[str, Any]] = []
    planner_requests: list[tuple[str, str, str]] = []
    manager.active = lambda: current  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: []  # type: ignore[method-assign]
    manager._publish_transition = lambda state: transitions.append(deepcopy(state))  # type: ignore[method-assign]
    manager._persist_immutable_snapshot = lambda state: (_ for _ in ()).throw(  # type: ignore[method-assign]
        RuntimeError("full activation started")
    )
    manager._record_activation_best_effort = lambda state: None  # type: ignore[method-assign]
    manager._publish_observed_state = lambda state: None  # type: ignore[method-assign]

    def wrong_planner_token(socket: str, method: str, path: str) -> tuple[int, str]:
        planner_requests.append((socket, method, path))
        return (
            200,
            f"MAP IS LOADED collection=MapDB.{snapshot['map_collection']} "
            "activation=wrong-token",
        )

    monkeypatch.setattr(scenario_runtime, "_docker_request", wrong_planner_token)

    with pytest.raises(
        scenario_runtime.ScenarioNotReadyError,
        match="full activation started",
    ):
        manager.activate(payload)

    assert planner_requests == [
        (
            "/missing",
            "GET",
            "/containers/c2-imugs2-backend-planner/logs?stdout=1&stderr=1&tail=1000",
        )
    ]
    assert len(transitions) == 1
    assert transitions[0]["status"] == "activating"


def test_scenario_activation_publishes_durable_phases_before_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "scenario_id": "phase-scenario",
        "name": "Phase scenario",
        "map": "rma",
        "agents": [{"agent_id": "robot-a"}],
        "feature_ids": ["60bae762-6c7a-4b11-8803-556fdfee4425"],
        "road_imports": [],
    }
    manager = ScenarioRuntimeManager(ROOT, ROOT, "mongodb://unused", docker_socket="/missing")
    transitions: list[dict[str, Any]] = []
    restarted: list[tuple[str, str]] = []
    manager.active = lambda: None  # type: ignore[method-assign]
    manager._publish_transition = lambda state: transitions.append(deepcopy(state))  # type: ignore[method-assign]
    manager._persist_immutable_snapshot = lambda snapshot: None  # type: ignore[method-assign]
    manager._write_planner_config = lambda collection, token: None  # type: ignore[method-assign]
    manager._replace_previous_runtime = lambda previous: None  # type: ignore[method-assign]
    manager._clear_scenario_runtime_records = lambda: None  # type: ignore[method-assign]
    manager._restart_container = lambda container, label: restarted.append(  # type: ignore[method-assign]
        (container, label)
    )
    manager._restart_planner = lambda: restarted.append(  # type: ignore[method-assign]
        (scenario_runtime.PLANNER_CONTAINER, "planner")
    )
    manager._wait_until_ready = lambda snapshot, containers, token: None  # type: ignore[method-assign]
    manager._clear_mission_runtime_records = lambda: None  # type: ignore[method-assign]
    monkeypatch.setattr(
        scenario_runtime,
        "launch_scenario",
        lambda *args, **kwargs: {
            "docker_started": True,
            "containers": [{"container_name": "scenario-robot-a"}],
        },
    )

    ready = manager.activate(payload)

    phases = [transition["activation_phase"] for transition in transitions]
    assert phases == [
        "validated",
        "snapshot_persisted",
        "planner_configured",
        "previous_runtime_stopped",
        "runtime_records_cleared",
        "backend_restarted",
        "robots_launched",
        "runtime_verified",
        "ready",
    ]
    assert len({transition["activation_id"] for transition in transitions}) == 1
    assert all(transition["ready"] is False for transition in transitions[:-1])
    assert ready["ready"] is True
    assert [entry["phase"] for entry in ready["phase_history"]] == phases
    assert restarted == [
        (scenario_runtime.COORDINATION_CONTAINER, "centralized coordination"),
        (scenario_runtime.PLANNER_CONTAINER, "planner"),
        (scenario_runtime.C2_REST_CONTAINER, "C2 REST bridge"),
        (scenario_runtime.ROSBRIDGE_CONTAINER, "rosbridge"),
    ]
