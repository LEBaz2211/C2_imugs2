# /multi_robot/edge/agent_profile

ROS topic `/multi_robot/edge/agent_profile`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/edge/agent_profile` |
| Type | `std_msgs/msg/String` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `data` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `std_msgs/msg/String` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82) |
| subscribes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77)
