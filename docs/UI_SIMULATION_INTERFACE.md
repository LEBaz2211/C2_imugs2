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
| Worlds | CRUD under `/api/worlds`, `GET /api/worlds/active`, `POST /api/worlds/{world_id}/launch`, deployment-bound live-feature routes, and world-bound road-import routes |
| Assistant | `GET /api/assistant/status`, `GET /api/assistant/operational-picture`, `POST /api/assistant/messages`, `DELETE /api/assistant/conversations/{id}` |
| Map authoring | `GET/POST /api/map/features`, `PUT/DELETE /api/map/features/{id}`, `GET /api/map/osm-roads` |
| Live state | `GET /api/events` |

The API implementation may include experimental map/world helpers. They are not compatibility contracts until documented as stable.

The assistant endpoint completes one non-streaming model request. The optional
request field `debug=true` adds a bounded, redacted trace of the exact model
messages, final provider event, and any actual tool calls to the response. The
UI exposes that option only when opened with `?assistantDebug=1`. The same
discoverability gate reveals Contracts and C2 Diagnostics; it is not access
control. World Builder remains available in the ordinary UI so operators can
select and launch a world. No tools are currently bound to the LLM.

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

Init additionally requires a ready active world and verifies that every mission vehicle belongs to it. Roads are never appended to `objective.geometries`; the planner reads them from the active world's immutable MapDB collection.

## World Definitions And Launch

The world-definition selector and Launch action are available in the ordinary
World Builder UI. A world definition is stored authoring state, not runtime state. Selecting or editing
a definition does not change C2 reality; pressing **Launch** freezes the map, restarts
coordination, the planner, the REST bridge, and rosbridge on that version,
replaces the robot simulation containers, and waits for matching ROS
registrations. The C2 tab displays the active readiness state but cannot switch
it.

After launch, C2 and the backend use the launched active-world snapshot and
live runtime revisions. They must not read mutable values from the selected
browser definition. World endpoint and field names are the maintained public
contract.

The Roads panel downloads OSM highways only through an explicit polygon action.
Those roads remain draft data until launch. Once active, that frozen
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
normalization and then applies semantic and active-world checks. Legacy
planner/edge code still has additional runtime invariants, so schema validity
alone is not a feasibility guarantee.

Important conventions:

- GeoJSON and mission coordinates are `[lon, lat]`.
- Leaflet marker coordinates are `[lat, lon]`.
- ROS odometry is a local pose unless an adapter converts it.
- Legacy aliases are accepted at input, normalized by the backend, and translated back only at the legacy boundary.
- Reverse translation covers `optimization -> optimalization`,
  `maximum_coverage_distances -> maximize_coverage_distances`, and the
  inherited formation/geofence spellings needed by the ROS parser.
- `maximum_coverage_distances` constrains separation between vehicles.
  `coverage_swath_widths` spaces area-coverage lanes and normally comes from
  each active-world vehicle's `constraints.coverage_width_m`.
- The mission editor keeps selected saved assets traceable by `feature_id`;
  selecting **Use geofence** creates a coverage mission and writes the same ID
  to `transit.geofence.feature_id` and `objective.geometries[0].feature_id`.
  It sets `behavior=1`, `maximize_coverage=true`, and uses each selected world
  vehicle's `constraints.coverage_width_m` swath. An existing draft width takes
  precedence, and vehicles without a usable value retain the `6 m` fallback.
  At mission initialization, the adapter inlines runtime user-feature geometry
  only in the translated copy sent to old REST/ROS when the planner cannot
  resolve that ID. World roads remain in MapDB and are not sent in mission
  JSON.

Allowed UI-created feature geometries:

| Feature | Geometry |
| --- | --- |
| `objective` | `Point` |
| `road` | `LineString` |
| `geofence`, `workspace`, `risk` | `Polygon` |

The simple draw-a-destination navigation tool creates Point objectives.
Advanced templates may use a Polygon as a multi-vehicle deployment region.
Area-coverage missions use a Polygon objective, `behavior=1`,
`maximize_coverage=true`, and an effective swath supplied by
`objective.coverage_swath_widths` or the selected vehicles' active-world
profiles. `objective.maximum_coverage_distances` remains a vehicle-separation
constraint.

