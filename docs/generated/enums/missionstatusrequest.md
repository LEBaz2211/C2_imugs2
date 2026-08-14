# MissionStatusRequest

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

## c2_msgs.MissionStatusRequest

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:43`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L43)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `INIT` | Initialize mission |
| `1` | `APPROVE` | Approve mission |
| `2` | `START` | Start mission |
| `3` | `PAUSE` | Pause mission |
| `4` | `STOP` | Stop mission |
| `5` | `DELETE` | Delete mission |

## centralized_msgs.MissionStatusRequest

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:52`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L52)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `INIT` | Initialize mission |
| `1` | `APPROVE` | Approve mission |
| `2` | `START` | Start mission |
| `3` | `PAUSE` | Pause mission |
| `4` | `STOP` | Stop mission |
| `5` | `DELETE` | Delete mission |

## centralized_msgs.MissionStatusRequest

Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:52`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L52)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `INIT` | Initialize mission |
| `1` | `APPROVE` | Approve mission |
| `2` | `START` | Start mission |
| `3` | `PAUSE` | Pause mission |
| `4` | `STOP` | Stop mission |
| `5` | `DELETE` | Delete mission |

## Values used by the verified navigation run

The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:

| Value | Member | Where it appeared |
|---:|---|---|
| `0` | `INIT` | initialize |
| `1` | `APPROVE` | install stopped task |
| `2` | `START` | execute task |

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

