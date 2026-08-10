# /multi_robot/environment_data_reset_request

ROS topic `/multi_robot/environment_data_reset_request`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/environment_data_reset_request` |
| Type | `environment_msgs/msg/EnvironmentDataResetRequest` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `request_id` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| subscribes | `environment_msgs/msg/EnvironmentDataResetRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:63`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L63) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:63`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L63)
