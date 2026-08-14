# /multi_robot/environment_data_upload_request

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/environment_data_upload_request`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/environment_data_upload_request` |
| Type | `environment_msgs/msg/EnvironmentDataUploadRequest` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `request_id` |
| message | `uint32` | `version_nr` |
| message | `string<=10000` | `insert_geojson` |
| message | `string<=10000` | `update_geojson` |
| message | `string<=5000` | `delete_json` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| subscribes | `environment_msgs/msg/EnvironmentDataUploadRequest` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L65) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp#L65)
