# ICD Examples — Code Sequence And Planner Algorithms

> **Documentation label: CURRENT**
> Explains how `fixtures/mission_examples/*` flow through validation, the
> editable ROS backend, and the planner. Verify volatile details against
> source, `tests/test_icd_examples.py`, and the running backend.

## 1. Two Mission Paths In The Code

| Path | Where | Used for |
| --- | --- | --- |
| Core seam | `src/c2_imugs2/core/mission_service.py` + `core/planner.py` `SimplePlanner` | Offline CLI/testing only (`src/c2_imugs2/cli.py:8-22`). It plans locally and never touches ROS. |
| Live adapter path | `src/c2_imugs2/api/services.py` `BackendMissionApplicationService` | Everything in the browser UI. It validates, shapes a compatibility copy, forwards to old REST, and lets the **real** ROS `planner_node` do the planning. |

The examples are exercised through the live path. Planning is serialized, so the
details below focus on `MultiRobotPathPlanning`.

## 2. End-To-End Sequence (Live UI Init)

1. **List examples** — `GET /api/mission-examples` reads every
   `fixtures/mission_examples/*.json` verbatim (`src/c2_imugs2/api/app.py:377-392`).
   The `icd_*` fixtures are world-independent templates with only inline
   geometry (enforced by `tests/test_icd_examples.py:66-77`); the two
   `*_themis` fixtures reference the `feature_id` seeded into `MapDB.rma`.
2. **Choose example** — the UI assigns a fresh mission UUID, slots active-world
   vehicles into the ordered template vehicle list, and checks capabilities
   (see `docs/ICD_MISSION_EXAMPLES.md`).
3. **POST `/api/missions/init`** → `mission_router` (`src/c2_imugs2/api/routers.py:219`)
   → `BackendMissionApplicationService.initialize` (`src/c2_imugs2/api/services.py:86`).
4. **Canonicalize** (`services.py:244-255`): `normalize_mission_config`
   (`src/c2_imugs2/core/mission_config.py:24-100`) fixes legacy spellings
   (`objective.geometry` → `objective.geometries[]`,
   `objective.feature_id` → `objective.geometries[].feature_id`,
   `objective.maximize_area_coverage` → `maximize_coverage`,
   `optimalization` → `optimization`,
   `vehicle_constraints` → `desired_vehicle_constraints`,
   `desired_speed` → `desired_vehicle_constraints.max_speed`,
   `vehicle_formation_distances` → `vehicle_formation_distance`,
   `maximize_coverage_distances` → `maximum_coverage_distances`),
   defaults missing `behavior` to `0`, and sets `maximize_coverage: true`
   for `behavior=1`. Then schema + semantic validation runs
   (`mission_config.py:156-233`).
5. **World binding + preflight** (`services.py:185-197` → `_preflight_mission_against_world`,
   `services.py:532-613`): every referenced `feature_id` must exist in the
   active world snapshot/deployment, each vehicle must advertise every
   `required_capabilities` value, and every numeric
   `transit.desired_vehicle_constraints` field must not exceed the vehicle
   profile. A NAVIGATE relay (`LineString` + `vehicle_order`) is rejected early
   if the infeasible span check fails (`_preflight_relay_geometry`, `services.py:668-693`).
6. **Compatibility shaping** — runs on a `deepcopy`; the canonical config and
   browser state are never mutated:
   - inline active-deployment feature refs (`_inline_live_feature_refs`, `services.py:616-625`)
     and runtime user features (`_inline_user_feature_refs`, `app.py:1346-1379`);
   - inject backend-only `transit.desired_vehicle_constraints.max_speed`
     derived from selected vehicles (`services.py:409-452`) — the inherited
     planner reads it unconditionally (`get_max_speed` also guards direct ROS
     callers, `multi_robot_path_planning.py:995-1020`);
   - inject backend-only `objective.coverage_swath_widths` from each selected
     vehicle's `constraints.coverage_width_m` for polygon area coverage
     (`_ensure_backend_coverage_swaths`, `services.py:455-529`); skipped for
     `road_usage >= 1` patrol and for missions that already declare swaths.
