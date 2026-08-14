# centralized_msgs/srv/GetPlan

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `centralized_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetPlan.srv` |
| Package | `centralized_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `id` |
| response | `string` | `id` |
| response | `string` | `plan` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Retrieve the generated robot task

!!! warning "Observed Excerpt"
    Phase: plan retrieval.

```json
{
  "request": {
    "id": "44444444-5555-4666-8777-888888888888"
  },
  "response": {
    "id": "44444444-5555-4666-8777-888888888888",
    "plan": "<JSON-encoded TaskPlan containing one Themis task and 10 waypoint objectives>"
  }
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:641`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L641)

## Definition evidence

- [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetPlan.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/srv/GetPlan.srv#L1)
