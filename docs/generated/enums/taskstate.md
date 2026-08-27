# TaskState

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

!!! warning "Conflicting extracted definitions"
    2 member/value signatures were found.

## autonomy_msgs.TaskState

Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/Enums.hpp#L24)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOPPED` | stopped, but not completed or started |
| `1` | `STARTED` | started |
| `2` | `PAUSED` | paused |
| `3` | `COMPLETED` | completed the task |
| `4` | `ABORTED` | aborted |
| `5` | `DELETED` | deleted |

## task_msgs.TaskState

Language: **C++** · Evidence: [`backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/edge/agent-tasks-supervisor/ros2ws/src/message_packages/task_msgs/json/Enums.hpp#L24)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOPPED` | stopped, but not completed or started |
| `1` | `STARTED` | started |
| `2` | `PAUSED` | paused |
| `3` | `COMPLETED` | completed the task |
| `4` | `ABORTED` | aborted |
| `5` | `DELETED` | deleted |

## autonomy_msgs.TaskState

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/autonomy_msgs/json/Enums.hpp#L24)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOPPED` | stopped, but not completed or started |
| `1` | `STARTED` | started |
| `2` | `PAUSED` | paused |
| `3` | `COMPLETED` | completed the task |
| `4` | `ABORTED` | aborted |
| `5` | `DELETED` | deleted |

## task_msgs.TaskState

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/task_msgs/json/Enums.hpp#L24)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOPPED` | stopped, but not completed or started |
| `1` | `STARTED` | started |
| `2` | `PAUSED` | paused |
| `3` | `COMPLETED` | completed the task |
| `4` | `ABORTED` | aborted |
| `5` | `DELETED` | deleted |

## c2_imugs2.core.models.TaskState

Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:71`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L71)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `STOP` |  |
| `1` | `EXECUTE` |  |
| `2` | `PAUSE` |  |
| `3` | `DELETE` |  |
| `4` | `COMPLETED` |  |

## Values used by the verified navigation run

The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:

Runtime definition: **task_msgs.TaskState used by Fleet and Edge; not c2_imugs2.core.models.TaskState**.

| Value | Member | Where it appeared |
|---:|---|---|
| `0` | `STOPPED` | after APPROVE |
| `1` | `STARTED` | after START |
| `3` | `COMPLETED` | final waypoint reached |

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

