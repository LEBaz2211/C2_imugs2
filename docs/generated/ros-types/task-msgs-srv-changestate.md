# task_msgs/srv/ChangeState

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

SRV definition from `task_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeState.srv` |
| Package | `task_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| request | `uint8` | `requested_state` |
| response | `uint8` | `state` |
| response | `string<=1024` | `feedback` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeState.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeState.srv#L1)
