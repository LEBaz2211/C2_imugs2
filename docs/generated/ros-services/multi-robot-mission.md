# multi_robot/mission_

ROS service `multi_robot/mission_`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/mission_` |
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
| calls | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:418`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L418) |
| calls | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419) |
| calls | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:420`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L420) |
| provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:149`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L149) |
| provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75) |
| provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78) |
| provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:81`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L81) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:81`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L81)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:149`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L149)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:418`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L418)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:420`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L420)
