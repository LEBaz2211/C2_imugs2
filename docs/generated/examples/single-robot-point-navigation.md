# One robot navigating to one Point

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

This example is generated from a checked-in runtime verification record and is linked into every extracted contract page that participates in the run.

!!! success "Runtime verified"
    The checked-in run reached planner state 2, mission PLANNED(1), and delivered a 10-waypoint route to Themis Fr.
    Source tree: `legacy_ros` · Stack: `docker-compose.legacy-ros.yml` · Evidence: [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:11`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L11)
    This run verifies the frozen compatibility reference, not the current editable backend.

## Fixed run data

| Value | Runtime data |
|---|---|
| Mission | `44444444-5555-4666-8777-888888888888` |
| Robot | `Themis Fr` · `f9992bb3-9871-451f-90a0-9207eb9fe6c5` |
| Start | `[4.392588, 50.844317]` [longitude, latitude] |
| Destination | `[4.39167, 50.84417]` [longitude, latitude] |
| Behavior | `0` (NAVIGATE) |
| Requested speed | `1.3 m/s` |
| Observed route | `10` waypoints |

## Recorded route coordinates

Only coordinates explicitly retained by the verification walkthrough are shown; the seven unrecorded intermediate points are not invented.

| Recorded position | Longitude | Latitude |
|---|---:|---:|
| first | `4.3925979` | `50.8443434` |
| second | `4.3923021488298595` | `50.8442681286928` |
| final | `4.391670213379427` | `50.84417059346137` |

## Payloads by phase

| Phase | Payload | Evidence class | Applicable extracted contracts |
|---|---|---|---|
| robot discovery | Themis agent returned to the UI adapter | `runtime_observed` | [GET /api/agents](../http/get-api-agents.md) |
| robot discovery | Canonical profile for the participating robot | `runtime_observed` | [AgentProfile](../schemas/agent-profile.md) |
| robot discovery | Edge publishes the participating robot profile | `observed_excerpt` | [/multi_robot/edge/agent_profile](../ros-topics/multi-robot-edge-agent-profile.md) |
| robot discovery | Autonomy publishes the Themis vehicle profile | `runtime_observed` | [autonomy_msgs/msg/VehicleProfile](../ros-types/autonomy-msgs-msg-vehicleprofile.md)<br>[autonomy_msgs/msg/VehicleConstraints](../ros-types/autonomy-msgs-msg-vehicleconstraints.md)<br>[autonomy_msgs/msg/VehicleInfo](../ros-types/autonomy-msgs-msg-vehicleinfo.md)<br>[autonomy_msgs/msg/SensorProperties](../ros-types/autonomy-msgs-msg-sensorproperties.md) |
| robot discovery | Fleet forwards Themis and its live pose to Planner | `observed_excerpt` | [/multi_robot/planner/agent](../ros-topics/multi-robot-planner-agent.md)<br>[centralized_msgs/msg/Agent](../ros-types/centralized-msgs-msg-agent.md) |
| planning | Mission manager requests the configured Themis agent | `verified_flow` | [multi_robot/fleet_manager/get_agents](../ros-services/multi-robot-fleet-manager-get-agents.md)<br>[centralized_msgs/srv/GetAgents](../ros-types/centralized-msgs-srv-getagents.md) |
| INIT | Canonical mission submitted to the adapter | `verified_flow` | [POST /api/missions/init](../http/post-api-missions-init.md)<br>[MissionConfig](../schemas/mission-config.md) |
| APPROVE | Approve the planned mission | `verified_flow` | [POST /api/missions/{mission_id}/approve](../http/post-api-missions-mission-id-approve.md) |
| START | Start the accepted mission | `verified_flow` | [POST /api/missions/{mission_id}/start](../http/post-api-missions-mission-id-start.md) |
| INIT | Mission initialization on ROS | `verified_flow` | [/multi_robot/mission_init_request](../ros-topics/multi-robot-mission-init-request.md)<br>[c2_msgs/msg/InitMissionRequest](../ros-types/c2-msgs-msg-initmissionrequest.md)<br>[c2_msgs/srv/InitMission](../ros-types/c2-msgs-srv-initmission.md) |
| APPROVE | APPROVE status request | `verified_flow` | [/multi_robot/change_mission_status_request](../ros-topics/multi-robot-change-mission-status-request.md)<br>[c2_msgs/msg/ChangeMissionStatusRequest](../ros-types/c2-msgs-msg-changemissionstatusrequest.md)<br>[c2_msgs/srv/ChangeMissionStatus](../ros-types/c2-msgs-srv-changemissionstatus.md)<br>[multi_robot/fleet_manager/change_mission_status](../ros-services/multi-robot-fleet-manager-change-mission-status.md) |
| START | START status request | `verified_flow` | [/multi_robot/change_mission_status_request](../ros-topics/multi-robot-change-mission-status-request.md)<br>[c2_msgs/msg/ChangeMissionStatusRequest](../ros-types/c2-msgs-msg-changemissionstatusrequest.md)<br>[c2_msgs/srv/ChangeMissionStatus](../ros-types/c2-msgs-srv-changemissionstatus.md)<br>[multi_robot/fleet_manager/change_mission_status](../ros-services/multi-robot-fleet-manager-change-mission-status.md) |
| APPROVE | Mission manager accepts the APPROVE transition | `verified_flow` | [/multi_robot/change_mission_status_response](../ros-topics/multi-robot-change-mission-status-response.md)<br>[c2_msgs/msg/ChangeMissionStatusResponse](../ros-types/c2-msgs-msg-changemissionstatusresponse.md)<br>[c2_msgs/srv/ChangeMissionStatus](../ros-types/c2-msgs-srv-changemissionstatus.md) |
| START | Mission manager accepts the START transition | `verified_flow` | [/multi_robot/change_mission_status_response](../ros-topics/multi-robot-change-mission-status-response.md)<br>[c2_msgs/msg/ChangeMissionStatusResponse](../ros-types/c2-msgs-msg-changemissionstatusresponse.md)<br>[c2_msgs/srv/ChangeMissionStatus](../ros-types/c2-msgs-srv-changemissionstatus.md) |
| planning | Create the planner for the mission | `verified_flow` | [/multi_robot/planner/create](../ros-services/multi-robot-planner-create.md)<br>[centralized_msgs/srv/CreatePlanner](../ros-types/centralized-msgs-srv-createplanner.md) |
| planning | Planner reports that the plan cache is ready | `runtime_observed` | [/multi_robot/planner/state](../ros-topics/multi-robot-planner-state.md) |
| plan retrieval | Observed 10-waypoint plan (recorded coordinate excerpt) | `observed_excerpt` | [TaskPlan](../schemas/task-plan.md) |
| plan retrieval | Retrieve the generated robot task | `observed_excerpt` | [/multi_robot/planner/get_plan](../ros-services/multi-robot-planner-get-plan.md)<br>[centralized_msgs/srv/GetPlan](../ros-types/centralized-msgs-srv-getplan.md) |
| PLANNED | Mission feedback proving that a route was received | `observed_excerpt` | [/multi_robot/mission_feedback](../ros-topics/multi-robot-mission-feedback.md)<br>[c2_msgs/msg/MissionFeedback](../ros-types/c2-msgs-msg-missionfeedback.md) |
| APPROVE | Fleet installs the stopped waypoint task on Themis | `observed_excerpt` | [multi_robot/edge/agent_{agent_id}/add_task](../ros-services/multi-robot-edge-agent-agent-id-add-task.md)<br>[task_msgs/srv/AddTask](../ros-types/task-msgs-srv-addtask.md) |
| APPROVE | Mission manager asks Fleet to dispatch the stored plan | `verified_flow` | [multi_robot/fleet_manager/send_tasks](../ros-services/multi-robot-fleet-manager-send-tasks.md)<br>[c2_msgs/srv/InitMission](../ros-types/c2-msgs-srv-initmission.md) |
| START | Fleet starts the installed Themis task | `verified_flow` | [task_msgs/srv/ChangeTaskState](../ros-types/task-msgs-srv-changetaskstate.md) |
| execution | Edge sends the current waypoint to autonomy | `observed_excerpt` | [autonomy_msgs/msg/AutonomySetObjective](../ros-types/autonomy-msgs-msg-autonomysetobjective.md)<br>[autonomy_msgs/msg/AutonomyObjective](../ros-types/autonomy-msgs-msg-autonomyobjective.md) |
| COMPLETED | Themis reports completion after the final waypoint | `verified_flow` | [/multi_robot/edge/feedback](../ros-topics/multi-robot-edge-feedback.md)<br>[task_msgs/msg/Feedback](../ros-types/task-msgs-msg-feedback.md)<br>[task_msgs/msg/TaskFeedback](../ros-types/task-msgs-msg-taskfeedback.md) |

## Provenance rules

- `runtime_observed`: the concrete value was recorded from the running system or its runtime configuration.
- `verified_flow`: the payload follows the exercised runtime path and extracted contract; generated identifiers remain labelled.
- `observed_excerpt`: the checked-in verification retained only part of a larger runtime payload.

Example record: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1)
