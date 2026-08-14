# multi_robot/fleet_manager/get_agents

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `multi_robot/fleet_manager/get_agents`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/fleet_manager/get_agents` |
| Type | `centralized_msgs/srv/GetAgents` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID[]` | `agent_id_list` |
| response | `centralized_msgs/Agent[]` | `agents` |
| response | `string<=2000` | `error_message` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `centralized_msgs/srv/GetAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87) |
| provides | `centralized_msgs/srv/GetAgents` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60) |

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

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:87`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L87)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:60`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L60)
