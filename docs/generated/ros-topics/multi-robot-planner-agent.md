# /multi_robot/planner/agent

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS topic `/multi_robot/planner/agent`

| Property | Extracted value |
|---|---|
| Kind | `ros_topic` |
| Interface | `/multi_robot/planner/agent` |
| Type | `centralized_msgs/msg/Agent` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `agent_id` |
| message | `string` | `agent_profile` |
| message | `nav_msgs/Odometry` | `odometry` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| publishes | `centralized_msgs/msg/Agent` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67) |
| subscribes | `centralized_msgs/msg/Agent` | [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Fleet forwards Themis and its live pose to Planner

!!! warning "Observed Excerpt"
    Phase: robot discovery.

```json
{
  "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
  "agent_profile": "<JSON profile published by Edge>",
  "odometry": {
    "pose": {
      "pose": {
        "position": {
          "x": 4.392588,
          "y": 50.844317,
          "z": 0.0
        }
      }
    }
  }
}
```

- In this global-coordinate simulation, odometry x is longitude and y is latitude.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:304`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L304)

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:67`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L67)
- [`backend/fog/planner/ros2ws/src/planner/planner/planner_node.py:134`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/planner/planner/planner_node.py#L134)
