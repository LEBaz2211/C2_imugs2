# c2_msgs/srv/ChangeMissionStatus

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `unique_identifier_msgs/UUID` | `mission_id` |
| request | `uint8` | `mission_request_status` |
| response | `unique_identifier_msgs/UUID` | `mission_id` |
| response | `uint8` | `mission_status` |
| response | `string<=2000` | `error_message` |

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

### Mission manager accepts the APPROVE transition

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
  "mission_status": 4,
  "error_message": ""
}
```

- Mission status 4 is ACCEPTED.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

### Mission manager accepts the START transition

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
  "mission_status": 5,
  "error_message": ""
}
```

- Mission status 5 is STARTED.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp:876`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp#L876)

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/srv/ChangeMissionStatus.srv#L1)
