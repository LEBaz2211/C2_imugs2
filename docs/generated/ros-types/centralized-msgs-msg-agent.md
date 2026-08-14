# centralized_msgs/msg/Agent

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `centralized_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/Agent.msg` |
| Package | `centralized_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `string` | `agent_id` |
| message | `string` | `agent_profile` |
| message | `nav_msgs/Odometry` | `odometry` |

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

- [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/Agent.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/msg/Agent.msg#L1)
