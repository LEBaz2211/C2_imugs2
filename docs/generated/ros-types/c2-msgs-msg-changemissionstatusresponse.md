# c2_msgs/msg/ChangeMissionStatusResponse

MSG definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `uint8` | `mission_status` |
| message | `string<=2000` | `error_message` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg#L1)