7. **Old REST bridge** — `LegacyRestClient.initialize_mission` posts
   `action=initialize`; `c2_node` publishes
   `/multi_robot/mission_init_request`, `c2_interface_node` stores it, and
   `/orchestrator_node` (5 s poll) registers the mission in MongoDB and spawns
   one dynamic `/mission_<id>` manager node. Adapter response shape/timeout
   handling stays in `services.initialize` (`services.py:131-183`), including
   the backend single-mission `command_target_mission_id` rule.
8. **CreatePlanner** — the mission manager calls
   `/multi_robot/planner/create` (`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:302-334`):
   - `_ensure_map_ready` (`planner_node.py:792-809`) builds the routing graph
     from `MapDB.<collection>` if the watcher has not yet done it, or fails the
     request if the snapshot is empty.
   - `MultiRobotPathPlanning.update_mission`
     (`path_planning_lib/path_planning_lib/multi_robot_path_planning.py:36-96`)
     normalizes legacy aliases again (defense in depth), and resolves **every**
     `feature_id` (objective geometry, `vehicle_orientation_origin`,
     `line_of_sight`, `start.geometry`, `transit.geofence`, `transit.roads`)
     against the exact active-world Mongo collection (`_resolve_geometry_ref`,
     `multi_robot_path_planning.py:98-123`). Unknown ids raise, rather than
     silently producing non-executable geometry.
   - Sets `planner_states = 0`, clears cached paths, `mission_defined = True`.
9. **Planning timer** (`planner_node.py:226-296`, 1 Hz): marks state `1`,
   waits until **every** mission vehicle has a live `Buddy` in the
   `/multi_robot/planner/agent` cache (`planner_node.py:240-253`), sets nominal
   speeds from the mission `max_speed` (`planner_node.py:260-264`), then under
   `paths_mutex` runs `solve_mission` (`planner_node.py:268-275`) and caches
   `{agent_id: [waypoints]}` with state `2`. Planning is request-driven: a
   successful solve sets `mission_defined = False` so a moving robot cannot
   re-run planning against its own executing tasks (`planner_node.py:277-283`).
   Any exception clears cached paths, sets state `4`, and keeps the node alive
   (`planner_node.py:287-296`).
10. **GetPlan** — the mission manager polls planner state; at state `2` it calls
    `/multi_robot/planner/get_plan` (`planner_node.py:440-459`), which serializes
    the cached paths into task-plan JSON (`path_to_plan_json`, `planner_node.py:338-437`).
    The plan is registered as mission feedback (MongoDB `Planning`/`MissionFeedback`
    and `/multi_robot/mission_feedback`), which the adapter normalizes into
    `planned_paths` + `path_status` and streams as SSE `mission.updated`
    (`app.py:426-450`). The adapter never promotes a
    `/multi_robot/planner/state` READY to mission `PLANNED` — real waypoints
    come only from mission feedback (`_mission_updates_from_planner_state`, `app.py:1320-1343`).
11. **Approve** — `POST /api/missions/{id}/approve` → `change_status` with
    requested state `1`; adapter only allows it from `PLANNED`/`PLANNED_ALTERNATIVE`
    (`services.py:284-298`); mission manager moves to `ACCEPTED`.
12. **Start** — `POST /api/missions/{id}/start` → requested state `2`; the
    fleet manager dispatches task plans to the edge agents, the supervisor
    advances objectives, and the autonomy simulator executes waypoint paths and
    publishes edge feedback.
13. **Terminal states** — mission feedback `COMPLETED/FAILED/STOPPED/...`
    streams to the UI; `DELETE /api/missions/{id}` only forgets it in the
    adapter (`services.py:348-361`).

## 3. Planner Entry Point

`solve_mission` (`multi_robot_path_planning.py:125-146`) is a two-way
dispatcher on `behavior`:

```text
behavior 0 (NAVIGATE)             -> _solve_navigation
behavior 1 (COVERAGE)             -> _solve_coverage
behavior 2 (NAVIGATE_NO_PLANNING) -> ValueError: not executable by the planner
no paths / no geometry            -> RuntimeError before state 2
```

Geometry is first split (`_mission_geometry_groups`, `multi_robot_path_planning.py:148-169`)
into `points` (Point / MultiPoint, validated by `_point_coordinates` which
unwraps the C++ `[[lon, lat]]` Point serialization) and
`shaped_geometries` (Polygon / LineString).

## 4. NAVIGATE (Behavior 0) Algorithm

