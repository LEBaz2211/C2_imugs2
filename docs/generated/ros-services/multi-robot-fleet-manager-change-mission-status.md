# multi_robot/fleet_manager/change_mission_status

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

ROS service `multi_robot/fleet_manager/change_mission_status`

| Property | Extracted value |
|---|---|
| Kind | `ros_service` |
| Interface | `multi_robot/fleet_manager/change_mission_status` |
| Type | `c2_msgs/srv/ChangeMissionStatus` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `uint8` | `mission_request_status` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `uint8` | `mission_status` |
| response | `string<=2000` | `error_message` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| calls | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:93`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L93) |
| provides | `c2_msgs/srv/ChangeMissionStatus` | [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L64) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### APPROVE status request

!!! success "Verified Flow"
    Phase: APPROVE.

```json
{
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
  "mission_request_status": 1
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:718`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L718)

### START status request

!!! success "Verified Flow"
    Phase: START.

```json
{
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
  "mission_request_status": 2
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:796`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L796)

## Definition evidence

- [`backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:93`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L93)
- [`backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp:64`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp#L64)
