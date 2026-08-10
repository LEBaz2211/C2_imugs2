# MissionStatus

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

## c2_imugs2.domain.MissionStatus

Language: **Python** · Evidence: [`src/c2_imugs2/domain.py:24`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/domain.py#L24)

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

