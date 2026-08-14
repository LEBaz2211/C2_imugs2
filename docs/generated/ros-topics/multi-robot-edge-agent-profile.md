# /multi_robot/edge/agent_profile

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/edge/agent_profile`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/edge/agent_profile` |
| Type | `std_msgs/msg/String` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `data` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `std_msgs/msg/String` | [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82) |
| subscribes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Edge publishes the participating robot profile

!!! warning "Observed Excerpt"
    Phase: robot discovery.

```json
{
  "data": "{\"agent_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"vehicle_constraints\":{\"max_speed\":{\"linear\":{\"x\":4.5}},\"max_acceleration\":{\"linear\":{\"x\":8.0}}},\"vehicle_info\":{\"fuel_status_pct\":85.0,\"battery_status_pct\":90.0}}"
}
```

- The JSON string is abridged; the runtime profile also contains angular constraints, dimensions, endurance, and sensors.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:250`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L250), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

## Definition evidence

- [`backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp:82`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp#L82)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:77`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L77)
