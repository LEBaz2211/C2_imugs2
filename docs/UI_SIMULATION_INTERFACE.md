# UI To Simulation Interface

This is the stable boundary between the operator UI and the current simulation runtime. For implementation details, see [UI_BACKEND_LEGACY_ADAPTER.md](UI_BACKEND_LEGACY_ADAPTER.md). For lower-level ROS contracts, see [ROS_COMPATIBILITY_ICD.md](ROS_COMPATIBILITY_ICD.md).

## Boundary

```text
Operator
  -> React UI
  -> FastAPI JSON/SSE interface
  -> legacy REST and rosbridge adapters
  -> legacy ROS fog, planner, fleet, edge, and autonomy simulation
```

The UI renders state and sends operator commands. It does not construct ROS messages, query MongoDB, run planning algorithms, or connect directly to rosbridge.

The backend:

- performs partial structural validation and normalizes mission JSON,
- translates canonical fields and enums to legacy forms,
- serves maps, agents, examples, and runtime state,
- sends mission commands through the old REST bridge,
- normalizes ROS feedback into UI-facing JSON,
- centralizes coordinate conversions and legacy workarounds.

## Current UI API

| Area | Endpoints |
| --- | --- |
| Health | `GET /api/health`, `/api/diagnostics`, `/api/planning/diagnostics`, `/api/legacy/trace` |
| Contracts | `GET /api/contracts` |
| Bootstrap | `GET /api/runtime/bootstrap`, `/api/agents`, `/api/mission-examples` |
| Missions | `POST /api/missions/init`, `GET /api/missions/{id}`, `POST /approve`, `POST /start`, `DELETE /api/missions/{id}` |
| Map | `GET/POST /api/map/features`, `PUT/DELETE /api/map/features/{id}`, `GET /api/map/osm-roads` |
| Live state | `GET /api/events` |

The API implementation may include experimental map/scenario helpers. They are not compatibility contracts until documented as stable.

`GET /api/contracts` contains a curated `atlas` for the verified active mission path and a broader source-discovery catalog. The atlas is authoritative for the visualization; raw scanner discoveries are evidence candidates, not proof of an active runtime contract.

## Mission Commands

| UI action | Backend behavior | Legacy request |
| --- | --- | --- |
| Apply | Parse and update local UI state | none |
| Init | Validate, normalize, inline runtime features, call old REST | `INIT=0` |
| Approve | Call old REST status change | `APPROVE=1` |
| Start | Call old REST status change | `START=2` |
| Delete | Hide/remove adapter runtime state | no legacy deletion |

Deleting through the UI does not remove ROS or MongoDB mission records. Test database cleanup is a separate, destructive action.

Important legacy limitation: approve/start are mission-specific only at the FastAPI route. The old REST status body contains no mission id and targets `/c2_node`'s last initialized mission. The adapter's immediate `ACCEPTED`/`STARTED` response is optimistic until ROS feedback confirms the state.

## Live Events

`GET /api/events` is a Server-Sent Events stream:

| Event | Meaning |
| --- | --- |
| `diagnostics.updated` | Backend and ROS reachability |
| `mission.updated` | Mission status, feedback, and path status |
| `agent.updated` | Normalized edge/agent state |
| `planner.updated` | Planner state or paths extracted from mission feedback |

Planner `READY` means the node is ready; it does not prove that a mission has a route. The UI should display a route only when mission feedback contains non-empty waypoint tasks.

## Data Rules

Use the canonical schemas:

```text
schemas/mission_config.schema.json
schemas/task_plan.schema.json
schemas/agent_profile.schema.json
schemas/map_feature.schema.json
```

These schemas describe the intended contract. The current mission endpoint does not execute full JSON Schema validation; its handwritten checks cover only a subset, and legacy planner/edge code has additional runtime invariants.

Important conventions:

- GeoJSON and mission coordinates are `[lon, lat]`.
- Leaflet marker coordinates are `[lat, lon]`.
- ROS odometry is a local pose unless an adapter converts it.
- Legacy aliases are accepted at input, normalized by the backend, and translated back only at the legacy boundary.
- The current reverse translation covers `optimization -> optimalization`, but not every canonicalized coverage/formation alias.
- UI-created features must be sent to the old planner as inline geometry because its baseline feature lookup does not know runtime feature ids.

Allowed UI-created feature geometries:

| Feature | Geometry |
| --- | --- |
| `objective` | `Point` |
| `road` | `LineString` |
| `geofence`, `workspace`, `risk` | `Polygon` |

The current simple navigation flow should not create arbitrary polygon objectives.

## Operational Expectations

The UI should:

- open with no mission selected,
- show examples only in the new-mission flow,
- replace local mission JSON with the actual config returned by the backend after Init,
- keep mission status separate from path availability,
- expose diagnostics without making raw logs the primary interface.

When a path is visible but the agent does not move, inspect edge feedback and the autonomy simulation. When a mission is planned but no path is visible, inspect mission feedback for empty tasks or waypoints.

## Non-Goals

- No ROS message logic in the browser.
- No mock replacement for real legacy nodes during compatibility tests.
- No breaking changes to message, service, topic, enum, mission, or task-plan contracts.
- No LLM benchmarking until the verified mission-generation path is ready.
