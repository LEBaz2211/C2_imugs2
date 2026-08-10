# autonomy_msgs/msg/AutonomyObjective

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyObjective.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `id` |
| message | `string<=100` | `objective_type` |
| message | `bool` | `parallel_execution` |
| message | `string[]` | `primitives` |
| message | `float32` | `max_speed` |
| message | `uint8` | `mobility_profile` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomyObjective.msg#L1)
