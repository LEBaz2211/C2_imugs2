# multi_robot/fleet_manager/send_tasks

ROS service `multi_robot/fleet_manager/send_tasks`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/fleet_manager/send_tasks` |
| Type | `c2_msgs/srv/InitMission` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `string<=10000` | `mission_config` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `string<=10000` | `mission_feedback` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `c2_msgs/srv/InitMission` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90) |
| provides | `c2_msgs/srv/InitMission` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62)
