# UI To Simulation Interface

This document explains how the operator UI should interact with the mission system and the robot simulation. It is intentionally written as an interface contract, not an implementation guide. The UI should remain replaceable, and the simulation backend should remain replaceable.

## Purpose

The UI is the human-facing C2 surface. It lets an operator:

- view the real-world map and known tactical features,
- draw or select mission geometry,
- edit a schema-valid `mission_config`,
- initialize, approve, start, stop, or delete missions,
- watch planner output, agent movement, autonomy status, and mission feedback,
- inspect ROS/simulation diagnostics.

The UI must not contain planning algorithms, ROS message construction logic, or direct legacy-node assumptions. It should talk to a backend API. The backend API owns validation, normalization, ROS translation, storage, and simulation integration.

## High-Level Data Flow

```text
Operator
  -> UI
  -> C2 UI Backend API
  -> MissionService / adapters
  -> ROS bridge or ROS node adapter
  -> legacy fog/planner/fleet/edge/autonomy sim
  -> ROS feedback topics
  -> C2 UI Backend API
  -> UI live state
```

The current repository has two relevant runtimes:

| Runtime | Role | Current State |
| --- | --- | --- |
| New replacement core | Mission validation, simple planning, task-plan generation | File-backed and testable |
| Legacy ROS stack | Actual copied old fog/planner/edge/autonomy nodes | Runs through `docker-compose.legacy-ros.yml` |

For now, the UI is fixture-backed. The next step is to put a small backend between the UI and both runtimes.

## Ownership Boundary

| Concern | UI | Backend API | ROS / Simulation |
| --- | --- | --- | --- |
| Render map | yes | serves map features | publishes optional map/planner state |
| Draw polygon | yes | validates and stores geometry | no |
| Edit mission JSON | yes | validates and normalizes | receives final mission JSON |
| Generate task plan preview | optional local preview | authoritative planning request | planner computes real plan |
| Start/stop mission | command button only | translates command | executes through fog/edge |
| Agent live location | renders marker | converts ROS feedback to UI state | publishes localization/feedback |
| Diagnostics | renders status | aggregates Docker/ROS/API health | node/topic/service status |
| ROS messages | no | yes, via adapter | yes |

The UI should only use JSON contracts and WebSocket/SSE events. It should not publish ROS topics directly except during throwaway debug tooling.

## UI-Facing API

These endpoints are the recommended stable UI contract.

### Mission Endpoints

| Method | Path | Request | Response | Notes |
| --- | --- | --- | --- | --- |
| `POST` | `/api/missions/init` | `mission_config` | `mission_state` | Validates, normalizes, stores, sends to planner/fog |
| `POST` | `/api/missions/{mission_id}/approve` | empty | `mission_state` | Maps to old mission status request |
| `POST` | `/api/missions/{mission_id}/start` | empty | `mission_state` | Starts dispatch/execution |
| `POST` | `/api/missions/{mission_id}/pause` | empty | `mission_state` | Optional adapter behavior |
| `POST` | `/api/missions/{mission_id}/cancel` | empty | `mission_state` | Maps to delete/cancel behavior |
| `GET` | `/api/missions/{mission_id}` | empty | `mission_state` | Current mission status and feedback |
| `GET` | `/api/missions/{mission_id}/plan` | empty | `task_plan` | Latest planned tasks/routes |

### Asset Endpoints

| Method | Path | Response | Notes |
| --- | --- | --- | --- |
| `GET` | `/api/agents` | `agent_profile[]` | Known agents from fixture, Mongo, or ROS fleet manager |
| `GET` | `/api/map/features` | `map_feature[]` or GeoJSON | Tactical features, roads, risk zones, workspaces |
| `POST` | `/api/map/features` | `map_feature` | Add UI-drawn geometry as a feature |
| `GET` | `/api/diagnostics` | `diagnostics_state` | Docker/ROS/API health summary |

### Live Event Endpoint

Use one stream for UI live updates:

```text
GET /api/events
```

This can be implemented as WebSocket or Server-Sent Events. Event payloads should be plain JSON.

Recommended event types:

| Event Type | Payload | Source |
| --- | --- | --- |
| `agent.updated` | `agent_runtime_state` | `/multi_robot/edge/feedback`, autonomy localization |
| `mission.updated` | `mission_state` | mission feedback/status topics |
| `plan.updated` | `task_plan` or route summary | planner services/topics |
| `map.updated` | `map_feature` or feature id | Mongo/map adapter |
| `diagnostics.updated` | `diagnostics_state` | ROS/Docker health monitor |
| `log.created` | log entry | `/multi_robot/log`, `/multi_robot/swarm_log` |

## JSON Contracts

The UI/backend boundary should use the repo schemas:

```text
schemas/mission_config.schema.json
schemas/task_plan.schema.json
schemas/agent_profile.schema.json
schemas/map_feature.schema.json
```

The UI can display and edit legacy-like fields, but the backend should normalize them before any planning or ROS call.

Important legacy aliases:

| Legacy Input | Canonical Internal Field |
| --- | --- |
| `objective.geometry` | `objective.geometries[]` |
| `transit.optimalization` | `transit.optimization` |
| `transit.vehicle_constraints` | `transit.desired_vehicle_constraints` |
| `transit.desired_speed` | `transit.desired_vehicle_constraints.max_speed` |
| `objective.maximize_area_coverage` | `objective.maximize_coverage` |
| scalar `objective.vehicle_orientation` | array `objective.vehicle_orientation` |

## Map Interface

The UI should render a real GIS map, not a hand-drawn SVG.

