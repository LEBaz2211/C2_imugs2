from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import c2_imugs2.legacy_map as legacy_map
from c2_imugs2.api import (
    create_app as _create_app,
    _inline_user_feature_refs,
    _load_forgotten_missions,
    _mission_state_from_legacy_feedback,
    _mission_updates_from_planner_state,
    _normalize_edge_feedback,
    _normalize_mission_feedback,
    _planned_paths_from_planning_doc,
)
from c2_imugs2.domain import MissionRequest
from c2_imugs2.legacy_rest import LegacyRestResponse, to_legacy_mission_config
from c2_imugs2.scenario_launch import launch_scenario
from c2_imugs2.scenario_runtime import ScenarioNotReadyError, ScenarioRuntimeManager, build_scenario_snapshot


ROOT = Path(__file__).resolve().parents[1]


class FakeRestClient:
    def __init__(self) -> None:
        self.initialized: list[dict[str, Any]] = []
        self.status_changes: list[MissionRequest] = []

    def health(self) -> LegacyRestResponse:
        return LegacyRestResponse(True, 204, "")

    def initialize_mission(self, mission_config: dict[str, Any]) -> LegacyRestResponse:
        self.initialized.append(mission_config)
        return LegacyRestResponse(True, 200, "initialized")

    def change_status(self, requested_status: MissionRequest) -> LegacyRestResponse:
        self.status_changes.append(requested_status)
        return LegacyRestResponse(True, 200, "changed")


class FakeRosbridgeClient:
    url = "ws://fake-rosbridge:9090"

    async def diagnostics(self) -> dict[str, Any]:
        return {
            "rosbridge_url": self.url,
            "nodes": ["/c2_node", "/planner_node"],
            "topics": ["/multi_robot/mission_init_request"],
            "services": ["/rosapi/nodes"],
            "checks": [
                {"id": "rosbridge.websocket", "status": "ok", "message": "rosbridge reachable"},
                {"id": "ros.nodes.required", "status": "ok", "message": "required ROS nodes visible"},
                {"id": "ros.topics.required", "status": "ok", "message": "required ROS topics visible"},
            ],
        }


class ReadyScenarioManager:
    def active(self) -> dict[str, Any]:
        return {
            "scenario_id": "test-scenario",
            "name": "Test scenario",
            "version": "test-version",
            "map_collection": "scenario_test_testversion",
            "status": "ready",
            "ready": True,
        }

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]:
        return self.active()

    def validated_active(self) -> dict[str, Any] | None:
        return self.active()

    def activate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {**self.active(), "agents": payload.get("agents") or [], "containers": [], "message": "ready"}

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [
            {
                "scenario_id": "test-scenario",
                "name": "Test scenario",
                "map": "rma",
                "agents": [],
                "feature_ids": [],
                "road_imports": [],
                "runtime_active": True,
            }
        ]


class InactiveScenarioManager(ReadyScenarioManager):
    def active(self) -> None:
        return None

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]:
        raise ScenarioNotReadyError("activate a scenario first")


def create_app(*args: Any, **kwargs: Any):
    kwargs.setdefault("scenario_manager", ReadyScenarioManager())
    return _create_app(*args, **kwargs)


def test_health_and_diagnostics_shape() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    health = client.get("/api/health").json()
    diagnostics = client.get("/api/diagnostics").json()

    assert health["status"] == "ok"
    assert health["legacy_rest"]["ok"] is True
    assert diagnostics["legacy_rest"]["ok"] is True
    assert diagnostics["checks"][0]["id"] == "legacy_rest"
    assert diagnostics["ros"]["nodes"]


def test_mission_init_is_rejected_until_scenario_is_ready() -> None:
    rest = FakeRestClient()
    app = _create_app(
        ROOT,
        rest_client=rest,
        rosbridge_client=FakeRosbridgeClient(),
        scenario_manager=InactiveScenarioManager(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "behavior": 0,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "objective": {"geometry": {"geometry_type": "Point", "coordinates": [4.39218, 50.84417]}},
        },
    )

    assert response.status_code == 409
    assert "activate a scenario" in response.json()["detail"]
    assert rest.initialized == []


def test_scenario_activation_endpoint_reports_authoritative_runtime() -> None:
    client = TestClient(
        _create_app(
            ROOT,
            rest_client=FakeRestClient(),
            rosbridge_client=FakeRosbridgeClient(),
            scenario_manager=ReadyScenarioManager(),
        )
    )

    response = client.post(
        "/api/scenarios/activate",
        json={"scenario_id": "scenario-a", "map": "rma", "agents": [{"agent_id": "agent-a"}]},
    )

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["agents"] == [{"agent_id": "agent-a"}]


def test_scenario_catalog_endpoint_returns_activated_scenarios() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    assert response.json()["scenarios"][0]["scenario_id"] == "test-scenario"
    assert response.json()["scenarios"][0]["runtime_active"] is True


def test_scenario_snapshot_is_deterministic_and_normalizes_osm_to_mapdb_roads() -> None:
    payload = {
        "scenario_id": "Scenario One",
        "name": "Scenario One",
        "map": "rma",
        "agents": [{"agent_id": "agent-a"}],
        "feature_ids": ["dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e"],
        "road_imports": [
            {
                "import_id": "polygon-roads",
                "geojson": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "id": "way/123",
                            "properties": {"name": "Frozen road"},
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [[4.392, 50.844], [4.393, 50.845]],
                            },
                        }
                    ],
                },
            }
        ],
    }

    first = build_scenario_snapshot(ROOT, payload)
    second = build_scenario_snapshot(ROOT, payload)

    assert first["version"] == second["version"]
    assert first["map_collection"] == second["map_collection"]
    assert first["feature_count"] == 2
    assert first["road_count"] == 1
    road = next(feature for feature in first["features"] if feature["properties"]["feature_type"] == "road")
    assert road["properties"]["source"] == "frozen_openstreetmap"


