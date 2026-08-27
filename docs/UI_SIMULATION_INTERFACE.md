# UI To Simulation Interface

> **Documentation label: CONTRACT**
> Stable browser-facing boundary. Runtime implementation belongs in the
> adapter and editable ROS runtime described by [Architecture](ARCHITECTURE.md).

This is the stable boundary between the operator UI and the current simulation runtime. For implementation details, see [UI_BACKEND_LEGACY_ADAPTER.md](UI_BACKEND_LEGACY_ADAPTER.md). For lower-level ROS contracts, see [ROS_COMPATIBILITY_ICD.md](ROS_COMPATIBILITY_ICD.md).

## Boundary

```text
Operator
  -> React UI
  -> FastAPI JSON/SSE interface
  -> legacy REST and rosbridge adapters
  -> editable backend fog, planner, fleet, edge, and autonomy simulation
```

The UI renders state and sends operator commands. It does not construct ROS messages, query MongoDB, run planning algorithms, or connect directly to rosbridge.

The backend:

- executes the canonical mission schema and semantic checks after normalizing legacy aliases,
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
| Scenario | `GET /api/scenarios`, `GET /api/scenarios/active`, `POST /api/scenarios/activate` |
| Assistant | `GET /api/assistant/status`, `GET /api/assistant/operational-picture`, `POST /api/assistant/messages`, `DELETE /api/assistant/conversations/{id}` |
| Map | `GET/POST /api/map/features`, `PUT/DELETE /api/map/features/{id}`, `POST /api/map/osm-roads/query` |
| Live state | `GET /api/events` |

The API implementation may include experimental map/scenario helpers. They are not compatibility contracts until documented as stable.

The assistant endpoint completes one non-streaming model request. The optional
request field `debug=true` adds a bounded, redacted trace of the exact model
messages, final provider event, and any actual tool calls to the response. The
UI exposes that option only when opened with `?assistantDebug=1`. The same
discoverability gate reveals Scenario Lab, Contracts, and C2 Diagnostics; it is
not access control. No tools are currently bound to the LLM.

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

Important legacy limitation: the old REST status body contains no mission id
and targets `/c2_node`'s last initialized mission. The adapter rejects unknown,
forgotten, or non-current route IDs before calling that bridge. It also rejects
Approve before PLANNED/PLANNED_ALTERNATIVE and Start before ACCEPTED. Its
immediate accepted response remains an adapter acknowledgement until ROS
feedback confirms the state.

Init additionally requires a ready active scenario and verifies that every mission vehicle belongs to it. Roads are never appended to `objective.geometries`; the planner reads them from the active scenario's immutable MapDB collection.

## Scenario Activation

The scenario selector exists only in the gated Scenario Lab. Selecting a draft
does not change C2 reality; pressing **Activate** freezes the map, restarts
coordination, the planner, the REST bridge, and rosbridge on that version,
replaces the robot simulation containers, and waits for matching ROS
registrations. The C2 tab displays the active readiness state but cannot switch
it.

The Roads panel downloads OSM highways only through an explicit polygon action.
Those roads remain draft data until activation. Once active, that frozen
GeoJSON is the map source used by both the C2 display and the editable backend
planner.

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

The mission endpoint executes `mission_config.schema.json` after alias
normalization and then applies semantic and active-scenario checks. Legacy
planner/edge code still has additional runtime invariants, so schema validity
alone is not a feasibility guarantee.

Important conventions:

- GeoJSON and mission coordinates are `[lon, lat]`.
- Leaflet marker coordinates are `[lat, lon]`.
- ROS odometry is a local pose unless an adapter converts it.
- Legacy aliases are accepted at input, normalized by the backend, and translated back only at the legacy boundary.
- Reverse translation covers `optimization -> optimalization` and the coverage
  swath field `maximum_coverage_distances -> maximize_coverage_distances`; not
  every other canonicalized formation alias is translated yet.
- The mission editor keeps selected saved assets traceable by `feature_id`;
  selecting **Use geofence** creates a coverage mission and writes the same ID
  to `transit.geofence.feature_id` and `objective.geometries[0].feature_id`.
  It sets `behavior=1`, `maximize_coverage=true`, and uses each selected scenario
  vehicle's `constraints.coverage_width_m` swath. An existing draft width takes
  precedence, and vehicles without a usable value retain the `6 m` fallback.
  At mission initialization, the adapter inlines runtime user-feature geometry
  only in the translated copy sent to old REST/ROS when the planner cannot
  resolve that ID. Scenario roads remain in MapDB and are not sent in mission
  JSON.

Allowed UI-created feature geometries:

| Feature | Geometry |
| --- | --- |
| `objective` | `Point` |
| `road` | `LineString` |
| `geofence`, `workspace`, `risk` | `Polygon` |

The current simple navigation flow should not create arbitrary polygon objectives.
Coverage missions use one Polygon objective, `behavior=1`,
`maximize_coverage=true`, and `objective.maximum_coverage_distances`. That array
contains either one shared swath width in metres or one width per mission
vehicle.

## Operational Expectations

The UI should:

- open with no mission selected,
- show examples only in the new-mission flow,
- replace local mission JSON with the actual config returned by the backend after Init,
- keep mission status separate from path availability,
- expose diagnostics without making raw logs the primary interface.
- show the operational-picture revision used for every assistant answer;
- enable **Inspect in manual UI** only after schema, semantic, ready-scenario and vehicle-membership validation, and
  never initialize an assistant proposal automatically.

When a path is visible but the agent does not move, inspect edge feedback and the autonomy simulation. When a mission is planned but no path is visible, inspect mission feedback for empty tasks or waypoints.

## Non-Goals

- No ROS message logic in the browser.
- No mock replacement for real legacy nodes during compatibility tests.
- No breaking changes to message, service, topic, enum, mission, or task-plan contracts.
- No LLM benchmarking until the verified mission-generation path is ready.
- No model access to ROS, MongoDB, Docker, runtime files, or mission commands.
