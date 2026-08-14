# c2_msgs/msg/ChangeMissionStatusResponse

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `uint8` | `mission_status` |
| message | `string<=2000` | `error_message` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

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

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusResponse.msg#L1)