def test_invalid_scenario_draft_does_not_replace_ready_active_runtime(tmp_path: Path) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    previous = {
        "scenario_id": "already-active",
        "status": "ready",
        "ready": True,
        "version": "v1",
        "map_collection": "scenario_already_active_v1",
    }
    (runtime / "active_scenario.json").write_text(json.dumps(previous), encoding="utf-8")
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://unused", docker_socket="/missing")
    manager.active = lambda: deepcopy(previous)  # type: ignore[method-assign]

    try:
        manager.activate({"scenario_id": "invalid", "map": "missing", "agents": [{"agent_id": "a"}]})
    except ScenarioNotReadyError:
        pass
    else:
        raise AssertionError("invalid scenario activation should fail")

    assert manager.active() == previous


def test_stale_external_runtime_invalidates_ready_scenario(tmp_path: Path) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    ready = {
        "scenario_id": "stale-scenario",
        "status": "ready",
        "ready": True,
        "version": "v1",
        "map_collection": "scenario_stale_v1",
    }
    (runtime / "active_scenario.json").write_text(json.dumps(ready), encoding="utf-8")
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://unused", docker_socket="/missing")
    manager.active = lambda: deepcopy(ready)  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: ["MapDB.scenario_stale_v1 is missing"]  # type: ignore[method-assign]
    manager._mark_active_in_mongo = lambda state: None  # type: ignore[method-assign]

    stale = manager.validated_active()

    assert stale is not None
    assert stale["status"] == "stale"
    assert stale["ready"] is False
    assert "is missing" in stale["error"]
    try:
        manager.require_ready()
    except ScenarioNotReadyError as exc:
        assert "runtime is not ready" in str(exc)
    else:
        raise AssertionError("a stale runtime must reject mission commands")


def test_ready_runtime_requires_exact_planner_proof(tmp_path: Path, monkeypatch) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    ready = {
        "scenario_id": "missing-planner-proof",
        "status": "ready",
        "ready": True,
        "version": "v1",
        "map_collection": "scenario_missing_planner_proof_v1",
        "activation_token": "activation-1",
    }
    (runtime / "active_scenario.json").write_text(json.dumps(ready), encoding="utf-8")
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://unused", docker_socket="/missing")
    published: list[dict[str, Any]] = []
    manager.active = lambda: deepcopy(ready)  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: []  # type: ignore[method-assign]
    manager._publish_observed_state = lambda state: published.append(deepcopy(state))  # type: ignore[method-assign]
    monkeypatch.setattr(
        "c2_imugs2.scenario_runtime._docker_request",
        lambda socket, method, path: (
            200,
            "MAP IS LOADED collection=MapDB.scenario_missing_planner_proof_v1 "
            "activation=wrong-token",
        ),
    )

    result = manager.validated_active()

    assert result is not None
    assert result["status"] == "stale"
    assert result["ready"] is False
    assert "planner has not reported the active MapDB collection and activation token" in result["error"]
    assert published == [result]


def test_ready_runtime_accepts_matching_planner_collection_and_token(
    tmp_path: Path, monkeypatch
) -> None:
    ready = {
        "scenario_id": "matching-planner-proof",
        "status": "ready",
        "ready": True,
        "version": "v1",
        "map_collection": "scenario_matching_planner_proof_v1",
        "activation_token": "activation-1",
    }
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://unused", docker_socket="/missing")
    requests: list[tuple[str, str, str]] = []
    manager.active = lambda: deepcopy(ready)  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: []  # type: ignore[method-assign]

    def planner_logs(socket: str, method: str, path: str) -> tuple[int, str]:
        requests.append((socket, method, path))
        return (
            200,
            "MAP IS LOADED collection=MapDB.scenario_matching_planner_proof_v1 "
            "activation=activation-1",
        )

    monkeypatch.setattr("c2_imugs2.scenario_runtime._docker_request", planner_logs)

    result = manager.validated_active()

    assert result == ready
    assert requests == [
        (
            "/missing",
            "GET",
            "/containers/c2-imugs2-backend-planner/logs?stdout=1&stderr=1&tail=1000",
        )
    ]


def test_stale_runtime_recovers_after_all_readiness_proofs_return(tmp_path: Path) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    ready = {
        "scenario_id": "recovering-scenario",
        "status": "ready",
        "ready": True,
        "version": "v1",
        "map_collection": "scenario_recovering_v1",
        "activation_token": "activation-1",
    }
    (runtime / "active_scenario.json").write_text(json.dumps(ready), encoding="utf-8")
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://unused", docker_socket="/missing")
    issues = ["robots are not registered: robot-a"]
    published: list[dict[str, Any]] = []
    manager.active = lambda: deepcopy(published[-1] if published else ready)  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: list(issues)  # type: ignore[method-assign]
    manager._planner_readiness_issue = lambda state: None  # type: ignore[method-assign]
    manager._publish_observed_state = lambda state: published.append(deepcopy(state))  # type: ignore[method-assign]

    stale = manager.validated_active()
    issues.clear()
    recovered = manager.validated_active()

    assert stale is not None
    assert stale["status"] == "stale"
    assert recovered is not None
    assert recovered["status"] == "ready"
    assert recovered["ready"] is True
    assert "recovered_at" in recovered
    assert "error" not in recovered
    assert "stale_at" not in recovered
    assert manager.active() == recovered
    assert published[-1]["status"] == "ready"


def test_stale_runtime_does_not_recover_without_exact_planner_proof(tmp_path: Path) -> None:
    runtime = tmp_path / "data" / "runtime"
    runtime.mkdir(parents=True)
    stale = {
        "scenario_id": "still-stale",
        "status": "stale",
        "ready": False,
        "version": "v1",
        "map_collection": "scenario_still_stale_v1",
        "activation_token": "activation-1",
        "error": "active scenario runtime is stale: robots are not registered: robot-a",
    }
    (runtime / "active_scenario.json").write_text(json.dumps(stale), encoding="utf-8")
    manager = ScenarioRuntimeManager(tmp_path, tmp_path, "mongodb://unused", docker_socket="/missing")
    manager.active = lambda: deepcopy(stale)  # type: ignore[method-assign]
    manager._active_runtime_issues = lambda state: []  # type: ignore[method-assign]
    manager._planner_readiness_issue = lambda state: "planner proof is missing"  # type: ignore[method-assign]
    manager._mark_active_in_mongo = lambda state: None  # type: ignore[method-assign]

    result = manager.validated_active()

    assert result is not None
    assert result["status"] == "stale"
    assert result["ready"] is False
    assert "planner proof is missing" in result["error"]


