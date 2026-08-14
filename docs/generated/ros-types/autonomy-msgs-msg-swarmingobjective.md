# autonomy_msgs/msg/SwarmingObjective

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

MSG definition from `autonomy_msgs`

| Property | Extracted value |
|---|---|
| Kind | `ros_type` |
| Path | `backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingObjective.msg` |
| Package | `autonomy_msgs` |

## Fields

| Section | Type | Name |
|---|---|---|
| message | `unique_identifier_msgs/UUID` | `id` |
| message | `string<=100` | `arrival_point` |
| message | `string<=150000[<=1]` | `path` |
| message | `float32` | `max_speed` |
| message | `uint8` | `mobility_profile` |

## Definition evidence

- [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingObjective.msg:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/.devcontainer/msg/SwarmingObjective.msg#L1)
