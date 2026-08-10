# autonomy_msgs/msg/SwarmingStatus

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingStatus.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `autonomy_objective_id` |
| message | `uint8` | `status` |
| message | `uint32` | `time_to_arrival` |
| message | `uint32` | `distance_to_arrival` |
| message | `float32` | `needed_energy_to_arrival` |
| message | `string<=2000` | `blockages` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingStatus.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingStatus.msg#L1)