def test_forget_mission_removes_adapter_runtime_record() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    mission = (ROOT / "fixtures" / "mission_examples" / "simple_navigation_themis.json").read_text(encoding="utf-8")

    initialized = client.post("/api/missions/init", content=mission, headers={"content-type": "application/json"}).json()
    removed = client.delete(f"/api/missions/{initialized['mission_id']}").json()
    diagnostics = client.get("/api/diagnostics").json()

    assert removed["removed"] is True
    assert removed["mission_id"] == initialized["mission_id"]
    assert diagnostics["missions"] == []


def test_forget_mission_persists_hidden_runtime_record(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "behavior": 0,
        "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
        "objective": {"geometry": {"geometry_type": "Point", "coordinates": [4.39218, 50.84417]}},
    }

    initialized = client.post("/api/missions/init", json=mission).json()
    client.delete(f"/api/missions/{initialized['mission_id']}")

    assert _load_forgotten_missions(tmp_path) == {initialized["mission_id"]}


def test_map_features_returns_legacy_geojson() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    response = client.get("/api/map/features?map=rma")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert payload["features"]
    assert {feature["properties"]["feature_type"] for feature in payload["features"]} >= {"road", "risk", "geofence"}


def test_create_map_feature_persists_user_geojson(tmp_path: Path) -> None:
    legacy_map_dir = tmp_path / "legacy_ros" / "config" / "data" / "map" / "rma" / "free_polygons"
    legacy_map_dir.mkdir(parents=True)
    (legacy_map_dir / "workspace.geojson").write_text(
        '{"type":"Feature","properties":{"feature_type":"workspace","name":"base"},'
        '"geometry":{"type":"Polygon","coordinates":[[[4.0,50.0],[4.1,50.0],[4.1,50.1],[4.0,50.0]]]}}',
        encoding="utf-8",
    )
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    feature = {
        "type": "Feature",
        "properties": {"feature_type": "objective", "name": "drawn point"},
        "geometry": {"type": "Point", "coordinates": [4.05, 50.05]},
    }

    created = client.post("/api/map/features?map=rma", json=feature).json()
    reloaded = client.get("/api/map/features?map=rma").json()

    assert created["map_feature"]["name"] == "drawn point"
    assert created["map_feature"]["feature_type"] == "objective"
    assert any(item["properties"].get("name") == "drawn point" for item in reloaded["features"])


def test_query_osm_roads_returns_scenario_overlay_without_persisting(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        legacy_map,
        "_query_overpass_roads",
        lambda bbox: {
            "elements": [
                {
                    "type": "way",
                    "id": 321,
                    "tags": {"highway": "residential", "name": "Scenario Road"},
                    "geometry": [{"lon": 4.05, "lat": 50.05}, {"lon": 4.06, "lat": 50.06}],
                }
            ]
        },
    )
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    payload = client.post("/api/map/osm-roads/query?map=rma", json={"bbox": [4.04, 50.04, 4.07, 50.07]}).json()

    assert payload["persisted"] is False
    assert payload["feature_count"] == 1
    assert payload["features"][0]["properties"]["feature_type"] == "scenario_osm_road"
    assert payload["features"][0]["properties"]["source_tool"] == "scenario_lab_osm_section"
    assert not (tmp_path / "data" / "runtime" / "user_features_rma.geojson").exists()


def test_query_osm_roads_for_polygon_clips_to_geofence(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        legacy_map,
        "_query_overpass_roads",
        lambda bbox: {
            "elements": [
                {
                    "type": "way",
                    "id": 411,
                    "tags": {"highway": "residential", "name": "Inside Road"},
                    "geometry": [{"lon": 4.05, "lat": 50.05}, {"lon": 4.06, "lat": 50.06}],
                },
                {
                    "type": "way",
                    "id": 412,
                    "tags": {"highway": "service", "name": "Outside Road"},
                    "geometry": [{"lon": 4.10, "lat": 50.05}, {"lon": 4.11, "lat": 50.06}],
                },
                {
                    "type": "way",
                    "id": 413,
                    "tags": {"highway": "path", "name": "Crossing Path"},
                    "geometry": [{"lon": 4.03, "lat": 50.05}, {"lon": 4.08, "lat": 50.05}],
                },
            ]
        },
    )
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    polygon = [[4.04, 50.04], [4.07, 50.04], [4.07, 50.07], [4.04, 50.07], [4.04, 50.04]]

    payload = client.post("/api/map/osm-roads/query?map=rma", json={"bbox": [4.04, 50.04, 4.07, 50.07], "polygon": polygon}).json()

    names = {feature["properties"]["name"] for feature in payload["features"]}
    assert payload["persisted"] is False
    assert payload["clipped_to_polygon"] is True
    assert payload["feature_count"] == 2
    assert payload["source_way_count"] == 2
    assert names == {"Inside Road", "Crossing Path"}
    for feature in payload["features"]:
        assert feature["properties"]["source_tool"] == "scenario_lab_osm_polygon"
        for lon, lat in feature["geometry"]["coordinates"]:
            assert 4.04 - 1e-7 <= lon <= 4.07 + 1e-7
            assert 50.04 - 1e-7 <= lat <= 50.07 + 1e-7
    assert not (tmp_path / "data" / "runtime" / "user_features_rma.geojson").exists()


