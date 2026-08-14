# {autonomy_prefix}/edge/multi_robot/detected_obstacle

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `{autonomy_prefix}/edge/multi_robot/detected_obstacle`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `{autonomy_prefix}/edge/multi_robot/detected_obstacle` |
| Type | `autonomy_msgs/msg/DetectedObstacle` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `obstacle_id` |
| message | `string` | `obstacle_geofence` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| subscribes | `autonomy_msgs/msg/DetectedObstacle` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L61) |

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:61`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L61)
