# centralized_msgs/srv/GetAgents

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `centralized_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv` |
| Package | `centralized_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
| response | `centralized_msgs/Agent[]` | `agents` |
| response | `string<=2000` | `error_message` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Mission manager requests the configured Themis agent

!!! success "Verified Flow"
    Phase: planning.

```json
{
  "request": {
    "agent_id_list": [
      {
        "uuid": [
          249,
          153,
          43,
          179,
          152,
          113,
          69,
          31,
          144,
          160,
          146,
          7,
          235,
          159,
          230,
          197
        ]
      }
    ]
  },
  "response": {
    "agents": [
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
    ],
    "error_message": "ok"
  }
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:452`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L452)

## Definition evidence

- [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetAgents.srv#L1)
