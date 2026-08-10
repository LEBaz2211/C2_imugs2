# /multi_robot/swarm_log

ROS topic `/multi_robot/swarm_log`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/swarm_log` |
| Type | `c2_msgs/msg/SwarmLog` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string` | `log` |
| message | `string` | `date` |
| message | `uint8` | `log_type` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:70`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L70) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:70`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L70)