## Mission Examples

`GET /api/mission-examples` serves the checked-in examples shown only in the
new-mission flow. Choosing an example creates a fresh mission ID and treats the
example vehicle list as ordered template slots. The UI maps those slots to the
first active-world vehicles in displayed order that advertise every required
capability and satisfy comparable requested vehicle limits. If there are too few compatible vehicles, it warns and leaves the
template IDs unchanged for the operator to resolve; it does not create robots,
features, roads, or a world for the operator.

The examples are editable mission templates, not self-contained simulations.
Before Init, the operator must launch a world whose routing graph covers the
template coordinates and whose vehicles meet the template count, capability,
constraint, and coverage-sensor needs. Feature references, if retained after
editing, must exist in that exact active-world snapshot. See
[ICD Mission Examples](ICD_MISSION_EXAMPLES.md) for the per-template
prerequisites and current execution limits.

## Mission Behavior Dispatch

The editable planner dispatches geometry according to `behavior` and geometry
type:

| Behavior and objective | Planner action |
| --- | --- |
| `NAVIGATE=0` + Point or MultiPoint | Route selected vehicles to one or more destinations; use ordered or closest allocation where requested. |
| `NAVIGATE=0` + LineString or Polygon | Place/deploy vehicles along or around the geometry. `maximize_coverage` affects the spatial deployment; it does not create lawnmower lanes. |
| `COVERAGE=1` + Polygon | Generate risk-aware lawnmower lanes using sensor swath widths. |
| `COVERAGE=1` + LineString | Follow/patrol the line and divide its continuous work among vehicles. |
| `COVERAGE=1` + Polygon with `road_usage=1` | Patrol active-world road edges contained by the polygon. |
| `COVERAGE=1` + explicit `maximize_coverage=false` | Reach the geometry without performing the coverage/patrol action. |
| `NAVIGATE_NO_PLANNING=2` | Rejected by the editable path planner; no raw no-planning executor is implemented. |

This is why a Polygon coverage mission uses lawnmower coverage, while the ICD
navigation/deployment examples do not.

## Init Preflight And Time Semantics

Init is bound to the immutable active world and rejects:

- selected vehicle IDs that are absent from that world;
- referenced feature IDs absent from that world's feature set;
- any `required_capabilities` missing from any selected vehicle;
- a requested numeric vehicle limit that exceeds the corresponding numeric
  limit declared by an active-world vehicle profile; and
- a LineString relay whose requested maximum separation and endpoint tolerance
  cannot span the line with the selected vehicle count.

Time windows must be timezone-qualified ISO 8601 and satisfy
`earliest <= target <= latest`. The edge waits until `start.start_time.earliest`
before releasing a task. For the final waypoint, it adjusts speed toward
`objective.arrival_time.target` and waits until `arrival_time.earliest` before
completion. Expired example timestamps execute immediately. `latest` and
`mission_end_time` are currently preserved in task metadata but are not
deadline/failure conditions.

## Operational Expectations

The UI should:

- open with no mission selected,
- show examples only in the new-mission flow,
- replace local mission JSON with the actual config returned by the backend after Init,
- keep mission status separate from path availability,
- expose diagnostics without making raw logs the primary interface.
- show the operational-picture revision used for every assistant answer;
- enable **Inspect in manual UI** only after schema, semantic, ready-world and vehicle-membership validation, and
  never initialize an assistant proposal automatically.

When a path is visible but the agent does not move, inspect edge feedback and the autonomy simulation. When a mission is planned but no path is visible, inspect mission feedback for empty tasks or waypoints.

## Non-Goals

- No ROS message logic in the browser.
- No mock replacement for real legacy nodes during compatibility tests.
- No breaking changes to message, service, topic, enum, mission, or task-plan contracts.
- No LLM benchmarking until the verified mission-generation path is ready.
- No model access to ROS, MongoDB, Docker, runtime files, or mission commands.
