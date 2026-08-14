# c2_msgs/msg/MissionFeedback

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `c2_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/MissionFeedback.msg` |
| Package | `c2_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `mission_id` |
| message | `string` | `mission_feedback` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Mission feedback proving that a route was received

!!! warning "Observed Excerpt"
    Phase: PLANNED.

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
  "mission_feedback": "{\"mission_id\":\"44444444-5555-4666-8777-888888888888\",\"behavior\":0,\"status\":1,\"requested_status\":0,\"tasks\":[{\"vehicle_id\":\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\",\"task_id\":\"<generated-task-uuid>\",\"waypoints\":[{\"coordinates\":[50.8443434,4.3925979]},{\"coordinates\":[50.84417059346137,4.391670213379427]}]}]}"
}
```

- The JSON string is abridged from 10 waypoints.
- Legacy MissionFeedback serializes waypoint coordinates as [latitude, longitude]; the adapter swaps them back to [longitude, latitude].

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:678`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L678)

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/MissionFeedback.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/msg/MissionFeedback.msg#L1)
