# autonomy_msgs/msg/VehicleInfo

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleInfo.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `vehicle_type` |
| message | `uint8` | `fuel_status_pct` |
| message | `float32` | `fuel_hours` |
| message | `uint8` | `battery_status_pct` |
| message | `float32` | `battery_hours` |
| message | `SensorProperties[]` | `sensor_list` |
| message | `float32[]` | `vehicle_dimensions` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleInfo.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/VehicleInfo.msg#L1)
