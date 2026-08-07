# `/planner_node`

## Purpose

`/planner_node` is the legacy ROS boundary around map loading, mission
interpretation, route calculation, planner state, and task-plan JSON. This page
describes the `multi-agent-framework` revision `b154575f5a5f` baseline plus the
small compatibility patches deployed in `legacy_ros/`, not the separately
editable `backend/` fork.

The node still plans from `MapDB.rma`. The local compose stack now seeds its
three valid baseline features idempotently before starting the planner, and
`CreatePlanner` can initialize the graph lazily if the three-second poll has not
finished.

Source:

- [`planner_node.py`](../../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py)
- [`multi_robot_path_planning.py`](../../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py)
- [`mapf.py`](../../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/mapf.py)
- [`graph.py`](../../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/graph.py)
- [`config_planner.yaml`](../../legacy_ros/config/config_planner.yaml)
- [`seed-mapdb.js`](../../legacy_ros/docker/seed-mapdb.js)

For the complete REST-to-robot path with exact line links, see the
[true legacy single-robot walkthrough](../LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md).

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/planner/create` | `centralized_msgs/srv/CreatePlanner` | Store one mission config and start planning |
| `/multi_robot/planner/get_plan` | `centralized_msgs/srv/GetPlan` | Serialize the node's current global path cache |
| `/multi_robot/planner/delete_planner` | `centralized_msgs/srv/DeletePlanner` | Return success; no planner state is actually deleted |
| `/multi_robot/planner/agent` | `centralized_msgs/msg/Agent` | Cache a robot's latest global pose and speed |
| `MapDB.rma` | MongoDB GeoJSON documents | Roads, workspace/geofence polygons, risks, and referenced features |
| OSMnx | Downloaded road graph | Network around the database-feature centroid |

The deployed Single-Robotnik configuration is:

```yaml
mapf: independent_agents
map_radius: 60.0
map_folder: /data/map/rma
load_map_from_database: true
load_map_from_local_folder: false
mongodb_url: mongodb://localhost:27017/
map_feature_collection: rma
line_graph_connect_max_distance: 25.0
poly_graph_connect_max_distance: 25.0
merge_nodes: true
merge_nodes_max_distance: 1.0
```

The Python implementation declares the database/local-folder flags but does not
branch on them. Its active initializer always reads MongoDB.

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/planner/state` | `std_msgs/msg/String` | JSON planner states keyed by mission ID |
| `/multi_robot/planner/graph_image` | `sensor_msgs/msg/CompressedImage` | Latest debug graph or route image |
| `/multi_robot/planner/get_plan` response | JSON string | Current paths converted to robot task JSON |

Planner state values emitted by the deployed node are:

```text
0 initialized, 1 planning, 2 planned, 4 planning/create failure
```

State `2` now follows a non-empty path result. If no matching robot has reported
yet, the timer remains in state `1` and waits instead of publishing an empty
plan.

## Actual Startup And Readiness

Compose first runs an idempotent seed service. It flattens FeatureCollections,
upserts the road, geofence, and risk documents by `properties.feature_id`,
preserves unrelated rows, and skips the malformed RMA virtual-geofence file.
The planner depends on successful seed completion:

- [`docker-compose.legacy-ros.yml`, L17-L37](../../docker-compose.legacy-ros.yml#L17-L37)
- [`docker-compose.legacy-ros.yml`, L75-L93](../../docker-compose.legacy-ros.yml#L75-L93)
- [`seed-mapdb.js`, L71-L144](../../legacy_ros/docker/seed-mapdb.js#L71-L144)

The upstream constructor behavior remains: it connects to `MapDB`, remembers a
count of zero, and leaves direct initialization commented out. Every three
seconds, `watch_db_changes()` compares the collection count with that value.

```text
seeded count is nonzero or later changes
  -> initialize_map()
  -> read road/workspace/geofence/risk features from MongoDB
  -> download and combine the OSMnx graph
  -> weight graph edges that intersect risks
  -> create MultiRobotPathPlanning

CreatePlanner arrives before the poll finishes
  -> _ensure_map_ready() performs the same initialization synchronously
  -> success accepts the mission
  -> failure returns state 4 without terminating /planner_node
```

This behavior is implemented in
[`watch_db_changes()`](../../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L165-L176)
and
[`initialize_map()`](../../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L459-L577).
The local readiness boundary is
[`set_mission_service_callback()`](../../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L290-L322)
plus
[`_ensure_map_ready()`](../../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L694-L711).

The seeded local graph's nearest measured gap to the current OSM component is
`21.45 m`. Upstream's `15 m` connection threshold leaves those components
disconnected, so the deployed configuration uses `25 m`
([`config_planner.yaml`, L7-L11](../../legacy_ros/config/config_planner.yaml#L7-L11)).
This changes graph connectivity, not any ROS or JSON contract.

## Mission And Agent Handling

`/multi_robot/planner/agent` messages become cached `Buddy` objects:

```text
agent_id = msg.agent_id
localization = [odometry.position.x, odometry.position.y]
current_speed = odometry.twist.linear.x
```

`CreatePlanner` receives both config and agent fields, but the callback ignores
the request's agent list. Planning later uses only the independent topic cache.
With an initialized graph, the callback:

1. parses and stores the mission;
2. assigns the new current mission ID;
3. writes state `0` under that mission ID;
4. sets `mission_defined=true`.

The one-second planning timer then repeatedly:

1. filters cached robots by `mission["vehicles"]` and waits if none match;
2. assigns `transit.desired_vehicle_constraints.max_speed`;
3. calls `solve_mission()` while holding a context-managed path lock;
4. writes state `2` only for non-empty paths and replaces the global path cache;
5. catches solver failures, clears the shared path cache, writes state `4`, and
   stops repeating that failed mission without killing the node.

`mission_defined` is not cleared after success, so the same mission is
recalculated every second. The global mission ID/path cache also makes concurrent
missions unsafe. The patched callback is
[`planning_timer_callback()`, L221-L287](../../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L221-L287).

## Single-Robot Point Navigation

Through the normal REST/C++ path, the mission can enter with a flat GeoJSON
Point. The C++ mission serializer normalizes it to a one-item coordinate array
before Planner receives it:

```json
{
  "behavior": 0,
  "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
  "objective": {
    "geometries": [{
      "geometry": {
        "geometry_type": "Point",
        "coordinates": [[4.392430, 50.844050]]
      }
    }]
  },
  "transit": {
    "desired_vehicle_constraints": {"max_speed": 1.3},
    "optimalization": {"road_usage": 1.0}
  }
}
```

The nested form matters for a direct Planner call because the baseline-derived
Python code does only `points.append(coordinates[0])`.

For one cached robot and one point:

1. Hungarian allocation assigns the point to the robot.
2. AStar snaps both the live pose and destination to nearest graph nodes.
3. Normal edge length is the cost; a risk edge costs 100 times its length.
4. The returned path contains graph-node coordinates only.

`road_usage` is retained in the mission contract but never read by this planner.
Risk is expensive rather than forbidden, and the exact start/destination are not
appended after graph snapping. Local free-road LineStrings are now explicitly
bidirectional
([`generate_graph_from_linestring()`, L184-L227](../../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/graph.py#L184-L227));
upstream created only the forward edges.

If AStar finds no route, its local compatibility patch returns the stable tuple
`(None, inf)` instead of the upstream scalar `False`
([`AStar.search()`, L71-L127](../../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/mapf.py#L71-L127)).
The solver converts that into an explicit `RuntimeError`
([`_search_route()`, L182-L197](../../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py#L182-L197)),
and the planning timer publishes state `4` while keeping `/planner_node` alive.

`GetPlan` turns every path coordinate into one waypoint objective:

```jsonc
{
  "mission_id": "11111111-2222-4333-8444-555555555555",
  "tasks": {
    "f9992bb3-9871-451f-90a0-9207eb9fe6c5": {
      "task_id": "<new UUID>",
      "primitives": [{
        "primitive_id": "<new UUID>",
        "primitive_type": "waypoint"
      }],
      "objectives": [{
        "objective_id": "<new UUID>",
        "primitives": [{
          "primitive_id": "<same primitive UUID>",
          "parameters": {
            "coordinates": [4.39245, 50.84408],
            "speed": 1.3,
            "max_speed": 1.3
          }
        }]
      }]
    }
  }
}
```

The coordinate shown is illustrative: the real value is the graph node nearest
the requested destination. Every `GetPlan` call generates fresh task, primitive,
and objective UUIDs even if `self.paths` has not changed.

## Multi-Robot And Coverage Limits

- With points no greater than vehicle count, Hungarian allocation and
  `independent_agents` calculate one AStar route per assigned cached robot.
- With more points than vehicles, the code enters `solve_mtsp()`, but that
  function indexes the agent list with string robot IDs and currently raises.
- Behavior `1` calls an undefined `coverage_algorithm` and currently raises.
- Behavior `0` with polygon/line objectives has a separate maximum-coverage
  point-selection branch, but it still depends on a valid graph and cached
  robots and is not a complete lawnmower sweep.
- A missing database `feature_id` is not converted to inline geometry; later
  mission interpretation fails when it expects a `geometry` object.
- CBS code exists, but the deployed config uses `independent_agents` and the
  current multi-mission/global-cache design is not safe orchestration.

## Operational Gotchas

- The compose seed is baseline-only and idempotent: it preserves unrelated
  `MapDB.rma` rows. The planner's watcher still compares document count only, so
  replacing geometry without changing the count does not automatically reload
  a running graph.
- No cached matching robot now waits in state `1`; it is still important to
  verify `/multi_robot/planner/agent` when planning appears stalled.
- MissionManager's legacy empty-task check looks for literal `"tasks":[]`, so
  a direct premature `GetPlan` response containing `"tasks": {}` is still not
  recognized as empty.
- Planner deletion only acknowledges the service request.
- The planner exposes `/multi_robot/planner/delete_planner`, while older
  orchestrator code points at `multi_robot/planner/delete`.
- MissionManager configures `/multi_robot/planner/set_agents`, but this node does
  not create that service.
- The node emits only `waypoint` primitives; it does not generate legacy
  `search_mine` or `dispose_mine` primitives.

## Live Validation

The rebuilt stack was tested through its real ROS services. The exact Themis
mission for `f9992bb3-9871-451f-90a0-9207eb9fe6c5` reached planner state `2` and
returned one task with `10` waypoint objectives. A deliberately unreachable
route reached planner state `4`; `/planner_node` stayed running and remained
available for subsequent requests.