Recommended UI map stack:

```text
Leaflet or MapLibre
+ OpenStreetMap/PMTiles/MBTiles base map
+ GeoJSON overlays from backend
+ mission geometry editing layer
+ live agent marker layer
+ planned trajectory layer
```

The backend should expose tactical map features as GeoJSON-compatible records. The old planner uses map data from:

```text
legacy_ros/config/data/map/rma
legacy_ros/config/data/map/estonia
MongoDB database MapDB, collection rma
```

Coordinate convention:

| Layer | Coordinate Order |
| --- | --- |
| GeoJSON and mission schema | `[lon, lat]` |
| Leaflet marker API | `[lat, lon]` |
| ROS odometry | local pose unless converted |
| Old autonomy config `start_location` | appears as `[lon, lat]` in current config |

The backend should centralize conversions. The UI should treat schema data as GeoJSON-style `[lon, lat]`.

## ROS Compatibility Mapping

The backend ROS adapter should translate UI/API operations to these old ROS interfaces.

### Mission Init

UI:

```text
POST /api/missions/init
```

Backend:

```text
validate mission_config
normalize legacy aliases
assign/verify mission_id
publish or call legacy mission init
```

Legacy ROS:

```text
/multi_robot/mission_init_request
  type: c2_msgs/msg/InitMissionRequest
  fields:
    mission_id UUID
    mission_config string
```

Response:

```text
/multi_robot/mission_init_response
  type: c2_msgs/msg/InitMissionResponse
  fields:
    mission_id UUID
    mission_feedback string
```

### Mission Status

UI:

```text
POST /api/missions/{mission_id}/approve
POST /api/missions/{mission_id}/start
POST /api/missions/{mission_id}/cancel
```

Legacy ROS:

```text
/multi_robot/change_mission_status_request
/multi_robot/change_mission_status_response
```

The backend should own enum conversion between UI strings and old numeric status values.

### Planner

Backend can either use the replacement `PlannerPort` or the legacy planner services:

```text
/multi_robot/planner/create
/multi_robot/planner/get_plan
/multi_robot/planner/delete
/multi_robot/planner/delete_planner
```

The UI should only see:

```text
task_plan
planned route overlays
planner diagnostic state
```

### Agent Runtime State

Legacy edge feedback:

```text
/multi_robot/edge/feedback
  type: task_msgs/msg/Feedback
```

Legacy autonomy topics:

```text
/<PREFIX>/edge/multi_robot/localization
/<PREFIX>/edge/multi_robot/vehicle_profile
/<PREFIX>/edge/multi_robot/autonomy_status
/<PREFIX>/edge/multi_robot/autonomy_trajectory
```

The backend should merge these into a UI model:

```json
{
  "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
  "name": "Themis_Fr",
  "status": "active",
  "location": [4.392588, 50.844317],
  "heading_deg": 0,
  "speed_mps": 0,
  "battery_pct": 90,
  "fuel_pct": 85,
  "current_task_id": null,
  "current_objective_id": null,
  "trajectory": []
}
```

## Diagnostics Interface

The diagnostics page should not scrape raw logs in the browser. The backend should expose structured status.

Recommended `diagnostics_state`:

```json
{
  "containers": {
    "c2-imugs2-planner": "running",
    "c2-imugs2-rosbridge": "running",
    "c2-imugs2-edge-agent-sim-1": "running"
  },
  "ros": {
    "nodes": ["/planner_node", "/fleet_manager_node"],
    "topics": ["/multi_robot/edge/feedback"],
    "services": ["/multi_robot/planner/create"]
  },
  "checks": [
    {
      "id": "rosbridge.websocket",
      "status": "ok",
      "message": "ws://localhost:9090 reachable"
    },
    {
      "id": "planner.node",
      "status": "ok",
      "message": "/planner_node visible"
    }
  ]
}
```

Minimum checks:

- backend API responds,
- rosbridge responds,
- required containers are running,
- required ROS nodes are visible,
- required ROS topics are visible,
- required ROS services are visible,
- at least one agent profile/feedback has been seen,
- planner service can be discovered.

## Recommended Implementation Phases

### Phase 1: Documented Static Contract

- Keep current UI fixture mode.
- Add this ICD as the source of truth.
- Ensure frontend TypeScript types mirror schema names.
- Keep `docs/ROS_COMPATIBILITY_ICD.md` as the lower-level ROS reference.

### Phase 2: Backend API

- Add a small API service.
- Expose `/api/agents`, `/api/map/features`, `/api/missions/init`, `/api/events`, `/api/diagnostics`.
- Use existing `MissionService` internally.
- Keep fixture-backed mode for fast tests.

### Phase 3: Real Map UI

- Replace SVG map with Leaflet or MapLibre.
- Load old GeoJSON map features through `/api/map/features`.
- Support drawing polygons and writing them back into `mission_config.objective.geometries`.

### Phase 4: ROS Adapter

- Backend subscribes to old ROS feedback and status topics.
- Backend publishes mission init/status commands.
- UI sees only API events.

### Phase 5: Simulation Control

- Add UI controls for starting/stopping/recreating the legacy stack.
- Add diagnostics tests.
- Add per-agent sim configuration controls.

## Non-Goals

For this stage:

- Do not put benchmarking UI into this interface.
- Do not let the browser construct ROS messages.
- Do not make the UI depend on old node names directly.
- Do not couple real-map rendering to planner internals.

The goal is a clean operator interface that can drive the current legacy simulation and later drive the replacement implementation through the same API contract.
