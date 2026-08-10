# /multi_robot/environment_data_get_version_response

ROS topic `/multi_robot/environment_data_get_version_response`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/environment_data_get_version_response` |
| Type | `environment_msgs/msg/EnvironmentDataGetVersionResponse` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `request_id` |
| message | `uint32` | `version_nr` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `environment_msgs/msg/EnvironmentDataGetVersionResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:68`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L68) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:68`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L68)
