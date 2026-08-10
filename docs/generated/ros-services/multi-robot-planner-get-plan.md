# /multi_robot/planner/get_plan

ROS service `/multi_robot/planner/get_plan`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `/multi_robot/planner/get_plan` |
| Type | `centralized_msgs/srv/GetPlan` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `id` |
| response | `string` | `id` |
| response | `string` | `plan` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `centralized_msgs/srv/GetPlan` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L53) |
| provides | `centralized_msgs/srv/GetPlan` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:144`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L144) |

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L53)
- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:144`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L144)
