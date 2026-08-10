# task_msgs/srv/AddTask

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

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/srv/AddTask.srv#L1)
