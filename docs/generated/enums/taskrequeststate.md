# TaskRequestState

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

## autonomy_msgs.TaskRequestState

Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L16)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOP` | request to stop the task & re-init |
| `1` | `EXECUTE` | request to execute the task |
| `2` | `PAUSE` | request to pause the task |
| `3` | `DELETE` | request to delete the task |

## task_msgs.TaskRequestState

Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L16)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOP` | request to stop the task & re-init |
| `1` | `EXECUTE` | request to execute the task |
| `2` | `PAUSE` | request to pause the task |
| `3` | `DELETE` | request to delete the task |

## autonomy_msgs.TaskRequestState

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L16)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOP` | request to stop the task & re-init |
| `1` | `EXECUTE` | request to execute the task |
| `2` | `PAUSE` | request to pause the task |
| `3` | `DELETE` | request to delete the task |

## task_msgs.TaskRequestState

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:16`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L16)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOP` | request to stop the task & re-init |
| `1` | `EXECUTE` | request to execute the task |
| `2` | `PAUSE` | request to pause the task |
| `3` | `DELETE` | request to delete the task |

## Values used by the verified navigation run

The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:

| Value | Member | Where it appeared |
|---:|---|---|
| `1` | `EXECUTE` | START fan-out |

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

