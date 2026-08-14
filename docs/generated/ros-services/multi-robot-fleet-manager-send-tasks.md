# multi_robot/fleet_manager/send_tasks

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `multi_robot/fleet_manager/send_tasks`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/fleet_manager/send_tasks` |
| Type | `c2_msgs/srv/InitMission` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `string<=10000` | `mission_config` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `string<=10000` | `mission_feedback` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `c2_msgs/srv/InitMission` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90) |
| provides | `c2_msgs/srv/InitMission` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Mission manager asks Fleet to dispatch the stored plan

!!! success "Verified Flow"
    Phase: APPROVE.

```json
{
  "request": {
    "mission_id": {
      "uuid": [
        68,
        68,
        68,
        68,
        85,
        85,
        70,
        102,
        135,
        119,
        136,
        136,
        136,
        136,
        136,
        136
      ]
    },
    "mission_config": ""
  },
  "response": {
    "mission_id": {
      "uuid": [
        68,
        68,
        68,
        68,
        85,
        85,
        70,
        102,
        135,
        119,
        136,
        136,
        136,
        136,
        136,
        136
      ]
    },
    "mission_feedback": ""
  }
}
```

- This service reuses InitMission.srv, but both string fields are intentionally empty; Fleet reloads the plan from RuntimeDB.Planning by mission ID.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:1056`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L1056), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:469`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L469)

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:90`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L90)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L62)
