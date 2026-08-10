# task_msgs/srv/ChangeTaskState

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

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/ChangeTaskState.srv#L1)
