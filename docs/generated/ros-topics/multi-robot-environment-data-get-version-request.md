# /multi_robot/environment_data_get_version_request

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/environment_data_get_version_request`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/environment_data_get_version_request` |
| Type | `environment_msgs/msg/EnvironmentDataGetVersionRequest` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `request_id` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| subscribes | `environment_msgs/msg/EnvironmentDataGetVersionRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L67) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L67)
