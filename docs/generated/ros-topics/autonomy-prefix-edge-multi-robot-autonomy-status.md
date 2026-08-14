# {autonomy_prefix}/edge/multi_robot/autonomy_status

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `{autonomy_prefix}/edge/multi_robot/autonomy_status`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `{autonomy_prefix}/edge/multi_robot/autonomy_status` |
| Type | `autonomy_msgs/msg/AutonomyStatus` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
| message | `uint8` | `status` |
| message | `AutonomyPrimitiveStatus[]` | `primitive_statuses` |
| message | `uint8` | `PENDING` |
| message | `uint8` | `ACTIVE` |
| message | `uint8` | `COMPLETED` |
| message | `uint8` | `FAILED` |
| message | `uint8` | `ABORTED` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `autonomy_msgs/msg/AutonomyStatus` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:47`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L47) |
| subscribes | `autonomy_msgs/msg/AutonomyStatus` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L64) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L64)
- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:47`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L47)
