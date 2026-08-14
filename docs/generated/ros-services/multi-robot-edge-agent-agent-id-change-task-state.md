# multi_robot/edge/agent_{agent_id}/change_task_state

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `multi_robot/edge/agent_{agent_id}/change_task_state`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/edge/agent_{agent_id}/change_task_state` |
| Type | `task_msgs/srv/ChangeTaskState` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `task_id` |
| request | `uint8` | `task_requested_state` |
| response | `string` | `task_id` |
| response | `uint8` | `task_state` |
| response | `string<=1024` | `feedback` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `task_msgs/srv/ChangeTaskState` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341) |
| provides | `task_msgs/srv/ChangeTaskState` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:95`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L95) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:95`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L95)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341)