def test_launch_scenario_generates_backend_edge_configs_without_docker(tmp_path: Path) -> None:
    payload = {
        "scenario_id": "Scenario One",
        "name": "Scenario One",
        "agents": [
            {
                "agent_id": "11111111-2222-4333-8444-555555555555",
                "name": "Scout 1",
                "vehicle_type": "UGV",
                "current_location": [4.123456, 50.654321],
                "constraints": {"max_speed": 3.2, "max_acceleration": 6.5, "max_weight": 20, "max_tilt_angle": 1.1},
            }
        ],
    }

    result = launch_scenario(tmp_path, payload, host_repo_root=tmp_path, docker_socket=str(tmp_path / "missing-docker.sock"))

    assert result["status"] == "generated"
    assert result["docker_started"] is False
    assert result["agent_count"] == 1
    assert "Docker socket is not available" in result["message"]
    container = result["containers"][0]
    autonomy_config = Path(container["autonomy_config"]).read_text(encoding="utf-8")
    compose = (tmp_path / "data" / "runtime" / "scenario_launches" / "scenario-one" / "docker-compose.scenario.yml").read_text(encoding="utf-8")
    assert "start_location: [4.1234560, 50.6543210]" in autonomy_config
    assert "max_speed: 3.2" in autonomy_config
    assert "sensors" not in autonomy_config
    assert "c2-imugs2/backend-edge-agent-sim:local" in compose
    assert "/backend/config/config_agent-tasks-supervisor.yaml:/app/config.yaml:ro" in compose
    assert "AUTONOMY_TOPIC_PREFIX: Scout_1" in compose
    assert 'ROS_LOCALHOST_ONLY: "1"' in compose
    assert "<MaxAutoParticipantIndex>120</MaxAutoParticipantIndex>" in compose


def test_delete_map_feature_removes_only_user_geojson(tmp_path: Path) -> None:
    legacy_map_dir = tmp_path / "legacy_ros" / "config" / "data" / "map" / "rma" / "free_polygons"
    legacy_map_dir.mkdir(parents=True)
    (legacy_map_dir / "workspace.geojson").write_text(
        '{"type":"Feature","properties":{"feature_id":"legacy-workspace","feature_type":"workspace","name":"base"},'
        '"geometry":{"type":"Polygon","coordinates":[[[4.0,50.0],[4.1,50.0],[4.1,50.1],[4.0,50.0]]]}}',
        encoding="utf-8",
    )
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    created = client.post(
        "/api/map/features?map=rma",
        json={
            "type": "Feature",
            "properties": {"feature_id": "runtime-point", "feature_type": "objective", "name": "runtime point"},
            "geometry": {"type": "Point", "coordinates": [4.05, 50.05]},
        },
    ).json()

    deleted = client.delete("/api/map/features/runtime-point?map=rma").json()
    legacy_delete = client.delete("/api/map/features/legacy-workspace?map=rma")
    reloaded = client.get("/api/map/features?map=rma").json()

    assert created["map_feature"]["feature_id"] == "runtime-point"
    assert deleted["deleted_feature_id"] == "runtime-point"
    assert legacy_delete.status_code == 404
    assert not any(item["properties"].get("feature_id") == "runtime-point" for item in reloaded["features"])
    assert any(item["properties"].get("feature_id") == "legacy-workspace" for item in reloaded["features"])


def test_user_map_feature_update_and_geometry_validation(tmp_path: Path) -> None:
    legacy_map_dir = tmp_path / "legacy_ros" / "config" / "data" / "map" / "rma" / "free_polygons"
    legacy_map_dir.mkdir(parents=True)
    (legacy_map_dir / "workspace.geojson").write_text(
        '{"type":"Feature","properties":{"feature_id":"legacy-workspace","feature_type":"workspace","name":"base"},'
        '"geometry":{"type":"Polygon","coordinates":[[[4.0,50.0],[4.1,50.0],[4.1,50.1],[4.0,50.0]]]}}',
        encoding="utf-8",
    )
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    client.post(
        "/api/map/features?map=rma",
        json={
            "type": "Feature",
            "properties": {"feature_id": "runtime-objective", "feature_type": "objective", "name": "old objective"},
            "geometry": {"type": "Point", "coordinates": [4.05, 50.05]},
        },
    )

    edited = client.put(
        "/api/map/features/runtime-objective?map=rma",
        json={
            "type": "Feature",
            "properties": {"feature_type": "objective", "name": "new objective"},
            "geometry": {"type": "Point", "coordinates": [4.06, 50.06]},
        },
    ).json()
    rejected = client.post(
        "/api/map/features?map=rma",
        json={
            "type": "Feature",
            "properties": {"feature_type": "objective", "name": "bad objective"},
            "geometry": {"type": "Polygon", "coordinates": [[[4.0, 50.0], [4.1, 50.0], [4.0, 50.0]]]},
        },
    )

    assert edited["map_feature"]["name"] == "new objective"
    assert edited["map_feature"]["geometry"]["coordinates"] == [4.06, 50.06]
    assert rejected.status_code == 422
    assert "objective features must use geometry type: Point" in rejected.text


def test_runtime_bootstrap_includes_agents_map_features_and_geojson() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    payload = client.get("/api/runtime/bootstrap?map=rma").json()

    assert [agent["agent_id"] for agent in payload["agents"]] == ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"]
    assert payload["map_features"]
    assert payload["geojson"]["type"] == "FeatureCollection"


