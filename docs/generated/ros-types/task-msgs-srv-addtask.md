# task_msgs/srv/AddTask

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `task_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv` |
| Package | `task_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `string` | `task_id` |
| request | `uint8` | `task_type` |
| request | `bool` | `override` |
| request | `string<=1048576` | `task_config` |
| request | `string` | `std` |
| response | `string` | `task_id` |
| response | `uint8` | `task_state` |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Fleet installs the stopped waypoint task on Themis

!!! warning "Observed Excerpt"
    Phase: APPROVE.

```json
{
  "request": {
    "task_id": "<generated-task-uuid>",
    "task_type": 0,
    "override": true,
    "task_config": "{\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"primitive_type\":\"waypoint\"}],\"objectives\":[{\"objective_id\":\"<first-generated-objective-uuid>\",\"primitives\":[{\"primitive_id\":\"<generated-primitive-uuid>\",\"parameters\":{\"coordinates\":[4.3925979,50.8443434],\"speed\":1.3,\"max_speed\":1.3}}]}]}",
    "std": ""
  },
  "response": {
    "task_id": "<generated-task-uuid>",
    "task_state": 0
  }
}
```

- task_config is an abridged JSON string; the real task contained 10 waypoint objectives.
- Task state 0 is STOPPED: APPROVE installs the task but does not move the robot.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:750`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L750)

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv#L1)
