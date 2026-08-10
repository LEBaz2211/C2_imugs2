# /multi_robot/mission_feedback

ROS topic `/multi_robot/mission_feedback`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/mission_feedback` |
| Type | `c2_msgs/msg/MissionFeedback` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string` | `mission_feedback` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/MissionFeedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L71) |
| publishes | `c2_msgs/msg/MissionFeedback` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:133`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L133) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:133`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L133)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L71)
