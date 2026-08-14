# /multi_robot/planner/set_agents

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `/multi_robot/planner/set_agents`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `/multi_robot/planner/set_agents` |
| Type | `centralized_msgs/srv/UpdatePlannerAgents` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `id` |
| request | `Agent[]` | `agents` |
| response | `string` | `id` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `centralized_msgs/srv/UpdatePlannerAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:59`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L59) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:59`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L59)
