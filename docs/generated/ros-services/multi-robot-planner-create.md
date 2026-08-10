# /multi_robot/planner/create

ROS service `/multi_robot/planner/create`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `/multi_robot/planner/create` |
| Type | `centralized_msgs/srv/CreatePlanner` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `id` |
| request | `uint8` | `priority` |
| request | `Agent[]` | `agents` |
| request | `string` | `config` |
| response | `string` | `id` |
| response | `uint8` | `state` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `centralized_msgs/srv/CreatePlanner` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:56`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L56) |
| provides | `centralized_msgs/srv/CreatePlanner` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:141`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L141) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:56`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L56)
- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:141`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L141)