`_solve_navigation` (`multi_robot_path_planning.py:187-243`) proceeds in
four stages, all merged into one goal list per agent:

1. **Single-point group deployment** — with exactly one Point objective and any
   of `vehicle_formation` / `minimum_distance` / `maximum_distance` /
   `maximize_coverage` set, `_point_objective_placements`
   (`multi_robot_path_planning.py:282-341`) spreads the vehicles geometrically:
   - placement ring center = the point offset by
     `radius = (min+max)/2` (or `min`) **away from the threat**: direction from
     the point toward `vehicle_orientation_origin`;
   - formation `2` (LINE): placements on the axis perpendicular to that
     threat bearing (the protective flank);
   - any other formation: `_formation_points`
     (`multi_robot_path_planning.py:502-531`: COLUMN=1, LINE=2, WEDGE=3,
     VEE=4, LEFT_FLANK=5, RIGHT_FLANK=6, spaced by
     `vehicle_formation_distance`, polygons may clamp back to their interior);
   - no formation: an even ring of radius `spacing`.
   Allocation honors `objective.vehicle_order` if present, otherwise uses the
   greedy allocator (stage 2).
2. **Point allocation** — `_allocate_points` (`multi_robot_path_planning.py:352-387`):
   with `vehicle_order`, goal k/k mod len fills agents in listed order; without
   it, the globally closest remaining agent/goal pair is assigned repeatedly,
   continuing from each agent's last goal. One-responder selection (ICD 3.2)
   emerges from the `one_to_one` branch: with one goal and several agents,
   exactly the **closest** agent receives it and the rest get no task.
