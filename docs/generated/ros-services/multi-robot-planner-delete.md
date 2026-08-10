# multi_robot/planner/delete

ROS service `multi_robot/planner/delete`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/planner/delete` |
| Type | `centralized_msgs/srv/DeletePlanner` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `id` |
| response | `string` | `id` |
| response | `uint8` | `state` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `centralized_msgs/srv/DeletePlanner` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:42`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L42) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:42`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L42)
