# environment_msgs/msg/EnvironmentDataUploadRequest

MSG definition from `environment_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadRequest.msg` |
| Package | `environment_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `request_id` |
| message | `uint32` | `version_nr` |
| message | `string<=10000` | `insert_geojson` |
| message | `string<=10000` | `update_geojson` |
| message | `string<=5000` | `delete_json` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/msg/EnvironmentDataUploadRequest.msg#L1)
