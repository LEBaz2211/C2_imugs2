# c2_msgs/srv/InitMission

SRV definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/InitMission.srv` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `string<=10000` | `mission_config` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `string<=10000` | `mission_feedback` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/InitMission.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/InitMission.srv#L1)
