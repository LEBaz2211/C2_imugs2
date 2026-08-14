# autonomy_msgs/msg/AutonomyPrimitiveStatus

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyPrimitiveStatus.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `primitive_id` |
| message | `string` | `primitive_type` |
| message | `uint8` | `status` |
| message | `float64` | `progress` |
| message | `string` | `feedback` |
| message | `uint8` | `PENDING` |
| message | `uint8` | `ACTIVE` |
| message | `uint8` | `COMPLETED` |
| message | `uint8` | `FAILED` |
| message | `uint8` | `ABORTED` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyPrimitiveStatus.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyPrimitiveStatus.msg#L1)
