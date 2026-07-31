# `/planner_node`

## Purpose

`/planner_node` is the legacy path planner. It loads the RMA map, receives live agent positions from the fleet manager, accepts mission configs through services, computes paths, and returns task-plan JSON that the edge supervisor can execute.

Source:

```text
legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py
legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py
legacy_ros/config/config_planner.yaml
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/planner/create` | `centralized_msgs/srv/CreatePlanner` | Create/update mission planning job |
| `/multi_robot/planner/get_plan` | `centralized_msgs/srv/GetPlan` | Return latest calculated plan |
| `/multi_robot/planner/delete_planner` | `centralized_msgs/srv/DeletePlanner` | Acknowledge planner deletion |
| `/multi_robot/planner/agent` | `centralized_msgs/msg/Agent` | Live agent profile and odometry |
| Local map folder | GeoJSON files | Roads, free polygons, risk polygons, geofences/workspaces |
| OSMnx graph | OSM network | Road graph around map centroid |

Current config highlights:

```yaml
mapf: independent_agents
map_radius: 180.0
map_folder: /data/map/rma
load_map_from_local_folder: true
line_graph_connect_max_distance: 45.0
poly_graph_connect_max_distance: 45.0
merge_nodes: true
merge_nodes_max_distance: 1.0
```

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/planner/state` | `std_msgs/msg/String` | JSON with planner state per mission |
| `/multi_robot/planner/graph_image` | `sensor_msgs/msg/CompressedImage` | Debug graph/path image |
| `/multi_robot/planner/get_plan` response | JSON string | Mission task-plan JSON |

Planner state JSON:

```json
{
  "planners": [
    {
      "mission_id": "11111111-2222-4333-8444-555555555555",
      "state": 2
    }
  ]
}
```

State values used by this node:

```text
0 initialized, 1 planning, 2 planned
```

## Internal Behavior

Startup builds a routable graph from:

- local free road LineStrings,
- free/workspace polygons converted into candidate graph nodes,
- risk polygons that mark graph edges as risky,
- an OSMnx graph around the map centroid.

`/multi_robot/planner/agent` messages are converted into internal `Buddy` objects:

```text
agent_id = msg.agent_id
localization = [msg.odometry.pose.pose.position.x, msg.odometry.pose.pose.position.y]
current_speed = msg.odometry.twist.twist.linear.x
```

`CreatePlanner` stores the mission JSON, marks planner state `0`, and sets `mission_defined=true`. The 1 second planning timer then:

1. filters live agents to those listed in `mission["vehicles"]`,
2. sets each selected agent's nominal speed from `transit.desired_vehicle_constraints.max_speed`,
3. calls `MultiRobotPathPlanning.solve_mission()`,
4. caches `self.paths`,
5. publishes state `2`.

`GetPlan` converts cached paths into one task per agent. Each waypoint becomes one objective containing a `waypoint` primitive. See [primitives.md](primitives.md) for the task primitive vocabulary.

## Planning Shapes

### 1. Single Robot Point Navigation

Required input:

```json
{
  "behavior": 0,
  "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
  "objective": {
    "geometries": [
      {
        "geometry": {
          "geometry_type": "Point",
          "coordinates": [4.392430, 50.844050]
        }
      }
    ]
  },
  "transit": {
    "desired_vehicle_constraints": {"max_speed": 1.3},
    "optimalization": {"road_usage": 1.0}
  }
}
```

Also required:

```yaml
topic: /multi_robot/planner/agent
agent_id: f9992bb3-9871-451f-90a0-9207eb9fe6c5
odometry.pose.pose.position.x: 4.392588
odometry.pose.pose.position.y: 50.844317
```

Output plan shape:

```json
{
  "mission_id": "11111111-2222-4333-8444-555555555555",
  "tasks": {
    "f9992bb3-9871-451f-90a0-9207eb9fe6c5": {
      "task_id": "6d2f54a2-a6fd-439a-b5af-a771e53c6e11",
      "primitives": [
        {
          "primitive_id": "c8cab10d-a718-42be-b6ac-4eb496f03d6d",
          "primitive_type": "waypoint",
          "continuous": false,
          "primitive_inputs": [],
          "primitive_outputs": [],
          "completion": {
            "ends_objective": true,
            "ends_task": false,
            "followed_by_primitives": [],
            "inherit_other_primitives": false,
            "resume_after": false
          }
        }
      ],
      "objectives": [
        {
          "objective_id": "31f65b58-e010-4838-9b79-cfb31ef8a84f",
          "objective_type": "combined_primitives",
          "parallel_execution": true,
          "primitives": [
            {
              "primitive_id": "c8cab10d-a718-42be-b6ac-4eb496f03d6d",
              "parameters": {
                "coordinates": [4.392430, 50.844050],
                "speed": 1.3,
                "max_speed": 1.3,
                "mobility_profile": 0,
                "wait_time": 0
              }
            }
          ]
        }
      ]
    }
  }
}
```

### 2. Multiple Robots Or Multiple Points

Required mission shape:

```json
{
  "behavior": 0,
  "vehicles": [
    "E1C4B33F-6639-4321-A8EF-26ADC046AD8B",
    "DC128E74-7C68-4ED3-9AF1-4A8189D4E217"
  ],
  "objective": {
    "geometries": [
      {
        "geometry": {
          "geometry_type": "MultiPoint",
          "coordinates": [
            [4.392430, 50.844050],
            [4.391900, 50.843970],
            [4.393050, 50.844280]
          ]
        }
      }
    ]
  },
  "transit": {
    "desired_vehicle_constraints": {"max_speed": 1.0},
    "optimalization": {"road_usage": 1.0}
  }
}
```

Runtime requirement:

```text
Every listed vehicle that should be planned must have a recent /multi_robot/planner/agent message.
The current compose stack launches one live Themis agent; this multi-agent shape needs additional edge agents.
```

Planner behavior:

- if points <= vehicles, use Hungarian assignment,
- if points > vehicles, use multi-traveling-salesman allocation,
- with `mapf: independent_agents`, plan each assigned route independently.

Output shape:

```json
{
  "tasks": {
    "E1C4B33F-6639-4321-A8EF-26ADC046AD8B": {"task_id": "...", "objectives": ["waypoint objectives..."]},
    "DC128E74-7C68-4ED3-9AF1-4A8189D4E217": {"task_id": "...", "objectives": ["waypoint objectives..."]}
  }
}
```

### 3. Sweeping Or Coverage Zone

Required mission shape:

```json
{
  "behavior": 1,
  "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
  "objective": {
    "geometries": [
      {
        "geometry": {
          "geometry_type": "Polygon",
          "coordinates": [
            [
              [4.391820, 50.844000],
              [4.392720, 50.844000],
              [4.392720, 50.844540],
              [4.391820, 50.844540],
              [4.391820, 50.844000]
            ]
          ]
        }
      }
    ],
    "maximize_coverage": true
  },
  "transit": {
    "desired_vehicle_constraints": {"max_speed": 1.0},
    "optimalization": {"road_usage": 0.5}
  }
}
```

Planner behavior:

```text
1. Find graph nodes inside the polygon.
2. Select coverage points with MaximizeCoverage.
3. For one robot, find the first reachable non-risk coverage point and path to it.
4. For multiple robots, allocate selected coverage points to the live agents.
```

For the current single-agent sim, coverage is not a full lawnmower sweep. It is legacy "choose reachable coverage goal(s)" behavior, then edge executes waypoint objectives.

## Gotchas

- If no matching live agent has reached `/multi_robot/planner/agent`, planning logs a warning and does not finish.
- `GetPlan` returns cached `self.paths`; this planner behaves like a single active planning job, not a robust multi-job planner.
- The current planner emits only `waypoint` primitives. Legacy examples contain `search_mine` and `dispose_mine`, but this planner does not generate them.
- The planner exposes `/multi_robot/planner/delete_planner`, while older orchestrator code points at `multi_robot/planner/delete`.
- The mission manager configures `/multi_robot/planner/set_agents`, but this active planner node does not create that service.
- If an objective uses an unknown `feature_id`, the planner may produce empty tasks while upstream still marks the mission as planned.
- `road_usage` is read from `transit.optimization.road_usage` or legacy `transit.optimalization.road_usage`; values above `1.0` are treated as percentages.
