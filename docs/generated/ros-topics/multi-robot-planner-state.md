# /multi_robot/planner/state

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/planner/state`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/planner/state` |
| Type | `std_msgs/msg/String` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `data` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `std_msgs/msg/String` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132) |
| subscribes | `std_msgs/msg/String` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Planner reports that the plan cache is ready

!!! success "Runtime Observed"
    Phase: planning.

```json
{
  "data": "{\"planners\":[{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"state\":2}]}"
}
```

- State 2 was observed, but usable route evidence still comes from non-empty mission feedback waypoints.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:65`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L65)
- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:132`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L132)
