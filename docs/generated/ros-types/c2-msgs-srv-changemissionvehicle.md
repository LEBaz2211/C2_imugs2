# c2_msgs/srv/ChangeMissionVehicle

SRV definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionVehicle.srv` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `unique_identifier_msgs/UUID[]` | `vehicule_id_list` |
| request | `uint8` | `vehicle_changes` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionVehicle.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionVehicle.srv#L1)
