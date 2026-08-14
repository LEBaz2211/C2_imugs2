# multi_robot/edge/connection_check

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `multi_robot/edge/connection_check`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `multi_robot/edge/connection_check` |
| Type | `std_msgs/msg/String` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `data` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:80`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L80) |
| subscribes | `std_msgs/msg/String` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:86`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L86) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:86`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L86)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:80`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L80)
