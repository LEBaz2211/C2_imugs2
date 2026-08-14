# ROS Compatibility ICD

> **Documentation label: CONTRACT**
> Stable ROS, REST, JSON, enum, and coordinate requirements. Current runtime
> architecture and behavior belong in [Architecture](ARCHITECTURE.md), not here.

## Scope And Authority

This ICD defines interfaces that the editable runtime in `backend/` and its
adapters must preserve. The embedded message and service definitions in
`legacy_ros/` are the frozen comparison evidence for the inherited interface;
they are not the current implementation target. New ROS work belongs only in
`backend/`.

The preservation and migration rules in
[PROJECT_PLANNING.md](../PROJECT_PLANNING.md) apply to every interface below.
Do not change a message layout, field type, name, enum value, topic, service, or
mission/task JSON shape without an explicit contract-migration request,
compatibility handling, tests, and documentation.

Generated documentation is a static inventory of the editable source tree. It
can help find declarations, but it does not replace this policy or prove that
an interface was observed on a running ROS graph.

## ROS Environment

```text
ROS_DOMAIN_ID=112
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

Older deployments may use `rmw_fastrtps_dynamic_cpp`; supporting it must not
alter the contracts below.

## C2 And Fog Topics

| Name | Direction | Type | Payload |
| --- | --- | --- | --- |
| `/multi_robot/mission_init_request` | C2 -> fog | `c2_msgs/msg/InitMissionRequest` | `mission_id UUID`, `mission_config string<=10000` |
| `/multi_robot/mission_init_response` | fog -> C2 | `c2_msgs/msg/InitMissionResponse` | Mission id, status, and error response fields |
| `/multi_robot/change_mission_status_request` | C2 -> fog | `c2_msgs/msg/ChangeMissionStatusRequest` | `mission_id UUID`, `mission_request_status uint8` |
| `/multi_robot/change_mission_status_response` | fog -> C2 | `c2_msgs/msg/ChangeMissionStatusResponse` | `mission_id UUID`, `mission_status uint8`, `error_message string<=2000` |
| `/multi_robot/change_mission_vehicle_request` | C2 -> fog | `c2_msgs/msg/ChangeMissionVehicleRequest` | `mission_id UUID`, vehicle ids, `vehicle_changes uint8` |
| `/multi_robot/change_mission_vehicle_response` | fog -> C2 | `c2_msgs/msg/ChangeMissionVehicleResponse` | `mission_id UUID` |
| `/multi_robot/mission_feedback` | fog -> C2 | `c2_msgs/msg/MissionFeedback` | `mission_id UUID`, `mission_feedback` JSON string |
| `/multi_robot/log` | fog/internal -> C2 | `c2_msgs/msg/SwarmLog` | `mission_id UUID`, log text, date, and type |
| `/multi_robot/swarm_log` | C2 interface | `c2_msgs/msg/SwarmLog` | Separate interface; not an alias for `/multi_robot/log` |

## Planner Services And Topics

| Name | Kind | Type | Payload |
| --- | --- | --- | --- |
| `/multi_robot/planner/create` | service | `centralized_msgs/srv/CreatePlanner` | request: `id`, `priority`, `Agent[]`, config JSON; response: `id`, `state` |
| `/multi_robot/planner/get_plan` | service | `centralized_msgs/srv/GetPlan` | request: `id`; response: `id`, plan JSON |
| `/multi_robot/planner/set_agents` | service name retained by clients | `centralized_msgs/srv/UpdatePlannerAgents` | Agent update request and planner state response |
| `/multi_robot/planner/delete` | service name retained by clients | `centralized_msgs/srv/DeletePlanner` | Planner deletion request and state response |
| `/multi_robot/planner/delete_planner` | service name provided by the inherited planner | `centralized_msgs/srv/DeletePlanner` | Planner deletion request and state response |
| `/multi_robot/planner/state` | topic | `std_msgs/msg/String` | Planner state JSON/string |
| `/multi_robot/planner/planner_calculated` | topic name retained by subscribers | `centralized_msgs/msg/PlanCalculated` | Plan-calculation notification |
| `/multi_robot/planner/agent` | topic | `centralized_msgs/msg/Agent` | Agent id, agent-profile JSON, and odometry |

The presence of a retained name in this ICD does not claim that both a client
and provider currently exist. Current topology must be checked in the generated
inventory and on the running ROS graph.

## Fleet And Edge Interfaces

| Name | Kind | Type | Payload |
| --- | --- | --- | --- |
| `multi_robot/fleet_manager/get_agents` | service | `centralized_msgs/srv/GetAgents` | requested agent ids; response `Agent[]` and error text |
| `multi_robot/fleet_manager/send_tasks` | service | `c2_msgs/srv/InitMission` | Mission id/config request and mission response |
| `multi_robot/fleet_manager/change_mission_status` | service | `c2_msgs/srv/ChangeMissionStatus` | Mission id and requested/status values |
| `/multi_robot/edge/agent_profile` | topic | `std_msgs/msg/String` | Agent-profile JSON |
| `/multi_robot/edge/feedback` | topic | `task_msgs/msg/Feedback` | Agent id, state, task feedback, and odometry |
| `multi_robot/edge/connection_check` | topic | `std_msgs/msg/String` | Heartbeat/check string |
| `multi_robot/edge/agent_<uuid>/add_task` | service | `task_msgs/srv/AddTask` | Task id/type, override, task-config JSON, and start time |
| `multi_robot/edge/agent_<uuid>/change_state` | service | `task_msgs/srv/ChangeState` | Requested state; returned state and feedback |
| `multi_robot/edge/agent_<uuid>/change_task_state` | service | `task_msgs/srv/ChangeTaskState` | Task id and requested/returned state |
| `multi_robot/edge/agent_<uuid>/cmd` | service | `std_srvs/srv/Trigger` | Development command trigger |

## Edge To Autonomy Topics

`<PREFIX>` is the configured autonomy topic prefix, for example `Themis_Fr`.

| Name | Direction | Type | Payload |
| --- | --- | --- | --- |
| `<PREFIX>/edge/multi_robot/autonomy_set_objective` | edge -> autonomy | `autonomy_msgs/msg/AutonomySetObjective` | Null flag and autonomy objective |
| `<PREFIX>/edge/multi_robot/localization` | autonomy -> edge | `nav_msgs/msg/Odometry` | Pose and twist |
| `<PREFIX>/edge/multi_robot/vehicle_profile` | autonomy -> edge | `autonomy_msgs/msg/VehicleProfile` | Vehicle state and capabilities |
| `<PREFIX>/edge/multi_robot/detected_obstacle` | autonomy -> edge | `autonomy_msgs/msg/DetectedObstacle` | Obstacle id and geofence |
| `<PREFIX>/edge/multi_robot/autonomy_status` | autonomy -> edge | `autonomy_msgs/msg/AutonomyStatus` | Objective id, status, and primitive statuses |
| `<PREFIX>/edge/multi_robot/autonomy_trajectory` | autonomy -> edge | `autonomy_msgs/msg/AutonomyTrajectory` | Trajectory JSON/GeoJSON |

## JSON Contracts

Canonical schemas:

```text
schemas/mission_config.schema.json
schemas/task_plan.schema.json
schemas/agent_profile.schema.json
schemas/map_feature.schema.json
```

Legacy input aliases are normalized at the adapter boundary:

| Legacy field | Canonical field |
| --- | --- |
| `objective.geometry` | `objective.geometries[]` |
| `objective.feature_id` | `objective.geometries[].feature_id` |
| `transit.optimalization` | `transit.optimization` |
| `transit.vehicle_constraints` | `transit.desired_vehicle_constraints` |
| `transit.desired_speed` | `transit.desired_vehicle_constraints.max_speed` |
| `objective.maximize_area_coverage` | `objective.maximize_coverage` |
| scalar `objective.vehicle_orientation` | one-item array |
| `vehicle_formation_distances` | `vehicle_formation_distance` |
| `maximize_coverage_distances` | `maximum_coverage_distances` |
| `transit.geofence_maximum_coverage` | `transit.geofence_maximize_coverage` |

The adapter translates canonical `optimization` back to inherited
`optimalization` before posting through the REST bridge.

## Numeric Enums

Mission request values:

```text
INIT=0 APPROVE=1 START=2 PAUSE=3 STOP=4 DELETE=5
```

Mission status values:

```text
NONE=0 PLANNED=1 PLANNED_ALTERNATIVE=2 PLANNED_FAILED=3 ACCEPTED=4
STARTED=5 PAUSED=6 FAILED=7 STOPPED=8 DELETED=9 COMPLETED=10
```

Mission behavior values:

```text
NAVIGATE=0 COVERAGE=1 NAVIGATE_NO_PLANNING=2
```

Numeric values are compatibility data. Do not reorder or renumber them.

## Coordinate And State Semantics

```text
GeoJSON and canonical mission coordinates: [longitude, latitude]
Leaflet marker APIs:                       [latitude, longitude]
ROS odometry:                              local pose unless explicitly converted
```

Coordinate conversion belongs in adapters, not UI mission construction.
Planner readiness is not proof of a usable mission path. A usable path is
confirmed only by mission feedback containing non-empty waypoint tasks.

## Out Of Scope

This ICD deliberately does not describe planner algorithms, scenario loading,
risk policy, coverage behavior, deployment fixes, current defects, or runtime
workarounds. Those details evolve with `backend/` and belong in
[Architecture](ARCHITECTURE.md), focused `CURRENT` documents, source, and
tests. Keep this document limited to compatibility requirements.
