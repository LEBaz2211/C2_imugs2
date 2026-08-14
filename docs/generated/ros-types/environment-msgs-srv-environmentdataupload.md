# environment_msgs/srv/EnvironmentDataUpload

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `environment_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataUpload.srv` |
| Package | `environment_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `request_id` |
| request | `uint32` | `version_nr` |
| request | `string<=10000` | `insert_geojson` |
| request | `string<=10000` | `update_geojson` |
| request | `string<=5000` | `delete_json` |
| response | `unique_identifier_msgs/UUID` | `request_id` |
| response | `uint8` | `result_status` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataUpload.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/environment_msgs/srv/EnvironmentDataUpload.srv#L1)
