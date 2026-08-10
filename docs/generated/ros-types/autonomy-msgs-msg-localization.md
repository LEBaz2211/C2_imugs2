# autonomy_msgs/msg/Localization

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/Localization.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `std_msgs/Header` | `header` |
| message | `geographic_msgs/GeoPoint` | `position` |
| message | `geometry_msgs/Quaternion` | `orientation` |
| message | `float64[36]` | `covariance` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/Localization.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/Localization.msg#L1)
