# multi_robot/mission_{mission_id}/mission_status_change

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `multi_robot/mission_{mission_id}/mission_status_change`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/mission_{mission_id}/mission_status_change` |
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
| provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:418`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L418)