def test_mission_examples_and_legacy_trace() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    examples = client.get("/api/mission-examples").json()
    trace = client.get("/api/legacy/trace").json()

    assert {example["id"] for example in examples["examples"]} >= {"simple_navigation_themis", "parade_coverage_themis"}
    assert all(example["config"]["vehicles"] == ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"] for example in examples["examples"])
    assert trace["steps"][0]["id"] == "adapter.api"
    assert "ros" in trace


def test_contract_graph_exposes_system_contracts() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    graph = client.get("/api/contracts?include_runtime=false").json()
    node_ids = {node["id"] for node in graph["nodes"]}
    scenario_ids = {scenario["id"] for scenario in graph["scenarios"]}

    assert graph["summary"]["nodes"] > 20
    assert "http:POST /api/missions/init" in node_ids
    assert "ros:service:/multi_robot/planner/create" in node_ids
    assert "schema:mission_config.schema.json" in node_ids
    assert "mongo:MapDB.rma" in node_ids
    assert "mission_lifecycle" in scenario_ids
    assert "unsupported_no_planning" in scenario_ids
    scenarios = {scenario["id"]: scenario for scenario in graph["scenarios"]}
    assert "lawnmower sweep" in scenarios["coverage_zone"]["summary"]
    assert "does not add mission geometry" in scenarios["mission_roads"]["summary"]
    assert graph["source_digest"]


def test_verified_contract_atlas_is_closed_and_source_backed() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    atlas = client.get("/api/contracts?include_runtime=false").json()["atlas"]
    component_ids = {component["id"] for component in atlas["components"]}
    interaction_ids = {interaction["id"] for interaction in atlas["interactions"]}

    assert atlas["verification"]["status"] == "source_verified"
    assert atlas["verification"]["runtime_status"] == "not_connected"
    assert component_ids >= {
        "browser_ui",
        "fastapi_adapter",
        "legacy_rest",
        "c2_interface",
        "orchestrator",
        "mission_manager",
        "planner",
        "fleet_manager",
        "edge_supervisor",
        "autonomy_sim",
        "rosbridge",
    }
    assert len(atlas["workflow"]["steps"]) == 15
    assert {
        "stateful_rest_target",
        "planner_singleton",
        "legacy_empty_task_sentinel",
    } <= {
        gap["id"] for gap in atlas["contract_gaps"]
    }
    planner_step = next(step for step in atlas["workflow"]["steps"] if step["id"] == "plan")
    assert planner_step["output"]["success"]["planner_state"] == 2
    assert planner_step["output"]["failure"] == {"planner_state": 4, "cached_paths": {}}

    for interaction in atlas["interactions"]:
        assert interaction["source"] in component_ids
        assert interaction["target"] in component_ids
        evidence_paths = " ".join(ref["path"] for ref in interaction["source_refs"])
        assert "/centralized_coordination/test/" not in evidence_paths
        assert "/planner/test/" not in evidence_paths
        assert all(ref["resolved"] for ref in interaction["source_refs"])

    for step in atlas["workflow"]["steps"]:
        assert set(step["actor_ids"]) <= component_ids
        assert set(step["interaction_ids"]) <= interaction_ids
        assert all(ref["resolved"] for ref in step["source_refs"])


def test_init_approve_start_posts_to_legacy_rest() -> None:
    rest = FakeRestClient()
    client = TestClient(create_app(ROOT, rest_client=rest, rosbridge_client=FakeRosbridgeClient()))
    mission = {
        "mission_id": "not-a-legacy-uuid",
        "behavior": 0,
        "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
        "transit": {"optimalization": {"road_usage": 0.4}, "desired_speed": 4},
        "objective": {"geometry": {"geometry_type": "Point", "coordinates": [4.39218, 50.84417]}},
    }

    init_payload = client.post("/api/missions/init", json=mission).json()
    mission_id = init_payload["mission_id"]
    client.app.state.missions[mission_id].update(
        {"status": 1, "status_name": "PLANNED", "status_source": "mission_feedback"}
    )
    approved = client.post(f"/api/missions/{mission_id}/approve", json={}).json()
    started = client.post(f"/api/missions/{mission_id}/start", json={}).json()

    assert rest.initialized[0]["mission_id"] == mission_id
    assert rest.initialized[0]["objective"]["geometries"][0]["geometry"]["coordinates"] == [4.39218, 50.84417]
    assert rest.initialized[0]["transit"]["optimization"] == {"road_usage": 0.4}
    assert rest.initialized[0]["transit"]["desired_vehicle_constraints"]["max_speed"] == 4
    assert rest.status_changes == [MissionRequest.APPROVE, MissionRequest.START]
    assert approved["status"] == 4
    assert approved["status_name"] == "ACCEPTED"
    assert started["status"] == 5
    assert started["status_name"] == "STARTED"


def test_status_route_rejects_unknown_mission_without_posting_to_legacy_rest() -> None:
    rest = FakeRestClient()
    client = TestClient(
        create_app(ROOT, rest_client=rest, rosbridge_client=FakeRosbridgeClient())
    )

    response = client.post(
        "/api/missions/77734909-0b4b-4ee4-b0d2-e5bb5893dd14/approve",
        json={},
    )

    assert response.status_code == 404
    assert rest.status_changes == []


def test_status_route_cannot_command_a_different_last_initialized_mission() -> None:
    rest = FakeRestClient()
    client = TestClient(
        create_app(ROOT, rest_client=rest, rosbridge_client=FakeRosbridgeClient())
    )

    def mission(mission_id: str) -> dict[str, Any]:
        return {
            "mission_id": mission_id,
            "behavior": 0,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "objective": {
                "geometry": {
                    "geometry_type": "Point",
                    "coordinates": [4.39218, 50.84417],
                }
            },
        }

    first_id = "77734909-0b4b-4ee4-b0d2-e5bb5893dd14"
    second_id = "dcfa9605-1387-47e4-b4c8-f2ddcc4868a2"
    assert client.post("/api/missions/init", json=mission(first_id)).status_code == 200
    assert client.post("/api/missions/init", json=mission(second_id)).status_code == 200

    rejected = client.post(f"/api/missions/{first_id}/approve", json={})

    assert rejected.status_code == 409
    assert "not the backend status-command target" in rejected.json()["detail"]
    client.app.state.missions[second_id].update(
        {"status": 1, "status_name": "PLANNED", "status_source": "mission_feedback"}
    )
    accepted = client.post(f"/api/missions/{second_id}/approve", json={})
    assert accepted.status_code == 200
    assert rest.status_changes == [MissionRequest.APPROVE]


def test_get_mission_runtime_state_returns_adapter_record() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "behavior": 0,
        "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
        "objective": {"geometry": {"geometry_type": "Point", "coordinates": [4.39218, 50.84417]}},
    }

    initialized = client.post("/api/missions/init", json=mission).json()
    runtime_state = client.get(f"/api/missions/{initialized['mission_id']}").json()

    assert runtime_state["mission_id"] == initialized["mission_id"]
    assert runtime_state["status_name"] == "NONE"
    assert runtime_state["config"]["objective"]["geometries"][0]["geometry"]["coordinates"] == [4.39218, 50.84417]


