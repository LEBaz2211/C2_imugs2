# `/autonomy_test_node_Themis_Fr`

> **Documentation label: REFERENCE** — frozen `legacy_ros/` node evidence.

## Purpose

`/autonomy_test_node_Themis_Fr` is the simple autonomy simulator launched with the edge supervisor. It receives the edge's current objective, moves its odometry toward the first waypoint primitive, and publishes vehicle profile plus autonomy status.

Source:

```text
legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp
legacy_ros/config/config_autonomy.yaml
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `Themis_Fr/edge/multi_robot/autonomy_set_objective` | `autonomy_msgs/msg/AutonomySetObjective` | Current edge objective or null objective |

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| `Themis_Fr/edge/multi_robot/localization` | `nav_msgs/msg/Odometry` | Simulated robot pose |
| `Themis_Fr/edge/multi_robot/autonomy_status` | `autonomy_msgs/msg/AutonomyStatus` | Active/completed objective state |
| `Themis_Fr/edge/multi_robot/vehicle_profile` | `autonomy_msgs/msg/VehicleProfile` | Simulated vehicle capabilities |

Current Themis config:

```yaml
vehicle_type: ugv
start_location: [4.392588, 50.844317]
coordinate_mode: 0
max_speed: 4.5
max_acceleration: 8.0
fuel_status_pct: 85.0
battery_status_pct: 90.0
vehicle_dimensions: [0.9, 0.6, 0.55]
sensors: [lidar, camera, gpr]
```

`coordinate_mode: 0` means global map coordinates. The simulator treats odometry `x` as longitude and `y` as latitude.

## Internal Behavior

The simulator:

1. initializes odometry from `start_location`,
2. publishes odometry every 500 ms,
3. publishes vehicle profile and autonomy status every 1000 ms,
4. runs motion control every 100 ms,
5. when a non-null objective arrives, parses waypoint primitive JSON and sets `_current_arrival_point`,
6. moves toward that point at `objective.max_speed`,
7. sets autonomy status `COMPLETED=2` once within objective distance tolerance.

## Workflow Examples

### 1. Startup Vehicle Profile

Published profile:

```yaml
topic: Themis_Fr/edge/multi_robot/vehicle_profile
active_autonomy_mode: 1
vehicle_constraints:
  max_speed:
    linear:
      x: 4.5
  max_acceleration:
    linear:
      x: 8.0
  max_weight: 16.0
  max_tilt_angle: 1.8
vehicle_info:
  vehicle_type: ugv
  fuel_status_pct: 85
  fuel_hours: 1.5
  battery_status_pct: 90
  battery_hours: 3.0
  vehicle_dimensions: [0.9, 0.6, 0.55]
```

The edge supervisor converts this into JSON and republishes it on `/multi_robot/edge/agent_profile`.

### 2. Receive A Waypoint Objective

Incoming objective:

```yaml
topic: Themis_Fr/edge/multi_robot/autonomy_set_objective
null_objective: false
objective:
  id: 31f65b58-e010-4838-9b79-cfb31ef8a84f
  max_speed: 1.3
  primitives:
    - "{\"id\":\"c8cab10d-a718-42be-b6ac-4eb496f03d6d\",\"type\":\"waypoint\",\"parameters\":{\"coordinates\":[4.392430,50.844050]}}"
```

Internal target:

```text
_current_arrival_point = [4.392430, 50.844050]
_null_objective = false
```

Motion loop:

```text
every 100 ms:
  long_dist = 4.392430 - odom.x
  lat_dist = 50.844050 - odom.y
  travel_dist = (0.00000901 * max_speed) * 0.1
  odom.x += d_long
  odom.y += d_lat
```

### 3. Objective Completion

Published status near target:

```yaml
topic: Themis_Fr/edge/multi_robot/autonomy_status
status: 2
primitive_statuses: []
```

The edge supervisor also checks its own distance to the waypoint. With current config, being within `3.0` meters is enough to complete the waypoint even when primitive statuses are sparse.

## Gotchas

- This is a basic simulator, not a vehicle dynamics model.
- In global coordinate mode it uses approximate degrees-to-meters math.
- The current primitive parser breaks after finding waypoint coordinates, so `primitive_statuses` can be empty even when overall autonomy status changes.
- It only targets the first waypoint primitive found in the current objective.
- It does not implement legacy example primitives such as `search_mine` or `dispose_mine`.
