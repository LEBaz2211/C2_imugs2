# multi_robot/edge/agent_

ROS service `multi_robot/edge/agent_`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/edge/agent_` |
| Type | `task_msgs/srv/AddTask` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `task_id` |
| request | `uint8` | `task_type` |
| request | `bool` | `override` |
| request | `string<=1048576` | `task_config` |
| request | `string` | `std` |
| response | `string` | `task_id` |
| response | `uint8` | `task_state` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `task_msgs/srv/AddTask` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:339`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L339) |
| calls | `task_msgs/srv/ChangeState` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:340`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L340) |
| calls | `task_msgs/srv/ChangeTaskState` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:339`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L339)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:340`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L340)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341)
