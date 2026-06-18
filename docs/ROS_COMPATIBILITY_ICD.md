# ROS Compatibility ICD

This document maps the old multi-agent framework ROS interfaces that must stay compatible while `c2_imugs2` is rebuilt. The runnable source of truth is the vendored old ROS code in `legacy_ros/`, especially the embedded message packages under each fog/planner/edge package.

## Runtime Approach

Run the actual old ROS stack through Docker from this repository:

```bash
docker compose -f docker-compose.legacy-ros.yml up --build
```

That compose file builds these old packages directly from `legacy_ros/`:

- `legacy_ros/fog/centralized-coordination`
- `legacy_ros/fog/planner`
- `legacy_ros/fog/command-control` ROS REST/rosbridge image
- `legacy_ros/edge/agent-tasks-supervisor`

The new Python core remains separate. Later, it should integrate through real ROS adapters or service clients, not through a simulated runtime.

## ROS Environment

The legacy stack mostly targets ROS 2 Humble in Docker, with some older launch scripts still sourcing Galactic. The compatibility target is:

```text
ROS_DOMAIN_ID=112
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

Old launch scripts sometimes use `rmw_fastrtps_dynamic_cpp`; keep that as a deployment option if integrating with old containers.

## Old Runtime Nodes

| Area | Legacy node/package | Role |
| --- | --- | --- |
| C2 interface | `centralized_coordination/c2_interface_node.cpp` | Mission init/status JSON ingress and feedback egress |
| Orchestrator | `centralized_coordination/orchestrator_node.cpp` | Mission lifecycle command/delete/log coordination |
| Mission manager | `centralized_coordination/mission_manager.cpp` | Per-mission planning and task dispatch orchestration |
| Fleet manager | `centralized_coordination/fleet_manager_node.cpp` | Agent registry, edge task dispatch, edge feedback |
| Planner | `planner/planner_node.py` | Old path planner service |
| Edge supervisor | `agent_tasks_supervisor_node.cpp` | Per-agent AddTask/ChangeState compatibility |
| Autonomy sim | `test_autonomy.cpp` | Optional mock autonomy status/localization source |

## C2 And Fog Topics

| Name | Direction | Type | Payload |
| --- | --- | --- | --- |
| `/multi_robot/mission_init_request` | C2 -> fog | `c2_msgs/msg/InitMissionRequest` | `mission_id UUID`, `mission_config string<=10000` |
| `/multi_robot/mission_init_response` | fog -> C2 | `c2_msgs/msg/InitMissionResponse` | `mission_id UUID`, `mission_feedback string<=10000` |
| `/multi_robot/change_mission_status_request` | C2 -> fog | `c2_msgs/msg/ChangeMissionStatusRequest` | `mission_id UUID`, `mission_request_status uint8` |
| `/multi_robot/change_mission_status_response` | fog -> C2 | `c2_msgs/msg/ChangeMissionStatusResponse` | `mission_id UUID`, `mission_status uint8`, `error_message string<=2000` |
| `/multi_robot/change_mission_vehicle_request` | C2 -> fog | `c2_msgs/msg/ChangeMissionVehicleRequest` | `mission_id UUID`, `vehicule_id_list`, `vehicle_changes uint8` |
| `/multi_robot/change_mission_vehicle_response` | fog -> C2 | `c2_msgs/msg/ChangeMissionVehicleResponse` | `mission_id UUID` |
| `/multi_robot/mission_feedback` | fog -> C2 | `c2_msgs/msg/MissionFeedback` | `mission_id UUID`, `mission_feedback JSON string` |
| `/multi_robot/log` | internal/fog -> C2 | `c2_msgs/msg/SwarmLog` | `mission_id UUID`, `log`, `date`, `log_type uint8` |
| `/multi_robot/swarm_log` | C2 interface alias | `c2_msgs/msg/SwarmLog` | same as `/multi_robot/log` |

## Planner Services And Topics

| Name | Kind | Type | Payload |
| --- | --- | --- | --- |
| `/multi_robot/planner/create` | service | `centralized_msgs/srv/CreatePlanner` | request: `id`, `priority`, `Agent[]`, `config JSON`; response: `id`, `state` |
| `/multi_robot/planner/get_plan` | service | `centralized_msgs/srv/GetPlan` | request: `id`; response: `id`, `plan JSON` |
| `/multi_robot/planner/set_agents` | service | `centralized_msgs/srv/UpdatePlannerAgents` | request: `id`, `Agent[]`; response: `id` |
| `/multi_robot/planner/delete` | service | `centralized_msgs/srv/DeletePlanner` | request: `id`; response: `id`, `state` |
| `/multi_robot/planner/delete_planner` | service | `centralized_msgs/srv/DeletePlanner` | active planner variant; keep as alias |
| `/multi_robot/planner/state` | topic | `std_msgs/msg/String` | planner state JSON/string |
| `/multi_robot/planner/planner_calculated` | topic | `centralized_msgs/msg/PlanCalculated` | `id`, `plan JSON` |
| `/multi_robot/planner/agent` | topic | `centralized_msgs/msg/Agent` | active planner package uses `agent_id string`, `agent_profile JSON`, `nav_msgs/Odometry` |

## Fleet And Edge Services

| Name | Kind | Type | Payload |
| --- | --- | --- | --- |
| `multi_robot/fleet_manager/get_agents` | service | `centralized_msgs/srv/GetAgents` | request: `agent_id_list`; response: `Agent[]`, `error_message` |
| `multi_robot/fleet_manager/send_tasks` | service | `c2_msgs/srv/InitMission` | request: mission/task JSON; response: mission feedback |
| `multi_robot/fleet_manager/change_mission_status` | service | `c2_msgs/srv/ChangeMissionStatus` | request: mission id + status; response: status |
| `/multi_robot/edge/agent_profile` | topic | `std_msgs/msg/String` | agent profile JSON |
| `/multi_robot/edge/feedback` | topic | `task_msgs/msg/Feedback` | `agent_id`, `state`, `TaskFeedback[]`, localization, speed |
| `multi_robot/edge/connection_check` | topic | `std_msgs/msg/String` | heartbeat/check string |
| `multi_robot/edge/agent_<uuid>/add_task` | service | `task_msgs/srv/AddTask` | `task_id`, `task_type`, `override`, `task_config JSON`, `std` |
| `multi_robot/edge/agent_<uuid>/change_state` | service | `task_msgs/srv/ChangeState` | `requested_state -> state + feedback` |
| `multi_robot/edge/agent_<uuid>/change_task_state` | service | `task_msgs/srv/ChangeTaskState` | `task_id`, requested state -> state |
| `multi_robot/edge/agent_<uuid>/cmd` | service | `std_srvs/srv/Trigger` | command trigger |

## Edge To Autonomy Topics

`AUTONOMY_TOPIC_PREFIX` examples in the old stack include `Themis_Fr`, `Themis_Ge`, and `Themis_Es`.

| Name | Direction | Type | Payload |
| --- | --- | --- | --- |
| `<PREFIX>/edge/multi_robot/autonomy_set_objective` | edge -> autonomy | `autonomy_msgs/msg/AutonomySetObjective` | `null_objective`, `AutonomyObjective` |
| `<PREFIX>/edge/multi_robot/localization` | autonomy -> edge | `nav_msgs/msg/Odometry` | pose/twist |
| `<PREFIX>/edge/multi_robot/vehicle_profile` | autonomy -> edge | `autonomy_msgs/msg/VehicleProfile` | vehicle state/capabilities |
| `<PREFIX>/edge/multi_robot/detected_obstacle` | autonomy -> edge | `autonomy_msgs/msg/DetectedObstacle` | obstacle id + geofence |
| `<PREFIX>/edge/multi_robot/autonomy_status` | autonomy -> edge | `autonomy_msgs/msg/AutonomyStatus` | objective status, ETA, distance, energy, blockages |
| `<PREFIX>/edge/multi_robot/autonomy_trajectory` | autonomy -> edge | `autonomy_msgs/msg/AutonomyTrajectory` | trajectory JSON/GeoJSON |

## JSON ICDs

The new canonical schemas are:

```text
schemas/mission_config.schema.json
schemas/task_plan.schema.json
schemas/agent_profile.schema.json
schemas/map_feature.schema.json
```

Old JSON snippets are normalized before planning:

| Old field | New field |
| --- | --- |
| `objective.geometry` | `objective.geometries[]` |
| `objective.geometry.feature_id` | `objective.geometries[].feature_id` |
| `transit.optimalization` | `transit.optimization` |
| `transit.vehicle_constraints` | `transit.desired_vehicle_constraints` |
| `transit.desired_speed` | `transit.desired_vehicle_constraints.max_speed` |
| `objective.maximize_area_coverage` | `objective.maximize_coverage` |
| scalar `objective.vehicle_orientation` | one-item array |

## Planner Algorithms To Preserve

The old planner algorithms should be wrapped behind `PlannerPort`, not imported throughout the app:

| Algorithm area | Legacy source |
| --- | --- |
| Mission interpretation and feature lookup | `submodules/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py` |
| A*/CBS/risk-weighted graph search | `path_planning_lib/mapf.py` |
| Graph utilities | `path_planning_lib/graph.py`, `path_planning_lib/utils.py` |
| Hungarian / mTSP allocation | `path_planning_lib/task_allocation.py` |
| Coverage spread | `path_planning_lib/max_coverage.py` |
| Older algorithm sketches | `planner/tools/a_star.py`, `hungarian.py`, `bresenham.py`, `rdp.py`, `geographic_computation.py` |
| Edge task execution model | `agent_tasks_supervisor_node.cpp` |

## Compatibility Notes

- Active embedded message packages differ from root `custom-msgs` in places. Prefer the message packages colocated with `centralized_coordination`, `planner`, and `agent_tasks_supervisor`.
- The old planner depends on MongoDB map collections. The new replacement defaults to fixture-backed map repositories; a Mongo adapter should be added behind `MapRepositoryPort`.
- `docker-compose.legacy-ros.yml` intentionally runs the old ROS code as-is. Any failures there are real legacy build/runtime problems to fix in the old package or in a copied/ported ROS workspace, not hidden by a compatibility simulator.
