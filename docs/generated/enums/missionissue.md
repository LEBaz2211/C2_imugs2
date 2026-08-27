# MissionIssue

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

## c2_msgs.MissionIssue

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp:5`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp#L5)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` | No issue |
| `10` | `MISSION_WARN_ID_ALREADY_USED` | Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT. |
| `11` | `MISSION_WARN_UGV_UNAVAILABLE` | At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE |
| `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` | The provided mission_config file contains unknown keys. The latter data will simply be ignored. |
| `13` | `MISSION_WARN_STATUS_NOT_CHANGED` | The requested mission status change was not valid. The transition will be ignored. |
| `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner. Mission state will not change |
| `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` | Could not communicate with at least one  edge module. Mission state will not change |
| `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module. Mission state will not change |
| `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` | The provided mission_config file could not be parsed. Mission state will be set to FAILED. |
| `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` | The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED. |
| `22` | `MISSION_FAILED_MISSION_COMPROMISED` | The mission is compromised and is unable to continue. Mission state will be set to FAILED. |
| `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED. |
| `24` | `MISSION_FAILED_DISCONNECTED_EDGE` | Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED. |
| `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED |
| `30` | `PLANNING_WARN_VEHICLES_MISMATCH` | Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
| `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` | not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
| `32` | `PLANNING_WARN_DATE_COMPROMISED` | Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway |
| `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` | No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED |
| `41` | `PLANNING_FAILED` | Swarm planner process fail,  Mission state will be set to PLANNED_FAILED. |

## centralized_msgs.MissionIssue

Language: **C++** · Evidence: [`backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp:14`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/centralized-coordination/src/message_packages/centralized_msgs/json/Enums.hpp#L14)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` | No issue |
| `10` | `MISSION_WARN_ID_ALREADY_USED` | Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT. |
| `11` | `MISSION_WARN_UGV_UNAVAILABLE` | At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE |
| `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` | The provided mission_config file contains unknown keys. The latter data will simply be ignored. |
| `13` | `MISSION_WARN_STATUS_NOT_CHANGED` | The requested mission status change was not valid. The transition will be ignored. |
| `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner. Mission state will not change |
| `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` | Could not communicate with at least one  edge module. Mission state will not change |
| `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module. Mission state will not change |
| `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` | The provided mission_config file could not be parsed. Mission state will be set to FAILED. |
| `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` | The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED. |
| `22` | `MISSION_FAILED_MISSION_COMPROMISED` | The mission is compromised and is unable to continue. Mission state will be set to FAILED. |
| `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED. |
| `24` | `MISSION_FAILED_DISCONNECTED_EDGE` | Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED. |
| `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED |
| `30` | `PLANNING_WARN_VEHICLES_MISMATCH` | Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
| `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` | not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
| `32` | `PLANNING_WARN_DATE_COMPROMISED` | Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway |
| `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` | No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED |
| `41` | `PLANNING_FAILED` | Swarm planner process fail,  Mission state will be set to PLANNED_FAILED. |

## centralized_msgs.MissionIssue

Language: **C++** · Evidence: [`backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp:14`](https://github.com/LEBaz2211/C2_imugs2/blob/main/backend/fog/planner/ros2ws/src/message_packages/centralized_msgs/json/Enums.hpp#L14)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` | No issue |
| `10` | `MISSION_WARN_ID_ALREADY_USED` | Mission ID is already in use. The corresponding mission configuration will be overwritten. Mission state will be set to INIT. |
| `11` | `MISSION_WARN_UGV_UNAVAILABLE` | At least one UGV is unavailable. Reduced set of UGVs will be used. Mission state will be set to PLANNED_ALTERNATIVE |
| `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` | The provided mission_config file contains unknown keys. The latter data will simply be ignored. |
| `13` | `MISSION_WARN_STATUS_NOT_CHANGED` | The requested mission status change was not valid. The transition will be ignored. |
| `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner. Mission state will not change |
| `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` | Could not communicate with at least one  edge module. Mission state will not change |
| `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module. Mission state will not change |
| `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` | The provided mission_config file could not be parsed. Mission state will be set to FAILED. |
| `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` | The provided mission_config file does not contain sufficient data for plannification. Mission state will be set to FAILED. |
| `22` | `MISSION_FAILED_MISSION_COMPROMISED` | The mission is compromised and is unable to continue. Mission state will be set to FAILED. |
| `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` | Could not communicate with swarm planner, results in process failure. Mission state will be set to FAILED. |
| `24` | `MISSION_FAILED_DISCONNECTED_EDGE` | Could not communicate with  edge modules, results in process failure. Mission state will be set to FAILED. |
| `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` | Could not communicate with at least one autonomy module, timeout results in mission failure. Mission state will be set to FAILED |
| `30` | `PLANNING_WARN_VEHICLES_MISMATCH` | Not enough vehicles for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
| `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` | not enough coverage for the given mission configuration. Mission state will be set to PLANNED_ALTERNATIVE |
| `32` | `PLANNING_WARN_DATE_COMPROMISED` | Requested start or end date is compromised in planning solution. Mission state will be set to PLANNED anyway |
| `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` | No planning solution found. New init_mission needed with adjusted configuration. Mission state will be set to PLANNED_FAILED |
| `41` | `PLANNING_FAILED` | Swarm planner process fail,  Mission state will be set to PLANNED_FAILED. |

## c2_imugs2.core.models.MissionIssue

Language: **Python** · Evidence: [`src/c2_imugs2/core/models.py:49`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/core/models.py#L49)

| Value | Member | Source comment |
|---:|---|---|
| `0` | `NONE` |  |
| `10` | `MISSION_WARN_ID_ALREADY_USED` |  |
| `11` | `MISSION_WARN_UGV_UNAVAILABLE` |  |
| `12` | `MISSION_WARN_CONFIG_UNKNOWN_DATA` |  |
| `13` | `MISSION_WARN_STATUS_NOT_CHANGED` |  |
| `14` | `MISSION_WARN_DISCONNECTED_SWARM_PLANNER` |  |
| `15` | `MISSION_WARN_DISCONNECTED_SWARMING_EDGE` |  |
| `16` | `MISSION_WARN_DISCONNECTED_AUTONOMY` |  |
| `20` | `MISSION_FAILED_CONFIG_PARSING_UNSUCCESSFUL` |  |
| `21` | `MISSION_FAILED_CONFIG_MISSING_DATA` |  |
| `22` | `MISSION_FAILED_MISSION_COMPROMISED` |  |
| `23` | `MISSION_FAILED_DISCONNECTED_SWARM_PLANNER` |  |
| `24` | `MISSION_FAILED_DISCONNECTED_EDGE` |  |
| `25` | `MISSION_FAILED_DISCONNECTED_AUTONOMY` |  |
| `30` | `PLANNING_WARN_VEHICLES_MISMATCH` |  |
| `31` | `PLANNING_WARN_NOT_ENOUGH_COVERAGE` |  |
| `32` | `PLANNING_WARN_DATE_COMPROMISED` |  |
| `40` | `PLANNING_FAILED_NO_SOLUTION_FOUND` |  |
| `41` | `PLANNING_FAILED` |  |

