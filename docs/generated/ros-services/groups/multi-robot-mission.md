# ROS services · /multi_robot/mission

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Service declarations in this extracted namespace group.

| Contract | Type/details | Evidence |
|---|---|---|
| [multi_robot/mission_{mission_id}/cmd](../multi-robot-mission-mission-id-cmd.md) | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:149`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L149) |
| [multi_robot/mission_{mission_id}/environment_change](../multi-robot-mission-mission-id-environment-change.md) | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78), [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419) |
| [multi_robot/mission_{mission_id}/mission_status_change](../multi-robot-mission-mission-id-mission-status-change.md) | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:75`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L75), [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:418`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L418) |
| [multi_robot/mission_{mission_id}/vehicle_change](../multi-robot-mission-mission-id-vehicle-change.md) | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:81`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L81), [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:420`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L420) |
