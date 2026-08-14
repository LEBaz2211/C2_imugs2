# /multi_robot/environment_data_reset_response

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/environment_data_reset_response`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/environment_data_reset_response` |
| Type | `environment_msgs/msg/EnvironmentDataResetResponse` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `request_id` |
| message | `uint8` | `result_status` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `environment_msgs/msg/EnvironmentDataResetResponse` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L64) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L64)
