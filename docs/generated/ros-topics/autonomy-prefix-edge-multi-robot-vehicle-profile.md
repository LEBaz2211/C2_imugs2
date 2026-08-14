# {autonomy_prefix}/edge/multi_robot/vehicle_profile

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `{autonomy_prefix}/edge/multi_robot/vehicle_profile`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `{autonomy_prefix}/edge/multi_robot/vehicle_profile` |
| Type | `autonomy_msgs/msg/VehicleProfile` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `uint8` | `active_autonomy_mode` |
| message | `VehicleConstraints` | `vehicle_constraints` |
| message | `VehicleInfo` | `vehicle_info` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `autonomy_msgs/msg/VehicleProfile` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:50`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L50) |
| subscribes | `autonomy_msgs/msg/VehicleProfile` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L58) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:58`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L58)
- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp:50`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/test_autonomy.cpp#L50)
