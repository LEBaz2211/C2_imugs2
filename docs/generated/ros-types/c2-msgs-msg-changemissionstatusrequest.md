# c2_msgs/msg/ChangeMissionStatusRequest

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusRequest.msg` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `uint8` | `mission_request_status` |

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

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusRequest.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/ChangeMissionStatusRequest.msg#L1)
