# Behavior

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

## c2_msgs.Behavior

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:53`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L53)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NAVIGATE` | Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection |
| `1` | `COVERAGE` | Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission |
| `2` | `NAVIGATE_NO_PLANNING` | Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space) |

## centralized_msgs.Behavior

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L62)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NAVIGATE` | Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection |
| `1` | `COVERAGE` | Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission |
| `2` | `NAVIGATE_NO_PLANNING` | Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space) |

## centralized_msgs.Behavior

Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:62`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L62)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NAVIGATE` | Navigation/driving based behavior. Used for mission types: Good transportation, CASEVAC, Comm relay, Screen mission, Ballistic protection |
| `1` | `COVERAGE` | Monitoring/patrolling the objective. Used for mission types: Reconnaissance mission, Patrolling mission |
| `2` | `NAVIGATE_NO_PLANNING` | Navigation/driving based behavior, but without using the planner: Used to test the navigation (local space) |

## c2_imugs2.core.models.Behavior

Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:10`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L10)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NAVIGATE` |  |
| `1` | `COVERAGE` |  |
| `2` | `NAVIGATE_NO_PLANNING` |  |

## Values used by the verified navigation run

The [one-robot Point-navigation run](../examples/single-robot-point-navigation.md) exercised these values:

| Value | Member | Where it appeared |
|---:|---|---|
| `0` | `NAVIGATE` | mission configuration |

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)

