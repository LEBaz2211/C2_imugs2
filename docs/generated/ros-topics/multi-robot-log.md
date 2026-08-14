# /multi_robot/log

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/log`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/log` |
| Type | `c2_msgs/msg/SwarmLog` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string` | `log` |
| message | `string` | `date` |
| message | `uint8` | `log_type` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L54) |
| publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:143`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L143) |
| publishes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L64) |
| subscribes | `c2_msgs/msg/SwarmLog` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:51`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L51) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:143`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L143)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:54`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L54)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:51`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L51)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L64)
