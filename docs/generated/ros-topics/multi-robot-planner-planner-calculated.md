# /multi_robot/planner/planner_calculated

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/planner/planner_calculated`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/planner/planner_calculated` |
| Type | `centralized_msgs/msg/PlanCalculated` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `id` |
| message | `string` | `plan` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| subscribes | `centralized_msgs/msg/PlanCalculated` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L62) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L62)
