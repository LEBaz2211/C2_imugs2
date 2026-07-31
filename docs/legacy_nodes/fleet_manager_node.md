# `/fleet_manager_node`

## Purpose

`/fleet_manager_node` is the fog-side registry and dispatcher for agents. It learns which edge agents are alive, exposes them to mission managers and the planner, sends task JSON to edge agents, and forwards edge odometry to the planner.

Source:

```text
legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp
legacy_ros/fog/centralized-coordination/src/centralized_coordination/include/centralized_coordination/fleet_manager_header.hpp
legacy_ros/config/config_centralized_coordination.yaml
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/edge/agent_profile` | `std_msgs/msg/String` | Agent profile JSON from edge |
| `/multi_robot/edge/feedback` | `task_msgs/msg/Feedback` | Agent odometry and task progress |
| `multi_robot/fleet_manager/get_agents` | `centralized_msgs/srv/GetAgents` | Mission manager asks for selected agents |
| `multi_robot/fleet_manager/send_tasks` | `c2_msgs/srv/InitMission` | Mission manager asks to send stored plan to edge |
| `multi_robot/fleet_manager/change_mission_status` | `c2_msgs/srv/ChangeMissionStatus` | Mission manager asks to change edge task state |

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/planner/agent` | `centralized_msgs/msg/Agent` | Live agent data for planner |
| `multi_robot/edge/connection_check` | `std_msgs/msg/String` | Fog heartbeat to edge |
| `multi_robot/edge/agent_<id>/add_task` client | `task_msgs/srv/AddTask` | Send one task JSON to one edge agent |
| `multi_robot/edge/agent_<id>/change_task_state` client | `task_msgs/srv/ChangeTaskState` | STOP/EXECUTE/PAUSE/DELETE edge task |
| `VehicleDB.Vehicles` | Mongo collection | Last known agent profile |
| `RuntimeDB.ConnectedVehicles` | Mongo collection | Currently connected agents |

## Internal Behavior

When an agent profile arrives, the fleet manager registers the agent, creates service clients to that edge node, stores the profile in MongoDB, and resets its disconnection counter.

When edge feedback arrives, it updates the agent's odometry and current task, then publishes `centralized_msgs/msg/Agent` to `/multi_robot/planner/agent`. This is how the planner gets current robot positions.

When asked to send tasks, it loads `RuntimeDB.Planning[mission_id]`, extracts each agent task, and calls that edge agent's `add_task` service.

Config defaults from the current compose stack:

```yaml
use_high_level_collision_avoidance: true
vicinity_radius: 30.0
tolerance_distance: 15.0
max_deceleration_factor: 0.10
```

Most high-level collision avoidance code is currently commented out.

## Workflow Examples

### 1. Register Themis From Edge Profile

Incoming profile:

```json
{
  "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
  "vehicle_constraints": {
    "max_speed": {"linear": {"x": 4.5, "y": 0.0, "z": 0.0}},
    "max_acceleration": {"linear": {"x": 8.0, "y": 0.0, "z": 0.0}},
    "max_weight": 3.141,
    "max_tilt_angle": 3.141
  },
  "vehicle_info": {
    "fuel_status_pct": 85,
    "battery_status_pct": 90,
    "vehicle_dimensions": {"length": 0.9, "width": 0.6, "height": 0.55}
  }
}
```

Created edge clients:

```text
multi_robot/edge/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5/add_task
multi_robot/edge/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5/change_state
multi_robot/edge/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5/change_task_state
```

### 2. Mission Manager Requests Agents For Planning

Service request:

```yaml
service: multi_robot/fleet_manager/get_agents
agent_id_list:
  - f9992bb3-9871-451f-90a0-9207eb9fe6c5
```

Response:

```yaml
agents:
  - agent_id: f9992bb3-9871-451f-90a0-9207eb9fe6c5
    agent_profile: "{...profile JSON...}"
    odometry:
      header:
        frame_id: map
      pose:
        pose:
          position:
            x: 4.392588
            y: 50.844317
error_message: ok
```

### 3. Send Planned Task To Edge

Planning record loaded from `RuntimeDB.Planning`:

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

Edge service request:

```yaml
service: multi_robot/edge/agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5/add_task
task_id: 6d2f54a2-a6fd-439a-b5af-a771e53c6e11
task_type: 0
override: true
task_config: "{...the agent task JSON above...}"
```

## Gotchas

- `multi_robot/fleet_manager/change_mission_status` reuses `c2_msgs/srv/ChangeMissionStatus`, but the status field means edge task request state, not mission status.
- The planner receives an agent only after both profile and feedback have been processed.
- Registering a new agent waits for its edge services. If an edge service is missing, the fleet manager can block while waiting.
- The active collision avoidance code path is mostly commented; do not assume it is protecting moving robots.

