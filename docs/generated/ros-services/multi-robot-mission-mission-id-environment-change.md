# multi_robot/mission_{mission_id}/environment_change

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `multi_robot/mission_{mission_id}/environment_change`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/mission_{mission_id}/environment_change` |
| Type | `std_srvs::srv::Trigger` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419) |
| provides | `std_srvs::srv::Trigger` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:78`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L78)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:419`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L419)
