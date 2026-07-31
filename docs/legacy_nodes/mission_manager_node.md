# `/mission_<mission_id>`

## Purpose

`/mission_<mission_id>` is a dynamic node created by the orchestrator for each mission. It is the real mission state machine: it creates planner jobs, retrieves plans, publishes mission feedback, asks the fleet manager to send tasks, and watches edge feedback for progress/completion.

For mission `11111111-2222-4333-8444-555555555555`, the node name is:

```text
/mission_11111111_2222_4333_8444_555555555555
```

Source:

```text
legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp
legacy_ros/fog/centralized-coordination/src/centralized_coordination/include/centralized_coordination/mission_manager_header.hpp
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `RuntimeDB.MissionConfig` | Mongo collection | Mission JSON loaded at startup |
| `multi_robot/mission_<id>/mission_status_change` | `c2_msgs/srv/ChangeMissionStatus` | Status requests from orchestrator |
| `multi_robot/mission_<id>/environment_change` | `std_srvs/srv/Trigger` | Replan because map/environment changed |
| `multi_robot/mission_<id>/vehicle_change` | `std_srvs/srv/Trigger` | Replan because mission vehicle list changed |
| `/multi_robot/planner/state` | `std_msgs/msg/String` | Planner state JSON |
| `/multi_robot/edge/feedback` | `task_msgs/msg/Feedback` | Agent task progress/completion |

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/planner/create` client | `centralized_msgs/srv/CreatePlanner` | Create planner job |
| `/multi_robot/planner/get_plan` client | `centralized_msgs/srv/GetPlan` | Retrieve task-plan JSON |
| `multi_robot/fleet_manager/get_agents` client | `centralized_msgs/srv/GetAgents` | Get live agent profiles and odometry |
| `multi_robot/fleet_manager/send_tasks` client | `c2_msgs/srv/InitMission` | Ask fleet manager to push tasks to edge |
| `multi_robot/fleet_manager/change_mission_status` client | `c2_msgs/srv/ChangeMissionStatus` | Ask fleet manager to STOP/EXECUTE/PAUSE tasks |
| `/multi_robot/mission_feedback` | `c2_msgs/msg/MissionFeedback` | Runtime mission feedback JSON |
| `/multi_robot/change_mission_status_response` | `c2_msgs/msg/ChangeMissionStatusResponse` | Response to C2 status request |
| `RuntimeDB.Planning` | Mongo collection | Stored planner task JSON |
| `RuntimeDB.MissionFeedback` | Mongo collection | Stored feedback snapshots |

## Internal Behavior

The node has a 50 ms mission state-machine timer, a 1 second planner connection timer, and a 1 second replanning timer.

Main state actions:

| Mission status | Action |
| --- | --- |
| `NONE=0` | Load config, create planner, mark planning needed |
| `PLANNED=1` | Wait for approval |
| `PLANNED_ALTERNATIVE=2` | Mark edge tasks for update |
| `ACCEPTED=4` | Ask fleet manager to send tasks |
| `STARTED=5` | Ask fleet manager to set edge tasks `EXECUTE=1` |
| `PAUSED=6` | Ask fleet manager to set edge tasks `PAUSE=2` |
| `FAILED=7` | Stop edge tasks, then restart state to `NONE` |
| `STOPPED=8` | Stop edge tasks and stop replanning |
| `DELETED=9` | Ask orchestrator to delete mission config |
| `COMPLETED=10` | Stop active feedback tasks |

Planner state values used internally:

```text
-1 not found for this mission, 0 initialized, 1 planning, 2 planned, 3 disconnected, 4 error
```

## Workflow Examples

### 1. Init Mission Becomes A Plan

Loaded mission config:

```json
{
  "mission_id": "11111111-2222-4333-8444-555555555555",
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

Sequence:

```text
1. State NONE calls fleet_manager/get_agents for f9992bb3-...
2. Fleet manager returns Agent with odometry near [4.392588, 50.844317].
3. Mission manager calls /multi_robot/planner/create.
4. Planner publishes state 2 for this mission.
5. Mission manager calls /multi_robot/planner/get_plan.
6. Plan is stored in RuntimeDB.Planning and mission status becomes PLANNED=1.
```

### 2. Approve Then Start Dispatches Edge Tasks

Approve request:

```yaml
service: multi_robot/mission_11111111_2222_4333_8444_555555555555/mission_status_change
mission_request_status: 1
```

Internal result:

```text
APPROVE=1 -> ACCEPTED=4 -> fleet_manager/send_tasks
```

Start request:

```yaml
service: multi_robot/mission_11111111_2222_4333_8444_555555555555/mission_status_change
mission_request_status: 2
```

Internal result:

```text
START=2 -> STARTED=5 -> fleet_manager/change_mission_status with mission_request_status=1
```

Here `mission_request_status=1` is reused as an edge task request state, meaning `EXECUTE`.

### 3. Edge Feedback Updates Mission Feedback

Incoming edge feedback:

```yaml
topic: /multi_robot/edge/feedback
agent_id: f9992bb3-9871-451f-90a0-9207eb9fe6c5
tasks:
  - task_id: 6d2f54a2-a6fd-439a-b5af-a771e53c6e11
    task_state: 1
    current_objective_id: 31f65b58-e010-4838-9b79-cfb31ef8a84f
```

Mission manager behavior:

```text
1. Find matching MissionFeedback task by VehicleId and TaskId.
2. Remove waypoints that are before current_objective_id.
3. If task_state becomes COMPLETED=3 for every planned vehicle, set mission status COMPLETED=10.
4. Publish /multi_robot/mission_feedback once per second.
```

## Gotchas

- The mission manager checks for the literal string `"tasks":[]` to detect empty planning. The planner normally returns an object under `"tasks"`, so an empty object can still be treated as planned.
- Published mission feedback truncates each task to the first 50 remaining waypoints.
- The internal feedback structs keep `TaskId` and `waypoint_id`, but the generated legacy feedback JSON serializer emits `vehicle_id`, `waypoints`, and `est`; it does not emit `task_id` or `waypoint_id`.
- Planner task coordinates are `[lon, lat]`; mission feedback waypoint coordinates are serialized as `[lat, lng]`.
- `/multi_robot/planner/set_agents` is configured as a client, but the active planner node does not expose that service.
- The node assumes the planner state topic is alive; if no matching mission id appears, planner service state becomes `-1` and it tries to create the planner again.
