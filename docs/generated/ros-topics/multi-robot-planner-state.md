# /multi_robot/planner/state

ROS topic `/multi_robot/planner/state`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/planner/state` |
| Type | `std_msgs/msg/String` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `data` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `std_msgs/msg/String` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132) |
| subscribes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65)
- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132)
