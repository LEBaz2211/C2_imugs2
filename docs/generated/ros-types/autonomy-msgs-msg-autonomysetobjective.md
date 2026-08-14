# autonomy_msgs/msg/AutonomySetObjective

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomySetObjective.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `bool` | `null_objective` |
| message | `AutonomyObjective` | `objective` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Edge sends the current waypoint to autonomy

!!! warning "Observed Excerpt"
    Phase: execution.

```json
{
  "null_objective": false,
  "objective": {
    "id": "<first-generated-objective-uuid>",
    "objective_type": "combined_primitives",
    "parallel_execution": true,
    "primitives": [
      "{\"id\":\"<generated-primitive-uuid>\",\"type\":\"waypoint\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3,\"mobility_profile\":0,\"wait_time\":0}}"
    ],
    "max_speed": 1.3,
    "mobility_profile": 0
  }
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:850`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L850)

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomySetObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/msg/AutonomySetObjective.msg#L1)
