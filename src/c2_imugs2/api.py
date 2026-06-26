from __future__ import annotations

import asyncio
from copy import deepcopy
import heapq
import json
import math
import os
import uuid
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .contracts import build_contract_graph
from .domain import MissionRequest, MissionStatus
from .legacy_map import delete_user_geojson_feature, feature_collection_to_map_features, import_osm_roads_as_user_features, load_legacy_geojson_map, load_osm_roads_overlay, load_user_geojson_map, save_user_geojson_feature, update_user_geojson_feature
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
    app.state.forgotten_missions = _load_forgotten_missions(repo_root)

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
        _backfill_missions_from_legacy_mongo(app)
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
            "missions": _visible_missions(app.state.missions, app.state.forgotten_missions),
            "planner_state": app.state.planner_state,
        }

    @app.get("/api/planning/diagnostics")
    async def planning_diagnostics(mission_id: str | None = Query(default=None)) -> dict[str, Any]:
        selected_id = mission_id or _latest_adapter_mission_id(app.state.missions)
        if selected_id:
            _backfill_mission_from_legacy_mongo(app, selected_id)
        return _planning_diagnostics_payload(app, selected_id)

    @app.get("/api/contracts")
    async def contracts(include_runtime: bool = Query(default=True)) -> dict[str, Any]:
        runtime = {}
        if include_runtime:
            runtime = await app.state.rosbridge_client.diagnostics()
        graph = build_contract_graph(app.state.repo_root, runtime=runtime)
        graph["adapter_runtime"] = {
            "missions": _visible_missions(app.state.missions, app.state.forgotten_missions),
            "agent_updates": list(app.state.agent_updates.values()),
            "planner_state": app.state.planner_state,
        }
        return graph

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
            "missions": _visible_missions(app.state.missions, app.state.forgotten_missions),
            "agent_updates": list(app.state.agent_updates.values()),
            "planner_state": app.state.planner_state,
        }

    @app.post("/api/testing/reset-legacy-runtime")
    async def reset_legacy_runtime() -> dict[str, Any]:
        result = _reset_legacy_runtime_database(app.state.mongodb_url)
        app.state.missions.clear()
        app.state.agent_updates.clear()
        app.state.planner_state = {}
        app.state.forgotten_missions.clear()
        _save_forgotten_missions(app.state.repo_root, app.state.forgotten_missions)
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

    @app.put("/api/map/features/{feature_id}")
    async def update_map_feature(feature_id: str, feature: dict[str, Any], map: str = Query(default="rma")) -> dict[str, Any]:
        try:
            updated = update_user_geojson_feature(app.state.repo_root, map, feature_id, feature)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not updated:
            raise HTTPException(status_code=404, detail="Only user-created runtime features can be edited")
        collection = load_legacy_geojson_map(app.state.repo_root, map)
        return {
            "feature": updated,
            "map_feature": feature_collection_to_map_features({"type": "FeatureCollection", "features": [updated]})[0],
            "geojson": collection,
            "map_features": feature_collection_to_map_features(collection),
        }

    @app.get("/api/map/osm-roads")
    async def osm_roads(map: str = Query(default="rma")) -> dict[str, Any]:
        return load_osm_roads_overlay(app.state.repo_root, map)

    @app.post("/api/map/osm-roads/import")
    async def import_osm_roads(payload: dict[str, Any], map: str = Query(default="rma")) -> dict[str, Any]:
        bbox = payload.get("bbox")
        if not isinstance(bbox, list | tuple) or len(bbox) != 4:
            raise HTTPException(status_code=422, detail="bbox must be [west, south, east, north]")
        try:
            return import_osm_roads_as_user_features(
                app.state.repo_root,
                map,
                (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                max_features=int(payload.get("max_features") or 80),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/agents")
    async def agents() -> dict[str, Any]:
        legacy_agent = {
            "agent_id": LEGACY_AGENT_ID,
            "name": "Themis Fr",
            "vehicle_type": "UGV",
            "status": "available",
            "current_location": [4.392588, 50.844317],
            "constraints": {"max_speed": 4.5},
            "capabilities": [],
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
        normalized = _inline_user_feature_refs(normalized, app.state.repo_root)
        normalized["mission_id"] = _legacy_uuid(normalized.get("mission_id"))
        app.state.forgotten_missions.discard(normalized["mission_id"])
        _save_forgotten_missions(app.state.repo_root, app.state.forgotten_missions)
        response = app.state.rest_client.initialize_mission(normalized)
        app.state.missions[normalized["mission_id"]] = {
            "mission_id": normalized["mission_id"],
            "status": 0,
            "status_name": _mission_status_name(0),
            "command_phase": "init_acknowledged",
            "planner_status": "waiting_for_feedback",
            "initialized_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "config": normalized,
            "adapter_adjustments": [],
            "legacy_rest": response.__dict__,
        }
        if not response.ok:
            raise HTTPException(status_code=502, detail={"message": "legacy REST mission init failed", "legacy_rest": response.__dict__})
        return app.state.missions[normalized["mission_id"]]

    @app.get("/api/missions/{mission_id}")
    async def mission_runtime_state(mission_id: str) -> dict[str, Any]:
        _backfill_mission_from_legacy_mongo(app, mission_id)
        mission = app.state.missions.get(mission_id)
        if not mission or mission_id in app.state.forgotten_missions:
            raise HTTPException(status_code=404, detail="mission is not in adapter runtime")
        return mission

    @app.post("/api/missions/{mission_id}/approve")
    async def approve_mission(mission_id: str) -> dict[str, Any]:
        return _change_mission_status(app, mission_id, MissionRequest.APPROVE, 4)

    @app.post("/api/missions/{mission_id}/start")
    async def start_mission(mission_id: str) -> dict[str, Any]:
        return _change_mission_status(app, mission_id, MissionRequest.START, 5)

    @app.delete("/api/missions/{mission_id}")
    async def forget_mission(mission_id: str) -> dict[str, Any]:
        app.state.forgotten_missions.add(mission_id)
        _save_forgotten_missions(app.state.repo_root, app.state.forgotten_missions)
        removed = app.state.missions.pop(mission_id, None)
        planner_state = app.state.planner_state
        if isinstance(planner_state, dict) and planner_state.get("mission_id") == mission_id:
            app.state.planner_state = {}
        return {
            "mission_id": mission_id,
            "removed": bool(removed),
            "message": "Removed mission from adapter runtime only. Legacy ROS and MongoDB are unchanged.",
        }

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
                            for planner_mission in _mission_updates_from_planner_state(payload):
                                mission_id = planner_mission["mission_id"]
                                if mission_id in app.state.forgotten_missions:
                                    continue
                                mission = app.state.missions.setdefault(mission_id, {"mission_id": mission_id, "config": {}})
                                mission.update(planner_mission)
                                mission["updated_at"] = _utc_now_iso()
                                yield _sse("mission.updated", mission)
                        if event_name == "mission.updated":
                            mission_id = payload.get("mission_id")
                            if mission_id in app.state.forgotten_missions:
                                continue
                            if mission_id:
                                mission = app.state.missions.setdefault(mission_id, {"mission_id": mission_id, "config": {}})
                                mission.update(payload)
                                mission["planner_status"] = _planner_status_from_mission_payload(payload)
                                mission["updated_at"] = _utc_now_iso()
                            planned_paths = payload.get("planned_paths")
                            if planned_paths:
                                planner_payload = {
                                    "mission_id": mission_id,
                                    "paths": planned_paths,
                                    "source": "mission_feedback",
                                    "received_at": _utc_now_iso(),
                                    "path_summary": _path_summary(planned_paths),
                                }
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
                            if mission.get("mission_id") in app.state.forgotten_missions:
                                continue
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

def _change_mission_status(app: FastAPI, mission_id: str, request: MissionRequest, status: int) -> dict[str, Any]:
    response = app.state.rest_client.change_status(request)
    mission = app.state.missions.setdefault(mission_id, {"mission_id": mission_id, "config": {}, "feedback": {}})
    mission["status"] = status
    mission["status_name"] = _mission_status_name(status)
    mission["requested_status"] = int(request)
    mission["requested_status_name"] = request.name
    mission["command_phase"] = request.name.lower()
    mission["updated_at"] = _utc_now_iso()
    mission["legacy_rest"] = response.__dict__
    if not response.ok:
        raise HTTPException(status_code=502, detail={"message": "legacy REST status change failed", "legacy_rest": response.__dict__})
    return mission


def _latest_adapter_mission_id(missions: dict[str, dict[str, Any]]) -> str | None:
    if not missions:
        return None
    return next(reversed(missions))


def _backfill_missions_from_legacy_mongo(app: FastAPI) -> None:
    for mission_id in list(app.state.missions.keys()):
        if mission_id in app.state.forgotten_missions:
            continue
        _backfill_mission_from_legacy_mongo(app, mission_id)


def _backfill_mission_from_legacy_mongo(app: FastAPI, mission_id: str) -> dict[str, Any] | None:
    feedback_doc = _latest_mongo_document(app.state.mongodb_url, "MissionFeedback", mission_id)
    if not feedback_doc:
        return None

    update = _mission_state_from_legacy_feedback(feedback_doc)
    if not update.get("mission_id"):
        update["mission_id"] = mission_id
    mission = app.state.missions.setdefault(mission_id, {"mission_id": mission_id, "config": {}})
    if _should_preserve_local_command_status(mission, update):
        status_fields = {"status", "status_name", "requested_status"}
        mission.update({key: value for key, value in update.items() if key not in status_fields})
    else:
        mission.update(update)
    mission["planner_status"] = _planner_status_from_mission_payload(update)
    mission["updated_at"] = _utc_now_iso()

    planned_paths = update.get("planned_paths")
    if planned_paths:
        app.state.planner_state = {
            "mission_id": mission_id,
            "paths": planned_paths,
            "source": "legacy_mongo_backfill",
            "received_at": _utc_now_iso(),
            "path_summary": _path_summary(planned_paths),
        }
    return mission


def _should_preserve_local_command_status(current: dict[str, Any], feedback_update: dict[str, Any]) -> bool:
    """Avoid downgrading optimistic approve/start state with an older feedback row."""
    current_status = _int_or_none(current.get("status"))
    feedback_status = _int_or_none(feedback_update.get("status"))
    requested_status = _int_or_none(current.get("requested_status"))
    if current_status is None or feedback_status is None:
        return False
    if current_status in (4, 5, 6, 8, 9, 10) and feedback_status in (0, 1, 2) and (requested_status or 0) >= int(MissionRequest.APPROVE):
        return True
    return False


def _mission_state_from_legacy_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    feedback = _json_safe(feedback)
    mission_id = _feedback_value(feedback, "mission_id", "MissionId")
    status = _feedback_value(feedback, "status", "Status")
    requested_status = _feedback_value(feedback, "requested_status", "RequestedStatus")
    planned_paths = _planned_paths_from_feedback(feedback)
    path_status = "received" if planned_paths else ("missing" if status in (1, 2, "1", "2") else "none")
    return {
        "mission_id": _normalize_uuidish_id(mission_id) if mission_id else "",
        "status": status,
        "status_name": _mission_status_name(status),
        "requested_status": requested_status,
        "planned_paths": planned_paths,
        "path_status": path_status,
        "feedback": feedback,
        "raw": {"source": "legacy_mongo", "collection": "MissionFeedback", "document_id": str(feedback.get("_id", ""))},
    }


def _planning_diagnostics_payload(app: FastAPI, mission_id: str | None) -> dict[str, Any]:
    if not mission_id:
        return {
            "mission_id": None,
            "checks": [_trace_step("planning.mission", False, "mission selected", "No adapter mission is selected or initialized.")],
            "adapter": {},
            "legacy_mongo": {},
        }

    mission = app.state.missions.get(mission_id, {})
    feedback_doc = _latest_mongo_document(app.state.mongodb_url, "MissionFeedback", mission_id)
    planning_doc = _latest_mongo_document(app.state.mongodb_url, "Planning", mission_id)
    config_doc = _latest_mongo_document(app.state.mongodb_url, "MissionConfig", mission_id)
    logs = _recent_mongo_documents(app.state.mongodb_url, "Logs", mission_id, limit=12)

    feedback_paths = _planned_paths_from_feedback(feedback_doc or {})
    planning_paths = _planned_paths_from_planning_doc(planning_doc or {})
    adapter_paths = mission.get("planned_paths") if isinstance(mission.get("planned_paths"), dict) else {}
    planner_state = app.state.planner_state if isinstance(app.state.planner_state, dict) else {}
    planner_state_for_mission = planner_state.get("mission_id") == mission_id or planner_state.get("mission_id") is None

    checks = [
        _trace_step("adapter.mission", bool(mission), "adapter has mission runtime state", "adapter has no runtime state for this mission"),
        _trace_step("legacy.config", bool(config_doc), "legacy Mongo has MissionConfig", "legacy Mongo has no MissionConfig for this mission"),
        _trace_step("legacy.planning", bool(planning_doc), "legacy Mongo has Planning output", "legacy Mongo has no Planning output for this mission"),
        _trace_step("legacy.feedback", bool(feedback_doc), "legacy Mongo has MissionFeedback", "legacy Mongo has no MissionFeedback for this mission"),
        _trace_step("legacy.feedback.paths", bool(feedback_paths), "MissionFeedback contains waypoint paths", "MissionFeedback has no waypoint paths"),
        _trace_step("adapter.paths", bool(adapter_paths), "adapter has planned paths", "adapter does not yet have planned paths"),
    ]

    summary = {
        "adapter_status": mission.get("status_name") or _mission_status_name(mission.get("status")),
        "adapter_path_summary": _path_summary(adapter_paths) if adapter_paths else None,
        "feedback_status": _mission_status_name(feedback_doc.get("status")) if feedback_doc else None,
        "feedback_path_summary": _path_summary(feedback_paths) if feedback_paths else None,
        "planning_path_summary": _path_summary(planning_paths) if planning_paths else None,
        "planner_state_matches_mission": planner_state_for_mission,
    }
    interpretation = _planning_interpretation(summary, bool(planning_doc), bool(feedback_doc))
    scenario_analysis = _planning_scenario_analysis(app, mission, config_doc or {}, feedback_paths or planning_paths or adapter_paths)

    return {
        "mission_id": mission_id,
        "checks": checks,
        "summary": summary,
        "interpretation": interpretation,
        "scenario_analysis": scenario_analysis,
        "adapter": {
            "mission": mission,
            "planner_state": app.state.planner_state,
        },
        "legacy_mongo": {
            "mission_config": _json_safe(config_doc),
            "planning": _json_safe(planning_doc),
            "mission_feedback": _json_safe(feedback_doc),
            "logs": _json_safe(logs),
        },
    }


def _planning_interpretation(summary: dict[str, Any], has_planning: bool, has_feedback: bool) -> list[str]:
    notes = []
    if has_feedback and summary.get("feedback_path_summary") and not summary.get("adapter_path_summary"):
        notes.append("Legacy has PLANNED feedback with waypoints, but the adapter had not cached paths before this diagnostic read. Mongo backfill should refresh the UI state.")
    if has_planning and not has_feedback:
        notes.append("Planner returned a plan, but mission feedback has not been recorded; inspect the mission manager logs.")
    if summary.get("adapter_path_summary"):
        notes.append("Adapter has waypoint paths for this mission; if the map still shows a dashed line, the UI is showing local preview instead of planner paths.")
    if not notes:
        notes.append("No single break point identified yet; compare the raw adapter and legacy Mongo payloads below.")
    return notes


DRIVE_HIGHWAY_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street", "service", "road"}
NON_DRIVE_HIGHWAY_CLASSES = {"footway", "path", "pedestrian", "steps", "cycleway", "bridleway", "corridor"}


def _planning_scenario_analysis(
    app: FastAPI,
    mission: dict[str, Any],
    config_doc: dict[str, Any],
    actual_paths: dict[str, list[list[float]]],
) -> dict[str, Any]:
    config = mission.get("config") if isinstance(mission.get("config"), dict) else {}
    if not config:
        config = config_doc if isinstance(config_doc, dict) else {}

    map_name = str(config.get("map") or "rma")
    agent_id = _scenario_agent_id(config, actual_paths)
    start = _scenario_start_point(app, agent_id, actual_paths)
    objective = _scenario_objective_point(config, app.state.repo_root, map_name)
    if not start or not objective:
        return {
            "status": "missing_inputs",
            "inputs": {"agent_id": agent_id, "start": start, "objective": objective, "map": map_name},
            "scenarios": [],
            "notes": ["Scenario analysis needs a point objective and either live agent feedback or a planned path start."],
        }

    scenarios = []
    actual_path = _actual_path_for_agent(actual_paths, agent_id)
    if actual_path:
        scenarios.append(_actual_path_scenario(actual_path, start, objective))

    scenario_defs = [
        {
            "id": "nearest_osm_drive_no_service",
            "label": "Nearest OSM Drive, No Service",
            "road_filter": "osm_drive_no_service",
            "candidate_count": 1,
            "endpoint_penalty": 0.0,
        },
        {
            "id": "candidate_osm_drive_no_service_1x",
            "label": "Candidate OSM Drive, Endpoint 1x",
            "road_filter": "osm_drive_no_service",
            "candidate_count": 10,
            "endpoint_penalty": 1.0,
        },
        {
            "id": "candidate_osm_drive_no_service_4x",
            "label": "Candidate OSM Drive, Endpoint 4x",
            "road_filter": "osm_drive_no_service",
            "candidate_count": 10,
            "endpoint_penalty": 4.0,
        },
        {
            "id": "nearest_osm_drive_with_service",
            "label": "Nearest OSM Drive + Service",
            "road_filter": "osm_drive_with_service",
            "candidate_count": 1,
            "endpoint_penalty": 0.0,
        },
        {
            "id": "candidate_osm_all",
            "label": "Candidate All OSM Ways",
            "road_filter": "osm_all",
            "candidate_count": 10,
            "endpoint_penalty": 1.0,
        },
        {
            "id": "candidate_mixed_legacy",
            "label": "Candidate OSM + Legacy Lines",
            "road_filter": "mixed_drive_no_service",
            "candidate_count": 10,
            "endpoint_penalty": 1.0,
        },
    ]
    graph_cache: dict[str, dict[str, Any]] = {}
    graph_summaries = {}
    for scenario_def in scenario_defs:
        road_filter = scenario_def["road_filter"]
        graph = graph_cache.get(road_filter)
        if graph is None:
            graph = _build_diagnostic_graph(app.state.repo_root, map_name, road_filter)
            graph_cache[road_filter] = graph
            graph_summaries[road_filter] = graph["summary"]
        scenarios.append(_run_graph_scenario(graph, scenario_def, start, objective))

    return {
        "status": "ok",
        "inputs": {
            "agent_id": agent_id,
            "start": start,
            "objective": objective,
            "map": map_name,
            "coordinate_order": "[lon, lat]",
        },
        "model": {
            "kind": "adapter_diagnostic_graph",
            "important_limit": "This does not command ROS. It isolates node snapping, source filters, and endpoint-cost assumptions using the adapter road overlays.",
            "legacy_planner_issue_to_watch": "The old planner chooses nearest graph nodes first, runs A*, then prepends/appends exact start/objective points. Those endpoint legs are not part of A* route selection.",
        },
        "graph_summaries": graph_summaries,
        "scenarios": scenarios,
    }


def _scenario_agent_id(config: dict[str, Any], actual_paths: dict[str, list[list[float]]]) -> str:
    vehicles = config.get("vehicles") if isinstance(config.get("vehicles"), list) else []
    if vehicles:
        return _normalize_uuidish_id(vehicles[0])
    if actual_paths:
        return next(iter(actual_paths.keys()))
    return LEGACY_AGENT_ID


def _scenario_start_point(app: FastAPI, agent_id: str, actual_paths: dict[str, list[list[float]]]) -> list[float] | None:
    normalized_agent_id = _normalize_uuidish_id(agent_id)
    agent_update = app.state.agent_updates.get(normalized_agent_id) or app.state.agent_updates.get(agent_id)
    if isinstance(agent_update, dict):
        point = _lonlat_point(agent_update.get("current_location"))
        if point:
            return point
    path = _actual_path_for_agent(actual_paths, normalized_agent_id)
    if path:
        return path[0]
    return [4.392588, 50.844317]


def _actual_path_for_agent(actual_paths: dict[str, list[list[float]]], agent_id: str) -> list[list[float]]:
    if not actual_paths:
        return []
    normalized_agent_id = _normalize_uuidish_id(agent_id)
    return actual_paths.get(normalized_agent_id) or actual_paths.get(agent_id) or next(iter(actual_paths.values()))


def _scenario_objective_point(config: dict[str, Any], repo_root: Path, map_name: str) -> list[float] | None:
    objective = config.get("objective") if isinstance(config.get("objective"), dict) else {}
    direct_geometry = objective.get("geometry") if isinstance(objective.get("geometry"), dict) else None
    if direct_geometry:
        point = _point_from_geometry(direct_geometry)
        if point:
            return point
    direct_feature_id = str(objective.get("feature_id") or "")
    if direct_feature_id:
        point = _feature_point_by_id(repo_root, map_name, direct_feature_id)
        if point:
            return point

    geometries = objective.get("geometries") if isinstance(objective.get("geometries"), list) else []
    for geometry_ref in geometries:
        if not isinstance(geometry_ref, dict):
            continue
        geometry = geometry_ref.get("geometry") if isinstance(geometry_ref.get("geometry"), dict) else geometry_ref
        point = _point_from_geometry(geometry)
        if point:
            return point
        feature_id = str(geometry_ref.get("feature_id") or "")
        if feature_id:
            point = _feature_point_by_id(repo_root, map_name, feature_id)
            if point:
                return point
    return None


def _point_from_geometry(geometry: Any) -> list[float] | None:
    if not isinstance(geometry, dict):
        return None
    if str(geometry.get("geometry_type") or geometry.get("type")) != "Point":
        return None
    return _lonlat_point(geometry.get("coordinates"))


def _feature_point_by_id(repo_root: Path, map_name: str, feature_id: str) -> list[float] | None:
    try:
        collection = load_legacy_geojson_map(repo_root, map_name)
    except FileNotFoundError:
        return None
    for feature in collection.get("features", []):
        properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        if str(properties.get("feature_id") or feature.get("id") or "") != feature_id:
            continue
        geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
        if geometry.get("type") == "Point":
            return _lonlat_point(geometry.get("coordinates"))
    return None


def _actual_path_scenario(path: list[list[float]], start: list[float], objective: list[float]) -> dict[str, Any]:
    route = [_lonlat_point(point) for point in path]
    route = [point for point in route if point]
    length = _route_length_m(route)
    start_gap = _haversine_m(start, route[0]) if route else None
    end_gap = _haversine_m(route[-1], objective) if route else None
    return {
        "id": "actual_legacy_output",
        "label": "Actual Legacy Output",
        "status": "ok" if route else "missing",
        "parameters": {"source": "legacy_mongo_or_adapter", "note": "Already planned route returned by the old stack."},
        "metrics": {
            "point_count": len(route),
            "visible_length_m": round(length, 2),
            "start_gap_to_current_start_m": round(start_gap, 2) if start_gap is not None else None,
            "end_gap_to_objective_m": round(end_gap, 2) if end_gap is not None else None,
        },
        "route": route,
        "notes": ["Use this to compare what legacy actually emitted against the diagnostic scenario routes."],
    }


def _build_diagnostic_graph(repo_root: Path, map_name: str, road_filter: str) -> dict[str, Any]:
    nodes: dict[str, list[float]] = {}
    adjacency: dict[str, list[dict[str, Any]]] = {}
    edge_count = 0
    source_counts: dict[str, int] = {}
    highway_counts: dict[str, int] = {}

    collections = []
    try:
        collections.append(("osm", load_osm_roads_overlay(repo_root, map_name)))
    except Exception:
        collections.append(("osm", {"type": "FeatureCollection", "features": []}))
    try:
        collections.append(("legacy", load_legacy_geojson_map(repo_root, map_name)))
    except FileNotFoundError:
        collections.append(("legacy", {"type": "FeatureCollection", "features": []}))

    for source, collection in collections:
        for feature in collection.get("features", []):
            if not _diagnostic_feature_allowed(feature, source, road_filter):
                continue
            geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
            if geometry.get("type") != "LineString":
                continue
            coordinates = [_lonlat_point(point) for point in geometry.get("coordinates", [])]
            coordinates = [point for point in coordinates if point]
            if len(coordinates) < 2:
                continue
            properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
            for first, second in zip(coordinates, coordinates[1:]):
                first_key = _node_key(first)
                second_key = _node_key(second)
                if first_key == second_key:
                    continue
                nodes[first_key] = first
                nodes[second_key] = second
                length_m = _haversine_m(first, second)
                edge = {
                    "to": second_key,
                    "length_m": length_m,
                    "source": source,
                    "feature_id": str(properties.get("feature_id") or feature.get("id") or ""),
                    "name": str(properties.get("name") or ""),
                    "highway": str(properties.get("highway") or properties.get("feature_type") or ""),
                }
                reverse = dict(edge)
                reverse["to"] = first_key
                adjacency.setdefault(first_key, []).append(edge)
                adjacency.setdefault(second_key, []).append(reverse)
                edge_count += 1
            source_counts[source] = source_counts.get(source, 0) + 1
            highway = str(properties.get("highway") or properties.get("feature_type") or "unknown")
            highway_counts[highway] = highway_counts.get(highway, 0) + 1

    return {
        "nodes": nodes,
        "adjacency": adjacency,
        "summary": {
            "road_filter": road_filter,
            "node_count": len(nodes),
            "edge_count": edge_count,
            "feature_counts_by_source": source_counts,
            "feature_counts_by_highway": highway_counts,
        },
    }


def _diagnostic_feature_allowed(feature: Any, source: str, road_filter: str) -> bool:
    if not isinstance(feature, dict):
        return False
    properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
    if geometry.get("type") != "LineString":
        return False
    feature_type = str(properties.get("feature_type") or "")
    highway = str(properties.get("highway") or "").lower()

    if source == "legacy":
        return road_filter == "mixed_drive_no_service" and feature_type == "road"
    if feature_type != "osm_road":
        return False
    if road_filter == "osm_all":
        return bool(highway)
    if highway in NON_DRIVE_HIGHWAY_CLASSES:
        return False
    if highway not in DRIVE_HIGHWAY_CLASSES:
        return False
    if road_filter in {"osm_drive_no_service", "mixed_drive_no_service"} and highway == "service":
        return False
    return road_filter in {"osm_drive_no_service", "osm_drive_with_service", "mixed_drive_no_service"}


def _run_graph_scenario(graph: dict[str, Any], scenario_def: dict[str, Any], start: list[float], objective: list[float]) -> dict[str, Any]:
    nodes = graph["nodes"]
    if not nodes:
        return {
            "id": scenario_def["id"],
            "label": scenario_def["label"],
            "status": "no_graph",
            "parameters": scenario_def,
            "metrics": {},
            "route": [],
            "notes": ["No line features matched this scenario filter."],
        }

    candidate_count = int(scenario_def["candidate_count"])
    endpoint_penalty = float(scenario_def["endpoint_penalty"])
    start_candidates = _nearest_graph_nodes(nodes, start, candidate_count)
    end_candidates = _nearest_graph_nodes(nodes, objective, candidate_count)
    best: dict[str, Any] | None = None
    evaluated = 0
    connected = 0
    for start_candidate in start_candidates:
        for end_candidate in end_candidates:
            evaluated += 1
            graph_length, node_path = _dijkstra(graph, start_candidate["node"], end_candidate["node"])
            if not node_path:
                continue
            connected += 1
            endpoint_distance = start_candidate["distance_m"] + end_candidate["distance_m"]
            total_cost = graph_length + endpoint_penalty * endpoint_distance
            if best is None or total_cost < best["total_cost_m"]:
                best = {
                    "start": start_candidate,
                    "end": end_candidate,
                    "graph_length_m": graph_length,
                    "node_path": node_path,
                    "total_cost_m": total_cost,
                    "endpoint_distance_m": endpoint_distance,
                }

    if best is None:
        nearest_start = start_candidates[0] if start_candidates else None
        nearest_end = end_candidates[0] if end_candidates else None
        return {
            "id": scenario_def["id"],
            "label": scenario_def["label"],
            "status": "no_route",
            "parameters": scenario_def,
            "metrics": {
                "candidate_pairs_evaluated": evaluated,
                "connected_candidate_pairs": connected,
                "nearest_start_snap_m": round(nearest_start["distance_m"], 2) if nearest_start else None,
                "nearest_end_snap_m": round(nearest_end["distance_m"], 2) if nearest_end else None,
            },
            "route": [],
            "notes": ["Graph nodes exist, but candidate start/end road nodes are disconnected under this scenario filter."],
        }

    route = [start, *[nodes[node] for node in best["node_path"]], objective]
    visible_length = _route_length_m(route)
    start_snap = float(best["start"]["distance_m"])
    end_snap = float(best["end"]["distance_m"])
    segments = _scenario_segments(graph, start, objective, best["node_path"], start_snap, end_snap)
    notes = []
    if start_snap > 25 or end_snap > 25:
        notes.append("Large endpoint snap: old A* route selection may ignore a visible off-road leg.")
    if endpoint_penalty == 0:
        notes.append("Endpoint snap is reported but not charged in this scenario cost, matching the legacy concern.")
    return {
        "id": scenario_def["id"],
        "label": scenario_def["label"],
        "status": "ok",
        "parameters": {
            "road_filter": scenario_def["road_filter"],
            "candidate_count": candidate_count,
            "endpoint_penalty": endpoint_penalty,
        },
        "metrics": {
            "point_count": len(route),
            "graph_length_m": round(float(best["graph_length_m"]), 2),
            "start_snap_m": round(start_snap, 2),
            "end_snap_m": round(end_snap, 2),
            "endpoint_distance_m": round(float(best["endpoint_distance_m"]), 2),
            "visible_length_m": round(visible_length, 2),
            "planner_like_cost_m": round(float(best["graph_length_m"]), 2),
            "total_cost_with_endpoint_penalty_m": round(float(best["total_cost_m"]), 2),
            "candidate_pairs_evaluated": evaluated,
            "connected_candidate_pairs": connected,
        },
        "route": route,
        "selected_nodes": {
            "start": {"coordinate": nodes[best["start"]["node"]], "distance_m": round(start_snap, 2)},
            "end": {"coordinate": nodes[best["end"]["node"]], "distance_m": round(end_snap, 2)},
        },
        "segments": segments,
        "notes": notes,
    }


def _nearest_graph_nodes(nodes: dict[str, list[float]], point: list[float], limit: int) -> list[dict[str, Any]]:
    ranked = [
        {"node": node, "coordinate": coordinate, "distance_m": _haversine_m(point, coordinate)}
        for node, coordinate in nodes.items()
    ]
    ranked.sort(key=lambda item: item["distance_m"])
    return ranked[: max(1, limit)]


def _dijkstra(graph: dict[str, Any], start_node: str, end_node: str) -> tuple[float, list[str]]:
    adjacency = graph["adjacency"]
    distances = {start_node: 0.0}
    previous: dict[str, str] = {}
    queue = [(0.0, start_node)]
    visited = set()
    while queue:
        current_distance, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        if node == end_node:
            break
        for edge in adjacency.get(node, []):
            neighbor = edge["to"]
            distance = current_distance + float(edge["length_m"])
            if distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = distance
                previous[neighbor] = node
                heapq.heappush(queue, (distance, neighbor))
    if end_node not in distances:
        return float("inf"), []

    path = [end_node]
    while path[-1] != start_node:
        path.append(previous[path[-1]])
    path.reverse()
    return distances[end_node], path


def _scenario_segments(graph: dict[str, Any], start: list[float], objective: list[float], node_path: list[str], start_snap: float, end_snap: float) -> list[dict[str, Any]]:
    nodes = graph["nodes"]
    segments = []
    if node_path:
        segments.append({"kind": "start_snap", "distance_m": round(start_snap, 2), "from": start, "to": nodes[node_path[0]]})
    for first, second in zip(node_path, node_path[1:]):
        edge = _best_graph_edge(graph, first, second)
        segments.append(
            {
                "kind": "graph",
                "distance_m": round(float(edge.get("length_m", 0)), 2),
                "from": nodes[first],
                "to": nodes[second],
                "source": edge.get("source"),
                "highway": edge.get("highway"),
                "name": edge.get("name"),
                "feature_id": edge.get("feature_id"),
            }
        )
    if node_path:
        segments.append({"kind": "end_snap", "distance_m": round(end_snap, 2), "from": nodes[node_path[-1]], "to": objective})
    return segments


def _best_graph_edge(graph: dict[str, Any], first: str, second: str) -> dict[str, Any]:
    candidates = [edge for edge in graph["adjacency"].get(first, []) if edge.get("to") == second]
    if not candidates:
        return {}
    return min(candidates, key=lambda edge: float(edge.get("length_m", float("inf"))))


def _node_key(point: list[float]) -> str:
    return f"{point[0]:.7f},{point[1]:.7f}"


def _lonlat_point(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) >= 2 and _is_number(value[0]) and _is_number(value[1]):
        return [float(value[0]), float(value[1])]
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        return _lonlat_point(value[0])
    return None


def _route_length_m(route: list[list[float]]) -> float:
    return sum(_haversine_m(first, second) for first, second in zip(route, route[1:]))


def _haversine_m(first: list[float], second: list[float]) -> float:
    lon1, lat1 = math.radians(first[0]), math.radians(first[1])
    lon2, lat2 = math.radians(second[0]), math.radians(second[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _latest_mongo_document(mongodb_url: str, collection_name: str, mission_id: str) -> dict[str, Any] | None:
    documents = _recent_mongo_documents(mongodb_url, collection_name, mission_id, limit=1)
    return documents[0] if documents else None


def _recent_mongo_documents(mongodb_url: str, collection_name: str, mission_id: str, limit: int = 5) -> list[dict[str, Any]]:
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
    except ImportError:
        return []

    try:
        with MongoClient(mongodb_url, serverSelectionTimeoutMS=1000) as client:
            runtime = client["RuntimeDB"]
            return list(runtime[collection_name].find({"mission_id": mission_id}).sort("_id", -1).limit(limit))
    except PyMongoError:
        return []


def _planned_paths_from_planning_doc(planning: dict[str, Any]) -> dict[str, list[list[float]]]:
    tasks = planning.get("tasks")
    if not isinstance(tasks, dict):
        return {}

    planned_paths: dict[str, list[list[float]]] = {}
    for agent_id, task in tasks.items():
        if not isinstance(task, dict):
            continue
        path = []
        objectives = task.get("objectives")
        if not isinstance(objectives, list):
            continue
        for objective in objectives:
            primitives = objective.get("primitives") if isinstance(objective, dict) else None
            if not isinstance(primitives, list):
                continue
            for primitive in primitives:
                parameters = primitive.get("parameters") if isinstance(primitive, dict) else None
                coordinate = parameters.get("coordinates") if isinstance(parameters, dict) else None
                if isinstance(coordinate, list) and len(coordinate) >= 2 and _is_number(coordinate[0]) and _is_number(coordinate[1]):
                    path.append([float(coordinate[0]), float(coordinate[1])])
        if path:
            planned_paths[_normalize_uuidish_id(agent_id)] = path
    return planned_paths


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    path_status = "received" if planned_paths else ("missing" if status in (1, 2, "1", "2") else "none")
    return {
        "mission_id": _normalize_uuidish_id(mission_id) if mission_id else "",
        "status": status,
        "status_name": _mission_status_name(status),
        "requested_status": requested_status,
        "planned_paths": planned_paths,
        "path_status": path_status,
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
    return {"state": data, "raw": msg, "received_at": _utc_now_iso()}


def _planner_status_from_mission_payload(payload: dict[str, Any]) -> str:
    status = payload.get("status")
    try:
        status_id = int(status)
    except (TypeError, ValueError):
        return "unknown"
    if status_id in (1, 2):
        return "planned"
    if status_id in (3, 7):
        return "failed"
    if status_id == 10:
        return "completed"
    if status_id in (4, 5, 6, 8, 9):
        return "mission_control"
    return "waiting_for_feedback"


def _mission_updates_from_planner_state(payload: dict[str, Any]) -> list[dict[str, Any]]:
    state = payload.get("state")
    if not isinstance(state, dict):
        return []
    planners = state.get("planners")
    if not isinstance(planners, list):
        return []

    updates = []
    for planner in planners:
        if not isinstance(planner, dict):
            continue
        mission_id = planner.get("mission_id")
        if not mission_id:
            continue
        planner_state = planner.get("state")
        update: dict[str, Any] = {
            "mission_id": _normalize_uuidish_id(mission_id),
            "planner_state": planner_state,
            "planner_state_name": _planner_state_name(planner_state),
            "planner_status": _planner_status_from_planner_state(planner_state),
        }
        updates.append(update)
    return updates


def _inline_user_feature_refs(mission_config: dict[str, Any], repo_root: Path, map_name: str = "rma") -> dict[str, Any]:
    """Replace runtime UI feature_id references with inline geometry for the legacy planner.

    The old planner can resolve feature_id values only from its local GeoJSON map folders.
    UI-created runtime features live in the adapter's user_features file, so they must be
    sent as literal geometry in mission_config.
    """
    normalized = deepcopy(mission_config)
    user_geometries = _user_feature_geometry_index(repo_root, map_name)
    if not user_geometries:
        return normalized

    objective = normalized.get("objective")
    if isinstance(objective, dict):
        geometries = objective.get("geometries")
        if isinstance(geometries, list):
            objective["geometries"] = [_inline_objective_geometry_ref(item, user_geometries) for item in geometries]
        for key in ("line_of_sight", "vehicle_orientation_origin"):
            value = objective.get(key)
            if isinstance(value, dict):
                objective[key] = _inline_direct_geometry_ref(value, user_geometries)

    transit = normalized.get("transit")
    if isinstance(transit, dict):
        if isinstance(transit.get("geofence"), dict):
            transit["geofence"] = _inline_direct_geometry_ref(transit["geofence"], user_geometries)
        roads = transit.get("roads")
        if isinstance(roads, list):
            transit["roads"] = [
                _inline_direct_geometry_ref(road, user_geometries) if isinstance(road, dict) else road
                for road in roads
            ]

    start = normalized.get("start")
    if isinstance(start, dict) and isinstance(start.get("geometry"), dict):
        start["geometry"] = _inline_direct_geometry_ref(start["geometry"], user_geometries)

    return normalized


def _user_feature_geometry_index(repo_root: Path, map_name: str) -> dict[str, dict[str, Any]]:
    geometries: dict[str, dict[str, Any]] = {}
    for feature in load_user_geojson_map(repo_root, map_name).get("features", []):
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        feature_id = str(properties.get("feature_id") or feature.get("id") or "")
        geometry = feature.get("geometry")
        if feature_id and isinstance(geometry, dict):
            geometries[feature_id] = {
                "geometry_type": geometry.get("type"),
                "coordinates": geometry.get("coordinates"),
            }
    return geometries


def _inline_objective_geometry_ref(value: Any, user_geometries: dict[str, dict[str, Any]]) -> Any:
    if not isinstance(value, dict):
        return value
    feature_id = str(value.get("feature_id") or "")
    if feature_id in user_geometries:
        return {"geometry": deepcopy(user_geometries[feature_id])}
    return value


def _inline_direct_geometry_ref(value: dict[str, Any], user_geometries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    feature_id = str(value.get("feature_id") or "")
    if feature_id in user_geometries:
        return deepcopy(user_geometries[feature_id])
    geometry = value.get("geometry")
    if isinstance(geometry, dict):
        nested_feature_id = str(geometry.get("feature_id") or "")
        if nested_feature_id in user_geometries:
            return deepcopy(user_geometries[nested_feature_id])
    return value


def _visible_missions(missions: dict[str, dict[str, Any]], forgotten_missions: set[str]) -> list[dict[str, Any]]:
    return [mission for mission in missions.values() if mission.get("mission_id") not in forgotten_missions]


def _forgotten_missions_path(repo_root: Path) -> Path:
    return repo_root / "data" / "runtime" / "forgotten_missions.json"


def _load_forgotten_missions(repo_root: Path) -> set[str]:
    path = _forgotten_missions_path(repo_root)
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, list):
        return set()
    return {str(mission_id) for mission_id in payload if mission_id}


def _save_forgotten_missions(repo_root: Path, mission_ids: set[str]) -> None:
    path = _forgotten_missions_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(mission_ids), indent=2), encoding="utf-8")
    except OSError:
        pass


def _planner_status_from_planner_state(planner_state: Any) -> str:
    name = _planner_state_name(planner_state)
    if name == "READY":
        return "planned"
    if name == "PLANNING":
        return "planning"
    if name == "FAILED":
        return "failed"
    return "waiting_for_feedback"


def _planner_state_name(planner_state: Any) -> str:
    try:
        state_id = int(planner_state)
    except (TypeError, ValueError):
        return "UNKNOWN"
    return {
        0: "IDLE",
        1: "PLANNING",
        2: "READY",
        3: "FAILED",
    }.get(state_id, f"UNKNOWN ({state_id})")


def _path_summary(planned_paths: dict[str, list[list[float]]]) -> dict[str, Any]:
    waypoint_counts = {agent_id: len(path) for agent_id, path in planned_paths.items()}
    return {
        "path_count": len(planned_paths),
        "waypoint_count": sum(waypoint_counts.values()),
        "waypoints_by_agent": waypoint_counts,
    }


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


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


app = create_app()


def main() -> None:
    uvicorn.run("c2_imugs2.api:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)
