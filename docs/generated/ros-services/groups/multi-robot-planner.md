# ROS services · /multi_robot/planner

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Service declarations in this extracted namespace group.

| Contract | Type/details | Evidence |
|---|---|---|
| [/multi_robot/planner/create](../multi-robot-planner-create.md) | `centralized_msgs/srv/CreatePlanner` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:56`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L56), [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:141`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L141) |
| [/multi_robot/planner/delete_planner](../multi-robot-planner-delete-planner.md) | `centralized_msgs/srv/DeletePlanner` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:147`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L147) |
| [/multi_robot/planner/get_plan](../multi-robot-planner-get-plan.md) | `centralized_msgs/srv/GetPlan` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L53), [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:144`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L144) |
| [/multi_robot/planner/set_agents](../multi-robot-planner-set-agents.md) | `centralized_msgs/srv/UpdatePlannerAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:59`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L59) |
| [multi_robot/planner/delete](../multi-robot-planner-delete.md) | `centralized_msgs/srv/DeletePlanner` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp:42`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp#L42) |
