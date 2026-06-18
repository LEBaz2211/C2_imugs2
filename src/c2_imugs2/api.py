from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .domain import MissionRequest, MissionStatus
from .legacy_map import delete_user_geojson_feature, feature_collection_to_map_features, load_legacy_geojson_map, load_osm_roads_overlay, save_user_geojson_feature
from .legacy_rest import LegacyRestClient
from .mission_config import MissionValidationError, load_and_validate_mission
from .repositories import read_json
from .rosbridge import RosbridgeClient


LEGACY_AGENT_ID = "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
REPO_ROOT = Path(os.environ.get("C2_IMUGS2_REPO_ROOT", Path(__file__).resolve().parents[2]))


def create_app(
    repo_root: Path = REPO_ROOT,
    rest_client: LegacyRestClient | None = None,
    rosbridge_client: RosbridgeClient | None = None,
) -> FastAPI:
    app = FastAPI(title="C2 iMUGS2 UI Adapter API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.repo_root = repo_root
    app.state.rest_client = rest_client or LegacyRestClient(os.environ.get("C2_IMUGS2_LEGACY_REST_URL", "http://localhost:5001/mission_control"))
    app.state.rosbridge_client = rosbridge_client or RosbridgeClient(os.environ.get("C2_IMUGS2_ROSBRIDGE_URL", "ws://localhost:9090"))
    app.state.mongodb_url = os.environ.get("C2_IMUGS2_MONGODB_URL", os.environ.get("MONGODB_CONNSTRING", "mongodb://127.0.0.1:27017"))
    app.state.missions = {}
    app.state.agent_updates = {}
    app.state.planner_state = {}

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        legacy = app.state.rest_client.health()
        ros = await app.state.rosbridge_client.diagnostics()
        checks = [
            {"id": "legacy_rest", "status": "ok" if legacy.ok else "error", "message": legacy.body or f"status {legacy.status_code}"},
            *ros["checks"],
        ]
        return {
            "status": "ok" if all(check["status"] == "ok" for check in checks) else "degraded",
            "legacy_rest": {"ok": legacy.ok, "status_code": legacy.status_code, "body": legacy.body},
            "rosbridge_url": app.state.rosbridge_client.url,
            "checks": checks,
        }

    @app.get("/api/diagnostics")
    async def diagnostics() -> dict[str, Any]:
        legacy = app.state.rest_client.health()
        ros = await app.state.rosbridge_client.diagnostics()
        checks = [
            {"id": "legacy_rest", "status": "ok" if legacy.ok else "error", "message": legacy.body or f"status {legacy.status_code}"},
            *ros["checks"],
        ]
        return {
            "containers": {},
            "legacy_rest": {"ok": legacy.ok, "status_code": legacy.status_code},
            "ros": ros,
            "checks": checks,
        }

    @app.get("/api/legacy/trace")
    async def legacy_trace() -> dict[str, Any]:
        legacy = app.state.rest_client.health()
        ros = await app.state.rosbridge_client.diagnostics()
        nodes = set(ros.get("nodes", []))
        topics = set(ros.get("topics", []))
        steps = [
            _trace_step("adapter.api", True, "FastAPI adapter is running"),
            _trace_step("legacy.rest", legacy.ok, "old REST bridge reachable", legacy.body or f"status {legacy.status_code}"),
            _trace_step("rosbridge.websocket", any(check["id"] == "rosbridge.websocket" and check["status"] == "ok" for check in ros["checks"]), "rosbridge reachable"),
            _trace_step("c2.node", "/c2_node" in nodes, "/c2_node visible", "missing /c2_node"),
            _trace_step("c2.interface", "/c2_interface_node" in nodes, "/c2_interface_node visible", "missing /c2_interface_node"),
            _trace_step("orchestrator", "/orchestrator_node" in nodes, "/orchestrator_node visible", "missing /orchestrator_node"),
            _trace_step("fleet.manager", "/fleet_manager_node" in nodes, "/fleet_manager_node visible", "missing /fleet_manager_node"),
            _trace_step("planner", "/planner_node" in nodes, "/planner_node visible", "missing /planner_node"),
            _trace_step("edge.agent", "/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5" in nodes, "edge agent visible", "missing edge agent"),
            _trace_step("autonomy.sim", "/autonomy_test_node_Themis_Fr" in nodes, "autonomy sim visible", "missing autonomy sim"),
            _trace_step("mission.init.topic", "/multi_robot/mission_init_request" in topics, "mission init topic visible", "missing /multi_robot/mission_init_request"),
            _trace_step("mission.feedback.topic", "/multi_robot/mission_feedback" in topics, "mission feedback topic visible", "missing /multi_robot/mission_feedback"),
            _trace_step("edge.feedback.topic", "/multi_robot/edge/feedback" in topics, "edge feedback topic visible", "missing /multi_robot/edge/feedback"),
            _trace_step("planner.state.topic", "/multi_robot/planner/state" in topics, "planner state topic visible", "missing /multi_robot/planner/state"),
        ]
        return {
            "steps": steps,
            "legacy_rest": {"ok": legacy.ok, "status_code": legacy.status_code, "body": legacy.body},
            "ros": ros,
            "missions": list(app.state.missions.values()),
            "agent_updates": list(app.state.agent_updates.values()),
            "planner_state": app.state.planner_state,
        }

    @app.post("/api/testing/reset-legacy-runtime")
    async def reset_legacy_runtime() -> dict[str, Any]:
        result = _reset_legacy_runtime_database(app.state.mongodb_url)
        app.state.missions.clear()
        app.state.agent_updates.clear()
        app.state.planner_state = {}
        return result

    @app.get("/api/map/features")
    async def map_features(map: str = Query(default="rma")) -> dict[str, Any]:
        try:
            return load_legacy_geojson_map(app.state.repo_root, map)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/map/features")
    async def create_map_feature(feature: dict[str, Any], map: str = Query(default="rma")) -> dict[str, Any]:
        try:
            saved = save_user_geojson_feature(app.state.repo_root, map, feature)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        collection = load_legacy_geojson_map(app.state.repo_root, map)
        return {
            "feature": saved,
            "map_feature": feature_collection_to_map_features({"type": "FeatureCollection", "features": [saved]})[0],
            "geojson": collection,
            "map_features": feature_collection_to_map_features(collection),
        }

    @app.delete("/api/map/features/{feature_id}")
    async def delete_map_feature(feature_id: str, map: str = Query(default="rma")) -> dict[str, Any]:
        deleted = delete_user_geojson_feature(app.state.repo_root, map, feature_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Only user-created runtime features can be deleted")
        collection = load_legacy_geojson_map(app.state.repo_root, map)
        return {
            "deleted_feature_id": feature_id,
            "geojson": collection,
            "map_features": feature_collection_to_map_features(collection),
        }

    @app.get("/api/map/osm-roads")
    async def osm_roads(map: str = Query(default="rma")) -> dict[str, Any]:
        return load_osm_roads_overlay(app.state.repo_root, map)

    @app.get("/api/agents")
    async def agents() -> dict[str, Any]:
        legacy_agent = {
            "agent_id": LEGACY_AGENT_ID,
            "name": "Themis Fr",
            "vehicle_type": "UGV",
            "status": "available",
            "current_location": [4.392588, 50.844317],
            "constraints": {"max_speed": 4.5},
            "capabilities": ["waypoint_navigation", "coverage"],
        }
        agent_update = app.state.agent_updates.get(LEGACY_AGENT_ID, {})
        if agent_update.get("current_location"):
            legacy_agent["current_location"] = agent_update["current_location"]
        if agent_update.get("status"):
            legacy_agent["status"] = str(agent_update["status"])
        return {"agents": [legacy_agent]}

    @app.get("/api/mission-examples")
    async def mission_examples() -> dict[str, Any]:
        examples_dir = app.state.repo_root / "fixtures" / "mission_examples"
        examples = []
        for path in sorted(examples_dir.glob("*.json")):
            config = read_json(path)
            examples.append(
                {
                    "id": path.stem,
                    "name": config.get("name", path.stem),
                    "behavior": config.get("behavior"),
                    "vehicles": config.get("vehicles", []),
                    "config": config,
                }
            )
        return {"examples": examples}

    @app.post("/api/missions/init")
    async def init_mission(mission_config: dict[str, Any]) -> dict[str, Any]:
        try:
            normalized = load_and_validate_mission(mission_config)
        except MissionValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        normalized["mission_id"] = _legacy_uuid(normalized.get("mission_id"))
        response = app.state.rest_client.initialize_mission(normalized)
        app.state.missions[normalized["mission_id"]] = {
            "mission_id": normalized["mission_id"],
            "status": 0,
            "status_name": _mission_status_name(0),
            "config": normalized,
            "legacy_rest": response.__dict__,
        }
        if not response.ok:
            raise HTTPException(status_code=502, detail={"message": "legacy REST mission init failed", "legacy_rest": response.__dict__})
        return app.state.missions[normalized["mission_id"]]

    @app.post("/api/missions/{mission_id}/approve")
    async def approve_mission(mission_id: str) -> dict[str, Any]:
        return _change_mission_status(app, mission_id, MissionRequest.APPROVE, 4)

    @app.post("/api/missions/{mission_id}/start")
    async def start_mission(mission_id: str) -> dict[str, Any]:
        return _change_mission_status(app, mission_id, MissionRequest.START, 5)

    @app.get("/api/events")
    async def events() -> StreamingResponse:
        async def stream():
            queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()

            async def read_rosbridge() -> None:
                while True:
                    async for message in app.state.rosbridge_client.topic_messages():
                        event = _normalize_rosbridge_event(message)
                        if event is not None:
                            await queue.put(event)
                    await asyncio.sleep(1)

            task = asyncio.create_task(read_rosbridge())
            try:
                while True:
                    try:
                        event_name, payload = await asyncio.wait_for(queue.get(), timeout=3)
                        if event_name == "agent.updated":
                            app.state.agent_updates[payload["agent_id"]] = payload
                        if event_name == "planner.updated":
                            app.state.planner_state = payload
                        if event_name == "mission.updated":
                            mission_id = payload.get("mission_id")
                            if mission_id:
                                app.state.missions.setdefault(mission_id, {"mission_id": mission_id, "config": {}}).update(payload)
                            planned_paths = payload.get("planned_paths")
                            if planned_paths:
                                planner_payload = {"mission_id": mission_id, "paths": planned_paths, "source": "mission_feedback"}
                                app.state.planner_state = planner_payload
                                yield _sse("planner.updated", planner_payload)
                        yield _sse(event_name, payload)
                    except asyncio.TimeoutError:
                        diagnostics_payload = await diagnostics()
                        yield _sse("diagnostics.updated", diagnostics_payload)
                        for agent in app.state.agent_updates.values():
                            yield _sse("agent.updated", agent)
                        if app.state.planner_state:
                            yield _sse("planner.updated", app.state.planner_state)
                        for mission in app.state.missions.values():
                            yield _sse("mission.updated", mission)
            finally:
                task.cancel()

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/runtime/bootstrap")
    async def runtime_bootstrap(map: str = Query(default="rma")) -> dict[str, Any]:
        collection = load_legacy_geojson_map(app.state.repo_root, map)
        return {
            "agents": (await agents())["agents"],
            "map_features": feature_collection_to_map_features(collection),
            "geojson": collection,
        }

    return app


app = create_app()


def _change_mission_status(app: FastAPI, mission_id: str, request: MissionRequest, status: int) -> dict[str, Any]:
    response = app.state.rest_client.change_status(request)
    mission = app.state.missions.setdefault(mission_id, {"mission_id": mission_id, "config": {}, "feedback": {}})
    mission["status"] = status
    mission["status_name"] = _mission_status_name(status)
    mission["requested_status"] = int(request)
    mission["requested_status_name"] = request.name
    mission["legacy_rest"] = response.__dict__
    if not response.ok:
        raise HTTPException(status_code=502, detail={"message": "legacy REST status change failed", "legacy_rest": response.__dict__})
    return mission


def _mission_status_name(status: Any) -> str:
    try:
        return MissionStatus(int(status)).name
    except (TypeError, ValueError):
        return "UNKNOWN"


def _legacy_uuid(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return str(uuid.uuid4())


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _trace_step(step_id: str, ok: bool, ok_message: str, fail_message: str | None = None) -> dict[str, str]:
    return {"id": step_id, "status": "ok" if ok else "error", "message": ok_message if ok else (fail_message or ok_message)}


def _normalize_rosbridge_event(message: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    topic = message.get("topic")
    msg = dict(message.get("msg") or {})
    if topic == "rosbridge.error":
        return "diagnostics.updated", {"checks": [{"id": "rosbridge.websocket", "status": "error", "message": str(msg.get("error", "unknown error"))}], "ros": {}}
    if topic == "/multi_robot/edge/feedback":
        return "agent.updated", _normalize_edge_feedback(msg)
    if topic == "/multi_robot/mission_feedback":
        return "mission.updated", _normalize_mission_feedback(msg)
    if topic == "/multi_robot/planner/state":
        return "planner.updated", _normalize_planner_state(msg)
    return None


def _normalize_edge_feedback(msg: dict[str, Any]) -> dict[str, Any]:
    agent_id = _normalize_uuidish_id(msg.get("agent_id") or LEGACY_AGENT_ID)
    odometry = msg.get("odometry") if isinstance(msg.get("odometry"), dict) else {}
    position = (((odometry.get("pose") or {}).get("pose") or {}).get("position") or {})
    location = None
    if isinstance(position, dict) and isinstance(position.get("x"), int | float) and isinstance(position.get("y"), int | float):
        location = [float(position["x"]), float(position["y"])]
    return {
        "agent_id": agent_id,
        "status": str(msg.get("state", "unknown")),
        "current_location": location,
        "tasks": msg.get("tasks", []),
        "raw": msg,
    }


def _normalize_mission_feedback(msg: dict[str, Any]) -> dict[str, Any]:
    feedback_raw = msg.get("mission_feedback")
    feedback = _json_or_raw(feedback_raw)
    mission_id = _mission_id_from_ros_msg(msg) or (_feedback_value(feedback, "mission_id", "MissionId") if isinstance(feedback, dict) else None)
    status = _feedback_value(feedback, "status", "Status") if isinstance(feedback, dict) else None
    requested_status = _feedback_value(feedback, "requested_status", "RequestedStatus") if isinstance(feedback, dict) else None
    planned_paths = _planned_paths_from_feedback(feedback) if isinstance(feedback, dict) else {}
    return {
        "mission_id": _normalize_uuidish_id(mission_id) if mission_id else "",
        "status": status,
        "status_name": _mission_status_name(status),
        "requested_status": requested_status,
        "planned_paths": planned_paths,
        "feedback": feedback,
        "raw": msg,
    }


def _feedback_value(feedback: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in feedback:
            return feedback[key]
    return None


def _normalize_planner_state(msg: dict[str, Any]) -> dict[str, Any]:
    data = _json_or_raw(msg.get("data"))
    return {"state": data, "raw": msg}


def _planned_paths_from_feedback(feedback: dict[str, Any]) -> dict[str, list[list[float]]]:
    tasks = _feedback_value(feedback, "tasks", "Tasks")
    if not isinstance(tasks, list):
        return {}

    planned_paths: dict[str, list[list[float]]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        agent_id = _normalize_uuidish_id(_feedback_value(task, "vehicle_id", "VehicleId", "agent_id", "AgentId"))
        waypoints = _feedback_value(task, "waypoints", "Waypoints")
        if not agent_id or not isinstance(waypoints, list):
            continue

        path = []
        for waypoint in waypoints:
            if not isinstance(waypoint, dict):
                continue
            coordinate = _feedback_value(waypoint, "coordinates", "Coordinates")
            lonlat = _legacy_feedback_coordinate_to_lonlat(coordinate)
            if lonlat:
                path.append(lonlat)
        if path:
            planned_paths[agent_id] = path
    return planned_paths


def _legacy_feedback_coordinate_to_lonlat(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) >= 2 and _is_number(value[0]) and _is_number(value[1]):
        lat = float(value[0])
        lng = float(value[1])
        return [lng, lat]
    if isinstance(value, dict):
        lat = _feedback_value(value, "lat", "Lat")
        lng = _feedback_value(value, "lng", "Lng", "lon", "Lon")
        if _is_number(lat) and _is_number(lng):
            return [float(lng), float(lat)]
    return None


def _normalize_uuidish_id(value: Any) -> str:
    raw = str(value or "")
    candidate = raw.removeprefix("agent_").replace("_", "-")
    try:
        return str(uuid.UUID(candidate))
    except ValueError:
        return raw


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _json_or_raw(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _mission_id_from_ros_msg(msg: dict[str, Any]) -> str:
    value = msg.get("mission_id")
    if isinstance(value, str):
        return _normalize_uuidish_id(value)
    if isinstance(value, dict) and isinstance(value.get("uuid"), list):
        try:
            return str(uuid.UUID(bytes=bytes(value["uuid"])))
        except (ValueError, TypeError):
            return ""
    return ""


def _reset_legacy_runtime_database(mongodb_url: str) -> dict[str, Any]:
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="pymongo is not installed in the API environment") from exc

    collections = ("MissionFeedback", "Planning", "MissionConfig", "Logs")
    deleted: dict[str, int] = {}
    try:
        with MongoClient(mongodb_url, serverSelectionTimeoutMS=2000) as client:
            client.admin.command("ping")
            runtime = client["RuntimeDB"]
            for collection_name in collections:
                deleted[collection_name] = runtime[collection_name].delete_many({}).deleted_count
    except PyMongoError as exc:
        raise HTTPException(status_code=502, detail=f"legacy Mongo cleanup failed: {exc}") from exc

    return {
        "status": "ok",
        "database": "RuntimeDB",
        "deleted": deleted,
        "preserved": ["RuntimeDB.ConnectedVehicles", "VehicleDB.Vehicles"],
        "restart_required": True,
        "message": "Cleared test mission runtime records. Restart legacy ROS containers to remove already-running mission nodes.",
    }


def main() -> None:
    uvicorn.run("c2_imugs2.api:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
