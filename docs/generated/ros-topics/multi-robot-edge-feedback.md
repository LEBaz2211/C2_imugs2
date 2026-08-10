# /multi_robot/edge/feedback

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

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L78)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:96`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L96)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:74`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L74)
