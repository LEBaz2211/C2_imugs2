# c2_msgs/srv/ChangeMissionStatus

SRV definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `uint8` | `mission_request_status` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `uint8` | `mission_status` |
| response | `string<=2000` | `error_message` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv#L1)
