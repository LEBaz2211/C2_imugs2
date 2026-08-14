# centralized_msgs/srv/CreatePlanner

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `centralized_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/CreatePlanner.srv` |
| Package | `centralized_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `id` |
| request | `uint8` | `priority` |
| request | `Agent[]` | `agents` |
| request | `string` | `config` |
| response | `string` | `id` |
| response | `uint8` | `state` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Create the planner for the mission

!!! success "Verified Flow"
    Phase: planning.

```json
{
  "request": {
    "id": "44444444-5555-4666-8777-888888888888",
    "priority": 0,
    "agents": [
      {
        "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
        "agent_profile": "<JSON vehicle profile>",
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
    ],
    "config": "<legacy mission_config JSON string>"
  },
  "response": {
    "id": "44444444-5555-4666-8777-888888888888",
    "state": 0
  }
}
```

- The verified run then published planner states 0, 1, and 2 asynchronously.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:475`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L475)

## Definition evidence

- [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/CreatePlanner.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/CreatePlanner.srv#L1)
