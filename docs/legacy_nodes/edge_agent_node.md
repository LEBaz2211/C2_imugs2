# `/agent_<agent_id>`

> **Documentation label: REFERENCE** — frozen `legacy_ros/` node evidence.

## Purpose

`/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5` is the edge task supervisor for the simulated Themis UGV. It receives task JSON from the fleet manager, translates the current objective into autonomy messages, monitors autonomy feedback, and publishes task feedback back to fog. For the primitive vocabulary used in task JSON, see [primitives.md](primitives.md).

Source:

```text
legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp
legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/include/agent_tasks_supervisor/agent_tasks_supervisor_header.hpp
legacy_ros/config/config_agent-tasks-supervisor.yaml
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `multi_robot/edge/agent_<id>/add_task` | `task_msgs/srv/AddTask` | New task JSON for this agent |
| `multi_robot/edge/agent_<id>/change_state` | `task_msgs/srv/ChangeState` | Activate/inactivate agent |
| `multi_robot/edge/agent_<id>/change_task_state` | `task_msgs/srv/ChangeTaskState` | STOP/EXECUTE/PAUSE/DELETE current task |
| `multi_robot/edge/connection_check` | `std_msgs/msg/String` | Fog heartbeat |
| `Themis_Fr/edge/multi_robot/localization` | `nav_msgs/msg/Odometry` | Autonomy odometry |
| `Themis_Fr/edge/multi_robot/vehicle_profile` | `autonomy_msgs/msg/VehicleProfile` | Autonomy capability/status profile |
| `Themis_Fr/edge/multi_robot/autonomy_status` | `autonomy_msgs/msg/AutonomyStatus` | Objective and primitive status |
| `Themis_Fr/edge/multi_robot/autonomy_trajectory` | `autonomy_msgs/msg/AutonomyTrajectory` | Optional trajectory |

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/edge/agent_profile` | `std_msgs/msg/String` | Agent profile JSON for fleet manager |
| `/multi_robot/edge/feedback` | `task_msgs/msg/Feedback` | Agent state, task state, odometry |
| `multi_robot/edge/node_init` | `std_msgs/msg/String` | Agent id at startup |
| `Themis_Fr/edge/multi_robot/autonomy_set_objective` | `autonomy_msgs/msg/AutonomySetObjective` | Current objective for autonomy |

Current config highlights:

```yaml
fog_connection_timeout: 5
autonomy_connection_timeout: 5
use_start_time: false
objective_distance_tolerance: 3.0
speed_control_mode: 1
edge_only_testing_mode: false
```

## Internal Behavior

The edge node maintains one current task. `AddTask` clears previous primitives/objectives, parses `task_config`, builds a primitive lookup, and builds an ordered list of objectives. `ChangeTaskState` controls whether the current objective is sent to autonomy.

In the current runnable stack, the edge safely executes `waypoint` primitives. It can carry generic primitive types such as `search_mine` and `dispose_mine`, but those require a real autonomy implementation that reports primitive statuses.

Timers:

- every 200 ms: decide whether to send a null objective or active objective,
- every 500 ms: publish `AutonomySetObjective`,
- every 500 ms: calculate required speed,
- every 2 seconds: publish edge feedback and agent profile,
- every 1 second: check fog/autonomy connection counters.

Waypoint completion can be detected by distance to target, autonomy status, or both depending on `waypoint_switching_mode`; current config uses distance tolerance.

## Workflow Examples

### 1. Receive Task From Fleet Manager

Service request:

```yaml
service: multi_robot/edge/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5/add_task
task_id: 6d2f54a2-a6fd-439a-b5af-a771e53c6e11
task_type: 0
override: true
task_config: "{...JSON below...}"
```

Task config:

```json
{
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
```

Response:

```yaml
task_id: 6d2f54a2-a6fd-439a-b5af-a771e53c6e11
task_state: 0
```

### 2. Execute Task And Publish Objective To Autonomy

Service request:

```yaml
service: multi_robot/edge/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5/change_task_state
task_id: 6d2f54a2-a6fd-439a-b5af-a771e53c6e11
task_requested_state: 1
```

Autonomy objective published:

```yaml
topic: Themis_Fr/edge/multi_robot/autonomy_set_objective
null_objective: false
objective:
  id: 31f65b58-e010-4838-9b79-cfb31ef8a84f
  parallel_execution: true
  max_speed: 1.3
  mobility_profile: 0
  primitives:
    - "{\"id\":\"c8cab10d-a718-42be-b6ac-4eb496f03d6d\",\"type\":\"waypoint\",\"continuous\":false,\"primitive_inputs\":[],\"primitive_outputs\":[],\"parameters\":{\"coordinates\":[4.392430,50.844050],\"speed\":1.3,\"max_speed\":1.3,\"mobility_profile\":0,\"wait_time\":0}}"
```

### 3. Publish Progress Back To Fog

Feedback published while active:

```yaml
topic: /multi_robot/edge/feedback
agent_id: f9992bb3-9871-451f-90a0-9207eb9fe6c5
state: 1
tasks:
  - task_id: 6d2f54a2-a6fd-439a-b5af-a771e53c6e11
    task_state: 1
    current_objective_id: 31f65b58-e010-4838-9b79-cfb31ef8a84f
odometry:
  header:
    frame_id: map
  pose:
    pose:
      position:
        x: 4.392500
        y: 50.844150
```

When the final objective completes, `task_state` becomes `3`, and the mission manager can mark the mission complete if all planned agents are done.

## Gotchas

- The node publishes a null objective unless the task state is `STARTED=1`, fog is connected, autonomy is connected, and start-time conditions pass.
- The task JSON parser expects `primitives` and `objectives` arrays. Missing keys will usually fail hard.
- Non-`waypoint` primitive types are not enough by themselves; autonomy must understand them and publish matching `AutonomyPrimitiveStatus` updates.
- In map/global mode, waypoint coordinates are interpreted as `[lon, lat]`, while odometry uses `x=lon`, `y=lat`.
- The edge publishes only one current task in feedback.
