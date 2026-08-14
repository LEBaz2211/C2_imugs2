# /multi_robot/planner/delete_planner

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `/multi_robot/planner/delete_planner`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `/multi_robot/planner/delete_planner` |
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
| provides | `centralized_msgs/srv/DeletePlanner` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:147`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L147) |

## Definition evidence

- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:147`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L147)
