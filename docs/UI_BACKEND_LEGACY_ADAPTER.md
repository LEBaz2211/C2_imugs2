# UI to Editable ROS Backend Adapter

> **Documentation label: CURRENT**
> Evolving adapter implementation. Use [Architecture](ARCHITECTURE.md) for
> ownership boundaries and verify volatile details against source and tests.

This phase preserves the old ROS contracts in the editable `backend/` runtime and places a stable FastAPI adapter between the browser UI and ROS.

Compatibility rules and project priorities are in [PROJECT_PLANNING.md](../PROJECT_PLANNING.md).

## Runtime Shape

```text
Browser UI (Vite/React/Leaflet)
  -> http://localhost:8000/api/*
Backend Adapter (FastAPI)
  -> http://localhost:5001/mission_control for mission commands
  -> ws://localhost:9090 for ROS diagnostics and live read-side events
  -> backend/config/data/map/<map> for GeoJSON overlays
Editable backend Docker stack
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
POST   /api/map/osm-roads/query?map=rma
GET    /api/scenarios
GET    /api/scenarios/active
POST   /api/scenarios/activate
GET    /api/assistant/status
GET    /api/assistant/operational-picture
POST   /api/assistant/messages
DELETE /api/assistant/conversations/{conversation_id}
GET    /api/agents
GET    /api/mission-examples
POST   /api/missions/init
GET    /api/missions/{mission_id}
POST   /api/missions/{mission_id}/approve
POST   /api/missions/{mission_id}/start
DELETE /api/missions/{mission_id}
GET    /api/events
```

`/api/missions/init` requires a ready active scenario, normalizes old mission
config aliases, executes the canonical draft-2020-12 JSON Schema and semantic
checks, verifies scenario vehicle membership, ensures the legacy mission ID is
UUID-shaped, then posts `action=initialize` to the old REST bridge. Scenario
roads are not added to mission JSON.

`/api/scenarios/activate` content-addresses the complete scenario, records
durable activation phases in MongoDB, writes its selected assets and downloaded
OSM LineStrings to an immutable MapDB collection, clears prior mission runtime,
restarts centralized coordination, the planner, the C2 REST bridge, and
rosbridge, replaces the prior scenario robot containers, and returns success
only after the exact collection and all robot IDs are verified. The local
host-network simulation uses loopback-only ROS discovery with an expanded
CycloneDDS participant-index range, so host interface changes cannot strand a
still-listening gateway outside the ROS graph or cap the local multi-process fleet.
Repeating the same healthy content is idempotent.

`/api/assistant/messages` performs one non-streaming LangChain request to the
configured LM Studio server, with maximum Qwen reasoning enabled and provider
retries disabled. It injects a freshly
materialized, source-labelled operational picture into every message and
reports the revision used. The model-facing projection calls the active world
the current environment and omits scenario/version/collection/activation
identity; the backend retains that identity for stale-proposal validation.
Bounded active Point/Polygon feature facts are read from the exact active MapDB
collection, so a named feature can be grounded without treating mutable
authoring state as active truth. A generated mission is schema/semantically
checked and bound internally to current ready runtime/vehicle membership,
displayed as a draft, and never initialized automatically.

`/api/assistant/operational-picture` exposes the same first-full, then keyed
diff protocol for inspection. A supplied `since_checksum` is verified; the
assistant's internal conversation path always supplies it.

The UI hides all advanced inspection surfaces unless the URL contains
`?assistantDebug=1`: Scenario Lab, Contracts, C2 Diagnostics, and the assistant
Debug control share that one discoverability gate. Enabling **Debug** before a
message requests the exact
redacted model input, final provider event, and any actual tool calls for that
turn. Backend context and validation events are identified separately. No
model-callable tools are currently configured. The browser stores up to 20
locally navigable conversations with 80 visible transcript items each and
migrates the former single-conversation record. New, history-select, and delete
controls do not alter separately persisted mission drafts. Every
deterministically valid proposal is registered immediately as a draft mission,
so leaving the assistant does not make it disappear from the mission list.
Backend dialogue state remains process-local, making model continuity after an
API restart best-effort even though the browser transcript is retained.

`/api/missions/{id}/approve` and `/start` post `action=change_status` to the old REST bridge using the legacy numeric mission request values.

The old status envelope contains no mission id. `/c2_node` applies it to the
last mission initialized through that bridge. The adapter therefore forwards a
status command only when the route mission exists, is visible, and equals the
last successfully initialized target; otherwise it returns `404` or `409`
without calling the bridge. It also requires PLANNED/PLANNED_ALTERNATIVE before
Approve and ACCEPTED before Start. Immediate `ACCEPTED`/`STARTED` responses are
still adapter acknowledgements; ROS feedback is the authoritative confirmation.

The UI command buttons mean:

```text
Apply   local UI only: parse/normalize the mission JSON and update the map/task preview
Init    backend posts action=initialize to old REST, which publishes /multi_robot/mission_init_request
Approve backend posts action=change_status with legacy requested_state=1
Start   backend posts action=change_status with legacy requested_state=2
```

The app opens without a selected mission. Mission JSON comes from an explicit
example selection, drawing on the map, pasting JSON, or a valid assistant
proposal. Such a proposal is registered as a local draft immediately and has a
conversation card with progress, Open/Validate, and state-appropriate
Init/Approve/Start actions. Clicking it selects the ordinary mission workspace
and updates the map through the same state as the normal mission list.

Deleting a mission removes it from adapter/UI runtime only. It does not delete editable-backend ROS or MongoDB records.

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

## Backend Smoke Test

After starting `docker-compose.backend.yml`, run:

```bash
./scripts/check_backend_ros_stack.sh
```

The script checks required containers, required ROS nodes, required ROS topics, old REST reachability, and rosbridge WebSocket reachability.
