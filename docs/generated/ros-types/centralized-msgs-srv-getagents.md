# centralized_msgs/srv/GetAgents

SRV definition from `centralized_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv` |
| Package | `centralized_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
| response | `centralized_msgs/Agent[]` | `agents` |
| response | `string<=2000` | `error_message` |

## Definition evidence

- [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv#L1)