def test_init_inlines_user_created_feature_ids_before_legacy_rest(tmp_path: Path) -> None:
    user_features = tmp_path / "data" / "runtime" / "user_features_rma.geojson"
    user_features.parent.mkdir(parents=True)
    user_features.write_text(
        """{
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "id": "runtime-objective",
              "properties": {"feature_id": "runtime-objective", "feature_type": "objective", "source": "user"},
              "geometry": {"type": "Point", "coordinates": [4.39218, 50.84417]}
            },
            {
              "type": "Feature",
              "id": "runtime-geofence",
              "properties": {"feature_id": "runtime-geofence", "feature_type": "geofence", "source": "user"},
              "geometry": {"type": "Polygon", "coordinates": [[[4.39,50.84],[4.40,50.84],[4.40,50.85],[4.39,50.84]]]}
            },
            {
              "type": "Feature",
              "id": "runtime-road",
              "properties": {"feature_id": "runtime-road", "feature_type": "road", "source": "user"},
              "geometry": {"type": "LineString", "coordinates": [[4.3922,50.8442],[4.3928,50.8450]]}
            }
          ]
        }""",
        encoding="utf-8",
    )
    rest = FakeRestClient()
    client = TestClient(create_app(tmp_path, rest_client=rest, rosbridge_client=FakeRosbridgeClient()))

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "behavior": 0,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "start": {"geometry": {"feature_id": "runtime-objective"}},
            "transit": {"geofence": {"feature_id": "runtime-geofence"}, "roads": [{"feature_id": "runtime-road"}]},
            "objective": {"geometries": [{"feature_id": "runtime-objective"}, {"feature_id": "runtime-road"}]},
        },
    )

    assert response.status_code == 200
    assert rest.initialized[0]["objective"]["geometries"] == [
        {"geometry": {"geometry_type": "Point", "coordinates": [4.39218, 50.84417]}},
        {"geometry": {"geometry_type": "LineString", "coordinates": [[4.3922, 50.8442], [4.3928, 50.8450]]}},
    ]
    assert rest.initialized[0]["transit"]["geofence"] == {
        "geometry": {
            "geometry_type": "Polygon",
            "coordinates": [[4.39, 50.84], [4.40, 50.84], [4.40, 50.85], [4.39, 50.84]],
        }
    }
    assert rest.initialized[0]["transit"]["roads"] == [
        {
            "geometry": {
                "geometry_type": "LineString",
                "coordinates": [[4.3922, 50.8442], [4.3928, 50.8450]],
            }
        }
    ]
    assert rest.initialized[0]["start"]["geometry"] == {
        "geometry": {
            "geometry_type": "Point",
            "coordinates": [4.39218, 50.84417],
        }
    }
    assert response.json()["config"]["start"]["geometry"] == {
        "feature_id": "runtime-objective"
    }
    assert response.json()["config"]["transit"]["geofence"] == {"feature_id": "runtime-geofence"}
    assert response.json()["config"]["objective"]["geometries"] == [
        {"feature_id": "runtime-objective"},
        {"feature_id": "runtime-road"},
    ]
    assert response.json()["adapter_adjustments"] == [
        "translated feature references or polygon geometry for editable-backend ROS compatibility",
        "added backend-only max_speed=1 m/s because canonical transit speed is optional",
    ]


def test_init_translates_canonical_line_of_sight_and_road_geometry_for_backend_ros(
    tmp_path: Path,
) -> None:
    rest = FakeRestClient()
    client = TestClient(
        create_app(
            tmp_path,
            rest_client=rest,
            rosbridge_client=FakeRosbridgeClient(),
        )
    )
    ring = [
        [4.391, 50.845],
        [4.394, 50.845],
        [4.394, 50.846],
        [4.391, 50.845],
    ]
    road = [[4.3922, 50.8442], [4.3928, 50.8450]]

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "dcfa9605-1387-47e4-b4c8-f2ddcc4868a2",
            "behavior": 0,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "transit": {
                "roads": [
                    {
                        "geometry": {
                            "geometry_type": "LineString",
                            "coordinates": road,
                        }
                    }
                ]
            },
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Point",
                            "coordinates": [4.39218, 50.84417],
                        }
                    }
                ],
                "line_of_sight": {
                    "geometry": {
                        "geometry_type": "Polygon",
                        "coordinates": [ring],
                    }
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["config"]["objective"]["line_of_sight"] == {
        "geometry": {
            "geometry_type": "Polygon",
            "coordinates": [ring],
        }
    }
    assert response.json()["config"]["transit"]["roads"] == [
        {
            "geometry": {
                "geometry_type": "LineString",
                "coordinates": road,
            }
        }
    ]
    assert rest.initialized[0]["objective"]["line_of_sight"] == {
        "geometry": {
            "geometry_type": "Polygon",
            "coordinates": ring,
        }
    }
    assert rest.initialized[0]["transit"]["roads"] == [
        {
            "geometry": {
                "geometry_type": "LineString",
                "coordinates": road,
            }
        }
    ]


def test_init_wraps_legacy_start_geometry_for_live_c2_msgs_parser(
    tmp_path: Path,
) -> None:
    rest = FakeRestClient()
    client = TestClient(
        create_app(
            tmp_path,
            rest_client=rest,
            rosbridge_client=FakeRosbridgeClient(),
        )
    )
    start_geometry = {
        "geometry_type": "Point",
        "coordinates": [4.39218, 50.84417],
    }

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "75861ed0-730b-41d0-a52a-63c6eb1ffd36",
            "behavior": 0,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "start": {"geometry": start_geometry},
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Point",
                            "coordinates": [4.394, 50.846],
                        }
                    }
                ]
            },
        },
    )

    assert response.status_code == 200
    expected = {"geometry": {"geometry": start_geometry}}
    assert response.json()["config"]["start"] == expected
    assert rest.initialized[0]["start"] == expected


def test_init_inlines_coverage_polygon_for_legacy_ros_without_losing_feature_id(tmp_path: Path) -> None:
    feature_path = tmp_path / "data" / "runtime" / "user_features_rma.geojson"
    feature_path.parent.mkdir(parents=True)
    feature_path.write_text(
        """{
          "type": "FeatureCollection",
          "features": [{
            "type": "Feature",
            "id": "runtime-parade",
            "properties": {"feature_id": "runtime-parade", "feature_type": "geofence", "source": "user"},
            "geometry": {
              "type": "Polygon",
              "coordinates": [[[4.391,50.845],[4.394,50.845],[4.394,50.846],[4.391,50.845]]]
            }
          }]
        }""",
        encoding="utf-8",
    )
    rest = FakeRestClient()
    client = TestClient(create_app(tmp_path, rest_client=rest, rosbridge_client=FakeRosbridgeClient()))

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "e742fc22-48c6-499d-96aa-cf054d650506",
            "behavior": 1,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "transit": {"geofence": {"feature_id": "runtime-parade"}},
            "objective": {
                "geometries": [{"feature_id": "runtime-parade"}],
                "maximize_coverage": True,
                "maximum_coverage_distances": [6],
            },
        },
    )

    assert response.status_code == 200
    legacy_polygon = {
        "geometry_type": "Polygon",
        "coordinates": [[4.391, 50.845], [4.394, 50.845], [4.394, 50.846], [4.391, 50.845]],
    }
    assert rest.initialized[0]["transit"]["geofence"] == {"geometry": legacy_polygon}
    assert rest.initialized[0]["objective"]["geometries"] == [{"geometry": legacy_polygon}]
    assert response.json()["config"]["transit"]["geofence"] == {"feature_id": "runtime-parade"}
    assert response.json()["config"]["objective"]["geometries"] == [{"feature_id": "runtime-parade"}]


