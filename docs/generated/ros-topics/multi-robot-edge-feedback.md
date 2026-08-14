# /multi_robot/edge/feedback

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/edge/feedback`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/edge/feedback` |
| Type | `task_msgs/msg/Feedback` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `agent_id` |
| message | `uint8` | `state` |
| message | `TaskFeedback[]` | `tasks` |
| message | `nav_msgs/Odometry` | `odometry` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `task_msgs/msg/Feedback` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L78) |
| subscribes | `task_msgs/msg/Feedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:74`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L74) |
| subscribes | `task_msgs/msg/Feedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:96`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L96) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Themis reports completion after the final waypoint

!!! success "Verified Flow"
    Phase: COMPLETED.

```json
{
  "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
  "state": 1,
  "tasks": [
    {
      "task_id": "<generated-task-uuid>",
      "task_state": 3,
      "current_objective_id": "<final-generated-objective-uuid>"
    }
  ],
  "odometry": {
    "pose": {
      "pose": {
        "position": {
          "x": 4.391670213379427,
          "y": 50.84417059346137,
          "z": 0.0
        }
      }
    }
  }
}
```

- Task state 3 is COMPLETED. The mission manager then transitions the one-robot mission to COMPLETED(10).

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:918`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L918)

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L78)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:96`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L96)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:74`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L74)
