# multi_robot/delete_mission

ROS service `multi_robot/delete_mission`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/delete_mission` |
| Type | `c2_msgs/srv/ChangeMissionStatus` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `uint8` | `mission_request_status` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `uint8` | `mission_status` |
| response | `string<=2000` | `error_message` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:84`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L84) |
| provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:48`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L48) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:84`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L84)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:48`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L48)