3. **Shaped-geometry placement** — `_placement_points_for_geometry`
   (`multi_robot_path_planning.py:417-467`):
   - LineString → evenly interpolated points along the line
     (`maximum_coverage_distances` is validated as a maximum vehicle
     separation, raising if `length/(n-1)` exceeds it — ICD 4's relay line);
   - Polygon with `minimum_distance`/`maximum_distance` → a standoff ring at
     the mean distance (`_polygon_standoff_points`, `multi_robot_path_planning.py:491-500`)
     — ICD 3.1's 100–200 m screening band;
   - Polygon with a formation → formation points inside the polygon;
   - Polygon without either → real graph nodes covered by the polygon,
     spread by max-min-distance from the centroid.
4. **Start staging** — `_start_formation_allocations`
   (`multi_robot_path_planning.py:245-280`): when `start.geometry` exists, its
   representative point is used as a staging waypoint for every agent, spread
   by the declared `start`/`transit` formation (or merged on one point), and
   **prepended** to each agent's goals. Robots always drive there first; no
   teleporting.

**Routing** — `_paths_for_allocations` (`multi_robot_path_planning.py:389-415`)
chains A* segments for every goal:

- `_search_route` (`multi_robot_path_planning.py:907-956`) is query-local:
  snap current position and destination to the nearest **risk-safe edge
  point** with `EdgeSnapIndex.snap` (`path_planning_lib/graph.py:112-146`,
  connector must not cross risk interiors), then `add_virtual_endpoint_nodes`
  (`graph.py:71`) attach both to the immutable snapshot graph, and
  `AStar(..., start_node, destination_node, optimization, constraints)` solves
  the segment. Risk edges are **hard-blocked** by
  `best_routable_edge` (`path_planning_lib/mapf.py:83-93`) — never soft cost.
- Edge cost (`edge_cost`, `mapf.py:58-81`):
  `road_usage >= 0.999` makes offroad edges infinite (strict road following);
  otherwise road/offroad factors `1.5 - road_usage` and `0.5 + road_usage`
  blend weighted `visibility`/`energy` costs with edge length, and
  `max_straight_slope`/`max_side_slope` request gates make violating edges
  infinite. Heuristic stays plain Manhattan (`mapf.py:95-104`).
- The exact requested endpoints are appended (`_navigation_path_from_route`,
  `multi_robot_path_planning.py:697-718`), then `_remove_collinear_waypoints`
  (`multi_robot_path_planning.py:720-737`) collapses redundant collinear
  lattice nodes only if the replacement connector stays risk-free
  (`_connector_is_risk_free`, `multi_robot_path_planning.py:893-895`).

## 5. COVERAGE (behavior 1) Algorithm

`_solve_coverage` (`multi_robot_path_planning.py:533-577`) branches on geometry
and `transit.optimization.road_usage`:

1. `maximize_coverage: false` or Point-only objectives fall back to plain
   `_solve_navigation` (lines 534-539).
2. **LineString** → `line_patrol`: walk the declared coordinates directly.
3. **`road_usage >= 1`** → `road_patrol` (`_road_patrol_path`,
   `multi_robot_path_planning.py:584-615`): build a subgraph of active-world
   graph edges flagged `surface == 'road'` and covered by the objective
   Polygon; fail if empty or disconnected; then Eulerize and emit one
   continuous closed Eulerian circuit over every road edge. No swath or camera
   profile is involved (that is why the adapter skips swath injection —
   `services.py:467-475`).
4. Otherwise **area coverage**: `lawnmower_coverage_path`
   (`path_planning_lib/max_coverage.py:16-88`) with
   `swath = min(coverage_swath_widths)` of the mission vehicles
   (`_coverage_widths_by_vehicle`, `multi_robot_path_planning.py:765-792`):
   - project to local UTM; align passes along the polygon's
     longest-minimum-rectangle axis;
   - subtract risk polygons buffered by `0.5 m` centerline clearance
     (`_subtract_risk_polygons`, `max_coverage.py:124-160`; disconnected
     remnants are rejected);
   - generate boundary-inset lawnmower lanes spaced no more than one swath
     apart; join lane fragments greedily through the nearest risk-safe
     endpoint with visibility connectors that stay inside the polygon
     (`_order_lane_fragments` + `_shortest_inside_path`,
     `max_coverage.py:184-289`).
5. Division and transit — `_split_continuous_path`
   (`multi_robot_path_planning.py:794-844`) cuts the work path into
   equal-arc-length chunks in mission vehicle order;
   `_route_agent_to_coverage_chunk` (`multi_robot_path_planning.py:846-891`)
   A*-routes each ordered agent to whichever chunk end is closer (it tries
   forward and reversed), then appends the sweep. `coverage_action` is stored
   in `planner_hints` for task metadata.

## 6. Task Plan Serialization And Executed Semantics

- `_build_plan_metadata` (`multi_robot_path_planning.py:617-663`) records per
  agent: `coverage_action`, `payload_action`, `desired_heading_deg` —
  `bearing(path[-1] -> vehicle_orientation_origin) + requested offset`
  when an origin is declared — `line_of_sight_target`,
  `start_time` / `arrival_time` / `mission_end_time` windows, transit and
  start formations, and `desired_vehicle_constraints`/`optimization`.
- `GetPlan` → `path_to_plan_json` (`planner_node.py:338-437`) emits one
  waypoint objective per path coordinate; the **final objective** carries the
  semantics above. Task/objective/waypoint UUIDs are regenerated per request.
- Edge runtime (`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/`):
  the supervisor holds a primitive until `arrival_time.earliest` opens
  (`agent_tasks_supervisor_node.cpp:492-505`), waits out `wait_time`
  (line 678), adjusts the final-leg speed toward `arrival_time.target`
  (lines 632-649), clamps to requested motion limits, retains `start_time`
  gates (line 877), and records `payload_state` for `pickup`/`dropoff`
  objectives (lines 549-572). The autonomy simulator accelerates toward the
  objective with the requested max/decel limits, brakes by stopping distance,
  snaps to within objective tolerance, and applies `desired_heading_deg` on
  arrival (`test_autonomy.cpp:79-98, 239-267`).
- Vehicle formation is a **final placement semantic** reflected in waypoints
  and heading; it is not enforced as a transit controller.

## 7. Where Each ICD Example Ends Up

| Fixture | Behavior / vehicles | Interpretation branch | Extra preflight notes |
| --- | --- | --- | --- |
| `icd_01_waypoint_formation.json` | NAVIGATE, 3 | Polygon objective + VEE (`formation=4`) placements via `_formation_points` inside the polygon; `start.geometry` + transit COLUMN (`formation=1`, 5 m) staging waypoints prepended; final headings from `vehicle_orientation` | Road-capable graph and capable vehicles required for a usable route |
| `icd_02a_goods_pickup.json` | NAVIGATE, 4 | 4-point `MultiPoint` allocation (`one_to_one` greedy); `arrival_time.window`; `payload_action: pickup` | `cargo` capability preflight |
| `icd_02b_goods_delivery.json` | NAVIGATE, 4 | Same MultiPoint allocation; `payload_action: dropoff`; `start.start_time` carried | `cargo` capability preflight |
| `icd_03a_screen.json` | NAVIGATE, 4 | Polygon with `min=100/max=200` → 150 m standoff ring around the mission area; threat-relative headings from `vehicle_orientation_origin`; LOS carried | `camera` capability |
| `icd_03b_casevac_pickup.json` | NAVIGATE, 4 | Single Point + no formation → `one_to_one` branch assigns the **globally closest eligible agent only** | All selected vehicles need `casualty_transport` |
| `icd_03c_casevac_safe.json` | NAVIGATE, 1 | Plain single-point navigation; `payload_action: dropoff` | `casualty_transport` |
| `icd_04_communication_relay.json` | NAVIGATE, 4 | LineString + `vehicle_order: true` → ordered, evenly interpolated relay placements; `maximum_coverage_distances: [500]` enforced as max vehicle separation; `line_of_sight_propagation` metadata | Feasibility: `length <= 3*500 + 2*100` m (`_preflight_relay_geometry`, mirrored in the planner at `multi_robot_path_planning.py:424-431`); `radio_relay` |
| `icd_05_reconnaissance.json` | COVERAGE, 4 | Polygon area coverage: risk-subtracted lawnmower + equal chunks per vehicle, routed transit prefix | `camera` + positive `coverage_width_m` per vehicle (adapter injects swaths) |
| `icd_06_route_patrol.json` | COVERAGE, 4 | `road_usage: 1` (legacy `optimalization` normalized) → closed Euler patrol of road edges inside the Polygon | Polygon must contain a non-empty connected road subgraph; no swath needed |
| `icd_07_ballistic_protection.json` | NAVIGATE, 6 | Single protected Point + `minimum_distance: 50` → threat-offset ring; LINE (`formation=2`) flank placed perpendicular to the threat bearing (`_point_objective_placements` LINE branch); LOS + origin metadata | `ballistic_protection` |
| `simple_navigation_themis.json` | NAVIGATE, 1 | Inline Point, `maximize_coverage: false`, strict roads (`road_usage: 1.0`) | Uses seeded map features/graph |
| `parade_coverage_themis.json` | COVERAGE, 1 | `feature_id` workspace polygon → polygon lawnmower with declared `coverage_swath_widths`, `road_usage: 0.4` factor on edge cost | Requires the seeded `MapDB.rma` feature |

## 8. States, Guards, And Failure Handling

- Planner state vocabulary (`planner_states`): `0` initialized, `1` planning,
  `2` planned, `4` failed. `CreatePlanner` returns state `4` on a failed
  mission parse instead of stopping the node (`planner_node.py:811-821`).
- Adapter normalizations (`src/c2_imugs2/api/app.py`):
  `_normalize_rosbridge_event` (line 1205) shapes ROS topics; planner state `4`
  maps to planner status `failed`; `/api/legacy/trace` and
  `/api/planning/diagnostics` replay the Mongo side for debugging.
- A mission stays hidden after `DELETE /forgot`: `forgotten_missions`
  filtering in the SSE loop (`app.py:418-462`) and unknown mission feedback
  from other deployments is never adopted (`app.py:431-435`).
- Empty plans are rejected before state `2`: `solve_mission` raises
  `RuntimeError` when no paths are produced (`multi_robot_path_planning.py:143-144`),
  and the planning timer treats falsy path dictionaries as failure
  (`planner_node.py:272-273`).

## 9. Verify With

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -q tests/test_icd_examples.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -q
```

Key checks: canonicalization/world-independence (`test_all_icd_examples_are_canonicalizable_world_independent_templates`),
preflight vs. capabilities (`test_required_capability_is_checked_before_ros_init`),
swath sourcing (`test_swaths_come_from_active_world_profiles_only_for_area_survey`),
relay infeasibility rejection (`test_original_long_relay_is_rejected_as_mathematically_infeasible`),
and nested-Point repair (`test_legacy_nested_casevac_point_is_repaired_without_changing_other_geometry`).
