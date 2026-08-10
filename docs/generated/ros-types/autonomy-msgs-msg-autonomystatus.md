# autonomy_msgs/msg/AutonomyStatus

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyStatus.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
| message | `uint8` | `status` |
| message | `AutonomyPrimitiveStatus[]` | `primitive_statuses` |
| message | `uint8` | `PENDING` |
| message | `uint8` | `ACTIVE` |
| message | `uint8` | `COMPLETED` |
| message | `uint8` | `FAILED` |
| message | `uint8` | `ABORTED` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyStatus.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyStatus.msg#L1)