def test_init_flattens_canonical_inline_polygon_only_at_backend_ros_boundary(
    tmp_path: Path,
) -> None:
    rest = FakeRestClient()
    client = TestClient(
        create_app(
            tmp_path,
            rest_client=rest,
            rosbridge_client=FakeRosbridgeClient(),
        )
    )
    ring = [
        [4.391, 50.845],
        [4.394, 50.845],
        [4.394, 50.846],
        [4.391, 50.845],
    ]

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "e742fc22-48c6-499d-96aa-cf054d650506",
            "behavior": 1,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "objective": {
                "geometries": [
                    {
                        "geometry": {
                            "geometry_type": "Polygon",
                            "coordinates": [ring],
                        }
                    }
                ],
                "maximize_coverage": True,
                "maximum_coverage_distances": [6],
            },
        },
    )

    assert response.status_code == 200
    assert rest.initialized[0]["objective"]["geometries"][0]["geometry"] == {
        "geometry_type": "Polygon",
        "coordinates": ring,
    }
    assert response.json()["config"]["objective"]["geometries"][0]["geometry"] == {
        "geometry_type": "Polygon",
        "coordinates": [ring],
    }
    assert response.json()["adapter_adjustments"] == [
        "translated feature references or polygon geometry for editable-backend ROS compatibility",
        "added backend-only max_speed=1 m/s because canonical transit speed is optional",
    ]


def test_init_rejects_runtime_polygon_holes_the_legacy_contract_cannot_represent(tmp_path: Path) -> None:
    feature_path = tmp_path / "data" / "runtime" / "user_features_rma.geojson"
    feature_path.parent.mkdir(parents=True)
    feature_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "polygon-with-hole",
                        "properties": {"feature_id": "polygon-with-hole", "feature_type": "geofence", "source": "user"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [[4.39, 50.84], [4.40, 50.84], [4.40, 50.85], [4.39, 50.84]],
                                [[4.395, 50.845], [4.396, 50.845], [4.395, 50.845]],
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    rest = FakeRestClient()
    client = TestClient(create_app(tmp_path, rest_client=rest, rosbridge_client=FakeRosbridgeClient()))

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "e742fc22-48c6-499d-96aa-cf054d650506",
            "behavior": 1,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "transit": {"geofence": {"feature_id": "polygon-with-hole"}},
            "objective": {
                "geometries": [{"feature_id": "polygon-with-hole"}],
                "maximize_coverage": True,
                "maximum_coverage_distances": [6],
            },
        },
    )

    assert response.status_code == 422
    assert "interior rings" in response.json()["detail"]
    assert rest.initialized == []


def test_init_preserves_full_road_usage_point_objective_coordinates(tmp_path: Path) -> None:
    osm_cache = tmp_path / "data" / "runtime" / "osm_roads_rma.geojson"
    osm_cache.parent.mkdir(parents=True)
    osm_cache.write_text(
        """{
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "properties": {"feature_type": "osm_road"},
              "geometry": {"type": "LineString", "coordinates": [[4.0, 50.0], [4.001, 50.0]]}
            }
          ]
        }""",
        encoding="utf-8",
    )
    rest = FakeRestClient()
    client = TestClient(create_app(tmp_path, rest_client=rest, rosbridge_client=FakeRosbridgeClient()))

    response = client.post(
        "/api/missions/init",
        json={
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "behavior": 0,
            "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
            "transit": {"optimization": {"road_usage": 1}},
            "objective": {"geometry": {"geometry_type": "Point", "coordinates": [4.0009, 50.0]}},
        },
    ).json()

    assert rest.initialized[0]["objective"]["geometries"][0]["geometry"]["coordinates"] == [4.0009, 50.0]
    assert response["config"]["objective"]["geometries"][0]["geometry"]["coordinates"] == [4.0009, 50.0]
    assert response["adapter_adjustments"] == [
        "added backend-only max_speed=1 m/s because canonical transit speed is optional"
    ]


def test_planning_diagnostics_includes_scenario_matrix(tmp_path: Path) -> None:
    agent_id = "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
    osm_cache = tmp_path / "data" / "runtime" / "osm_roads_rma.geojson"
    osm_cache.parent.mkdir(parents=True)
    osm_cache.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": "road-a",
                        "properties": {"feature_id": "road-a", "feature_type": "osm_road", "highway": "residential", "name": "Test Road"},
                        "geometry": {"type": "LineString", "coordinates": [[4.0, 50.0], [4.001, 50.0], [4.002, 50.0]]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    app = create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient())
    app.state.agent_updates[agent_id] = {"current_location": [4.0, 50.0]}
    client = TestClient(app)

    initialized = client.post(
        "/api/missions/init",
        json={
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "behavior": 0,
            "vehicles": [agent_id],
            "objective": {"geometry": {"geometry_type": "Point", "coordinates": [4.002, 50.0]}},
        },
    ).json()

    diagnostics = client.get(f"/api/planning/diagnostics?mission_id={initialized['mission_id']}").json()
    scenario_analysis = diagnostics["scenario_analysis"]
    ok_scenarios = [scenario for scenario in scenario_analysis["scenarios"] if scenario["status"] == "ok"]

    assert scenario_analysis["status"] == "ok"
    assert scenario_analysis["inputs"]["start"] == [4.0, 50.0]
    assert ok_scenarios
    assert "planner_like_cost_m" in ok_scenarios[0]["metrics"]
    assert "total_cost_with_endpoint_penalty_m" in ok_scenarios[0]["metrics"]


