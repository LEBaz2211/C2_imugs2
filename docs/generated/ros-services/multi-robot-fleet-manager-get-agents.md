# multi_robot/fleet_manager/get_agents

ROS service `multi_robot/fleet_manager/get_agents`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/fleet_manager/get_agents` |
| Type | `centralized_msgs/srv/GetAgents` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
| response | `centralized_msgs/Agent[]` | `agents` |
| response | `string<=2000` | `error_message` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `centralized_msgs/srv/GetAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87) |
| provides | `centralized_msgs/srv/GetAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60)
