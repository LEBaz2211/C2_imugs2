# task_msgs/srv/ChangeTaskState

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `task_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv` |
| Package | `task_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `task_id` |
| request | `uint8` | `task_requested_state` |
| response | `string` | `task_id` |
| response | `uint8` | `task_state` |
| response | `string<=1024` | `feedback` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Fleet starts the installed Themis task

!!! success "Verified Flow"
    Phase: START.

```json
{
  "request": {
    "task_id": "<generated-task-uuid>",
    "task_requested_state": 1
  },
  "response": {
    "task_id": "<generated-task-uuid>",
    "task_state": 1,
    "feedback": ""
  }
}
```

- task_requested_state 1 is EXECUTE; task_state 1 is STARTED.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:818`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L818)

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv#L1)