def test_inline_user_feature_refs_leaves_mapdb_feature_ids_alone(tmp_path: Path) -> None:
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "behavior": 0,
        "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
        "objective": {"geometries": [{"feature_id": "mapdb-known-by-planner"}]},
    }

    assert _inline_user_feature_refs(mission, tmp_path)["objective"]["geometries"] == [{"feature_id": "mapdb-known-by-planner"}]


def test_real_legacy_rest_payload_uses_old_optimization_spelling() -> None:
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "transit": {"optimization": {"road_usage": 1, "energy": 0.8}},
    }

    legacy = to_legacy_mission_config(mission)

    assert legacy["transit"]["optimalization"] == {"road_usage": 1, "energy": 0.8}
    assert "optimization" not in legacy["transit"]
    assert mission["transit"]["optimization"] == {"road_usage": 1, "energy": 0.8}


def test_real_legacy_rest_payload_uses_old_coverage_width_spelling() -> None:
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "objective": {"maximum_coverage_distances": [6.0]},
    }

    legacy = to_legacy_mission_config(mission)

    assert legacy["objective"]["maximize_coverage_distances"] == [6.0]
    assert "maximum_coverage_distances" not in legacy["objective"]
    assert mission["objective"]["maximum_coverage_distances"] == [6.0]


def test_ros_feedback_normalizes_legacy_agent_ids_and_planned_paths() -> None:
    feedback = _normalize_mission_feedback(
        {
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "mission_feedback": (
                '{"mission_id":"77734909-0b4b-4ee4-b0d2-e5bb5893dd14","status":1,"issue":0,'
                '"tasks":[{"vehicle_id":"f9992bb3_9871_451f_90a0_9207eb9fe6c5",'
                '"waypoints":[{"coordinates":[50.844317,4.392588]},{"coordinates":[50.844171,4.39167]}]}]}'
            ),
        }
    )
    edge = _normalize_edge_feedback(
        {
            "agent_id": "f9992bb3_9871_451f_90a0_9207eb9fe6c5",
            "state": 1,
            "tasks": [{"task_id": "task-1", "task_state": 3}],
        }
    )

    assert edge["agent_id"] == "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
    assert edge["status_name"] == "ACTIVE"
    assert edge["tasks"][0]["task_state_name"] == "COMPLETED"
    assert feedback["status_name"] == "PLANNED"
    assert feedback["status_source"] == "mission_feedback"
    assert feedback["issue_name"] == "NONE"
    assert feedback["path_status"] == "received"
    assert feedback["planned_paths"]["f9992bb3-9871-451f-90a0-9207eb9fe6c5"] == [
        [4.392588, 50.844317],
        [4.39167, 50.844171],
    ]

    empty_feedback = _normalize_mission_feedback(
        {
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "mission_feedback": '{"mission_id":"77734909-0b4b-4ee4-b0d2-e5bb5893dd14","status":1,"tasks":{}}',
        }
    )
    assert empty_feedback["status_name"] == "PLANNED"
    assert empty_feedback["path_status"] == "missing"
    assert empty_feedback["planned_paths"] == {}


def test_legacy_mongo_feedback_normalizes_planned_paths() -> None:
    state = _mission_state_from_legacy_feedback(
        {
            "_id": "feedback-doc",
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "status": 1,
            "issue": 40,
            "tasks": [
                {
                    "vehicle_id": "f9992bb3_9871_451f_90a0_9207eb9fe6c5",
                    "waypoints": [
                        {"coordinates": [50.844317, 4.392588]},
                        {"coordinates": [50.84534, 4.392684]},
                    ],
                }
            ],
        }
    )

    assert state["status_name"] == "PLANNED"
    assert state["issue_name"] == "PLANNING_FAILED_NO_SOLUTION_FOUND"
    assert state["path_status"] == "received"
    assert state["planned_paths"]["f9992bb3-9871-451f-90a0-9207eb9fe6c5"] == [
        [4.392588, 50.844317],
        [4.392684, 50.84534],
    ]
    assert state["raw"]["source"] == "legacy_mongo"


def test_legacy_planning_document_extracts_lonlat_paths() -> None:
    paths = _planned_paths_from_planning_doc(
        {
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "tasks": {
                "f9992bb3-9871-451f-90a0-9207eb9fe6c5": {
                    "objectives": [
                        {"primitives": [{"parameters": {"coordinates": [4.392095, 50.843586]}}]},
                        {"primitives": [{"parameters": {"coordinates": [4.392685, 50.845341]}}]},
                    ]
                }
            },
        }
    )

    assert paths == {
        "f9992bb3-9871-451f-90a0-9207eb9fe6c5": [
            [4.392095, 50.843586],
            [4.392685, 50.845341],
        ]
    }


def test_planner_ready_state_does_not_promote_mission_status_without_feedback() -> None:
    updates = _mission_updates_from_planner_state(
        {
            "state": {
                "planners": [
                    {"mission_id": "7ae5fb5a-bf4f-431f-8d39-5f750ac288f6", "state": 2},
                    {"mission_id": "9f74e8da-bce7-4101-b555-e36687beb8df", "state": 1},
                    {"mission_id": "11111111-2222-4333-8444-555555555555", "state": 4},
                    {"mission_id": "22222222-3333-4444-8555-666666666666", "state": 3},
                ]
            }
        }
    )

    assert updates[0]["mission_id"] == "7ae5fb5a-bf4f-431f-8d39-5f750ac288f6"
    assert updates[0]["planner_state_name"] == "READY"
    assert updates[0]["planner_status"] == "planned"
    assert "status_name" not in updates[0]
    assert updates[1]["planner_state_name"] == "PLANNING"
    assert "status_name" not in updates[1]
    assert updates[2]["planner_state_name"] == "FAILED"
    assert updates[2]["planner_status"] == "failed"
    assert "status_name" not in updates[2]
    assert updates[3]["planner_state_name"] == "DISCONNECTED"
    assert updates[3]["planner_status"] == "failed"
