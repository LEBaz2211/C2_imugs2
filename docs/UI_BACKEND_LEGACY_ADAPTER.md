# UI to Legacy ROS Adapter

This phase keeps the old ROS stack as the execution engine and places a stable FastAPI adapter between the browser UI and legacy ROS.

Compatibility rules and project priorities are in [PROJECT_PLANNING.md](../PROJECT_PLANNING.md).

## Runtime Shape

```text
Browser UI (Vite/React/Leaflet)
  -> http://localhost:8000/api/*
Backend Adapter (FastAPI)
  -> http://localhost:5001/mission_control for mission commands
  -> ws://localhost:9090 for ROS diagnostics and live read-side events
  -> legacy_ros/config/data/map/<map> for GeoJSON overlays
Legacy ROS Docker stack
  -> c2_node, c2_interface_node, orchestrator_node, fleet_manager_node, planner_node, edge agent, autonomy sim
```

The UI does not construct ROS messages and does not connect to rosbridge directly.

## Backend API

```text
GET    /api/health
GET    /api/diagnostics
GET    /api/planning/diagnostics
GET    /api/contracts
GET    /api/legacy/trace
GET    /api/runtime/bootstrap?map=rma
GET    /api/map/features?map=rma
POST   /api/map/features?map=rma
PUT    /api/map/features/{feature_id}?map=rma
DELETE /api/map/features/{feature_id}?map=rma
GET    /api/map/osm-roads?map=rma
GET    /api/agents
GET    /api/mission-examples
POST   /api/missions/init
GET    /api/missions/{mission_id}
POST   /api/missions/{mission_id}/approve
POST   /api/missions/{mission_id}/start
DELETE /api/missions/{mission_id}
GET    /api/events
```

`/api/missions/init` validates and normalizes old mission config aliases, ensures the legacy mission id is UUID-shaped, then posts `action=initialize` to the old REST bridge.

`/api/missions/{id}/approve` and `/start` post `action=change_status` to the old REST bridge using the legacy numeric mission request values.

The UI command buttons mean:

```text
Apply   local UI only: parse/normalize the mission JSON and update the map/task preview
Init    backend posts action=initialize to old REST, which publishes /multi_robot/mission_init_request
Approve backend posts action=change_status with legacy requested_state=1
Start   backend posts action=change_status with legacy requested_state=2
```

The app opens without a selected mission. Mission JSON comes from an explicit example selection, drawing on the map, pasting JSON, or the local drafting helper.

Deleting a mission removes it from adapter/UI runtime only. It does not delete old ROS or MongoDB records.

`/api/events` is SSE. It emits:

```text
diagnostics.updated
mission.updated
agent.updated
planner.updated
```

The event source reads rosbridge topics:

```text
/multi_robot/mission_feedback
/multi_robot/edge/feedback
/multi_robot/planner/state
```

Planner `READY` is only node readiness. The adapter reports a usable path only after mission feedback contains non-empty waypoint tasks.

## Legacy Smoke Test

After starting `docker-compose.legacy-ros.yml`, run:

```bash
./scripts/check_legacy_ros_stack.sh
```

The script checks required containers, required ROS nodes, required ROS topics, old REST reachability, and rosbridge WebSocket reachability.
