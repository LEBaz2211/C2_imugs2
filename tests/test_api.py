from pathlib import Path
import json
from typing import Any

from fastapi.testclient import TestClient

import c2_imugs2.legacy_map as legacy_map
from c2_imugs2.api import (
    create_app,
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


def test_health_and_diagnostics_shape() -> None:
    client = TestClient(create_app(ROOT, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    health = client.get("/api/health").json()
    diagnostics = client.get("/api/diagnostics").json()

    assert health["status"] == "ok"
    assert health["legacy_rest"]["ok"] is True
    assert diagnostics["legacy_rest"]["ok"] is True
    assert diagnostics["checks"][0]["id"] == "legacy_rest"
    assert diagnostics["ros"]["nodes"]


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


def test_import_osm_roads_persists_as_user_road_features(tmp_path: Path, monkeypatch: Any) -> None:
    legacy_map_dir = tmp_path / "legacy_ros" / "config" / "data" / "map" / "rma" / "free_polygons"
    legacy_map_dir.mkdir(parents=True)
    (legacy_map_dir / "workspace.geojson").write_text(
        '{"type":"Feature","properties":{"feature_id":"legacy-workspace","feature_type":"workspace","name":"base"},'
        '"geometry":{"type":"Polygon","coordinates":[[[4.0,50.0],[4.1,50.0],[4.1,50.1],[4.0,50.0]]]}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        legacy_map,
        "_query_overpass_roads",
        lambda bbox: {
            "elements": [
                {
                    "type": "way",
                    "id": 123,
                    "tags": {"highway": "service", "name": "Test Service Road"},
                    "geometry": [{"lon": 4.05, "lat": 50.05}, {"lon": 4.06, "lat": 50.06}],
                }
            ]
        },
    )
    client = TestClient(create_app(tmp_path, rest_client=FakeRestClient(), rosbridge_client=FakeRosbridgeClient()))

    imported = client.post("/api/map/osm-roads/import?map=rma", json={"bbox": [4.04, 50.04, 4.07, 50.07]}).json()
    reloaded = client.get("/api/map/features?map=rma").json()

    assert imported["imported_count"] == 1
    assert imported["features"][0]["properties"]["feature_type"] == "road"
    assert imported["features"][0]["properties"]["source"] == "user"
    assert imported["features"][0]["properties"]["import_source"] == "openstreetmap-overpass"
    assert any(item["properties"].get("feature_id") == "osm-way-123" for item in reloaded["features"])


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
    assert "mission_lifecycle" in scenario_ids
    assert "unsupported_no_planning" in scenario_ids
    assert graph["source_digest"]


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
        "geometry_type": "Polygon",
        "coordinates": [[[4.39, 50.84], [4.40, 50.84], [4.40, 50.85], [4.39, 50.84]]],
    }
    assert rest.initialized[0]["transit"]["roads"] == [
        {"geometry_type": "LineString", "coordinates": [[4.3922, 50.8442], [4.3928, 50.8450]]}
    ]


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
    assert response["adapter_adjustments"] == []


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


def test_inline_user_feature_refs_leaves_legacy_feature_ids_alone(tmp_path: Path) -> None:
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "behavior": 0,
        "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
        "objective": {"geometries": [{"feature_id": "legacy-known-by-planner"}]},
    }

    assert _inline_user_feature_refs(mission, tmp_path)["objective"]["geometries"] == [{"feature_id": "legacy-known-by-planner"}]


def test_real_legacy_rest_payload_uses_old_optimization_spelling() -> None:
    mission = {
        "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
        "transit": {"optimization": {"road_usage": 1, "energy": 0.8}},
    }

    legacy = to_legacy_mission_config(mission)

    assert legacy["transit"]["optimalization"] == {"road_usage": 1, "energy": 0.8}
    assert "optimization" not in legacy["transit"]
    assert mission["transit"]["optimization"] == {"road_usage": 1, "energy": 0.8}


def test_ros_feedback_normalizes_legacy_agent_ids_and_planned_paths() -> None:
    feedback = _normalize_mission_feedback(
        {
            "mission_id": "77734909-0b4b-4ee4-b0d2-e5bb5893dd14",
            "mission_feedback": (
                '{"mission_id":"77734909-0b4b-4ee4-b0d2-e5bb5893dd14","status":1,'
                '"tasks":[{"vehicle_id":"f9992bb3_9871_451f_90a0_9207eb9fe6c5",'
                '"waypoints":[{"coordinates":[50.844317,4.392588]},{"coordinates":[50.844171,4.39167]}]}]}'
            ),
        }
    )
    edge = _normalize_edge_feedback({"agent_id": "f9992bb3_9871_451f_90a0_9207eb9fe6c5"})

    assert edge["agent_id"] == "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
    assert feedback["status_name"] == "PLANNED"
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
