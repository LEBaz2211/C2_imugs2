# ROS services · /multi_robot/edge

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Service declarations in this extracted namespace group.

| Contract | Type/details | Evidence |
|---|---|---|
| [multi_robot/edge/agent_{agent_id}/add_task](../multi-robot-edge-agent-agent-id-add-task.md) | `task_msgs/srv/AddTask` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:89`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L89), [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:339`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L339) |
| [multi_robot/edge/agent_{agent_id}/change_state](../multi-robot-edge-agent-agent-id-change-state.md) | `task_msgs/srv/ChangeState` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:92`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L92), [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:340`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L340) |
| [multi_robot/edge/agent_{agent_id}/change_task_state](../multi-robot-edge-agent-agent-id-change-task-state.md) | `task_msgs/srv/ChangeTaskState` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:95`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L95), [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:341`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L341) |
| [multi_robot/edge/agent_{agent_id}/cmd](../multi-robot-edge-agent-agent-id-cmd.md) | `std_srvs::srv::Trigger` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:101`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L101) |
