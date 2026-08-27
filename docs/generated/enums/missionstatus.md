# MissionStatus

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

## c2_msgs.MissionStatus

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:28`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L28)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` | NOT USED |
| `1` | `PLANNED` | Mission is correctly planned |
| `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
| `3` | `PLANNED_FAILED` | Mission planning failed |
| `4` | `ACCEPTED` | Mission is accepted |
| `5` | `STARTED` | Mission is started |
| `6` | `PAUSED` | Mission is paused |
| `7` | `FAILED` | Mission has failed |
| `8` | `STOPPED` | Mission is finished by request.  it will not stop a mission, except if FAILED or another mission is started. |
| `9` | `DELETED` | Missio is deleted from the system. |
| `10` | `COMPLETED` |  |

## centralized_msgs.MissionStatus

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:37`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L37)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` | NOT USED |
| `1` | `PLANNED` | Mission is correctly planned |
| `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
| `3` | `PLANNED_FAILED` | Mission planning failed |
| `4` | `ACCEPTED` | Mission is accepted |
| `5` | `STARTED` | Mission is started |
| `6` | `PAUSED` | Mission is paused |
| `7` | `FAILED` | Mission has failed |
| `8` | `STOPPED` | Mission is finished by request.  itwill not stop a mission, except if FAILED or another mission is started. |
| `9` | `DELETED` | Missio is deleted from the system. |
| `10` | `COMPLETED` |  |

## centralized_msgs.MissionStatus

Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:37`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L37)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` | NOT USED |
| `1` | `PLANNED` | Mission is correctly planned |
| `2` | `PLANNED_ALTERNATIVE` | Mission has alternative planned |
| `3` | `PLANNED_FAILED` | Mission planning failed |
| `4` | `ACCEPTED` | Mission is accepted |
| `5` | `STARTED` | Mission is started |
| `6` | `PAUSED` | Mission is paused |
| `7` | `FAILED` | Mission has failed |
| `8` | `STOPPED` | Mission is finished by request.  itwill not stop a mission, except if FAILED or another mission is started. |
| `9` | `DELETED` | Missio is deleted from the system. |
| `10` | `COMPLETED` |  |

## c2_imugs2.core.models.MissionStatus

Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:26`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L26)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` |  |
| `1` | `PLANNED` |  |
| `2` | `PLANNED_ALTERNATIVE` |  |
| `3` | `PLANNED_FAILED` |  |
| `4` | `ACCEPTED` |  |
| `5` | `STARTED` |  |
| `6` | `PAUSED` |  |
| `7` | `FAILED` |  |
| `8` | `STOPPED` |  |
| `9` | `DELETED` |  |
| `10` | `COMPLETED` |  |

## Values used by the verified navigation run

The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:

| Value | Member | Where it appeared |
|---:|---|---|
| `0` | `NONE` | planning begins |
| `1` | `PLANNED` | 10-waypoint plan received |
| `4` | `ACCEPTED` | task dispatched stopped |
| `5` | `STARTED` | task execution requested |
| `10` | `COMPLETED` | Themis finished its task |

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

