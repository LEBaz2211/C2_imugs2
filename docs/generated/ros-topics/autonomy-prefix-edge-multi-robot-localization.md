# {autonomy_prefix}/edge/multi_robot/localization

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `{autonomy_prefix}/edge/multi_robot/localization`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `{autonomy_prefix}/edge/multi_robot/localization` |
| Type | `nav_msgs::msg::Odometry` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `nav_msgs::msg::Odometry` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:43`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L43) |
| subscribes | `nav_msgs::msg::Odometry` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L55) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:55`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L55)
- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:43`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L43)
