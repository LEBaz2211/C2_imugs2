# `/c2_interface_node`

> **Documentation label: REFERENCE** — frozen `legacy_ros/` node evidence.

## Purpose

`/c2_interface_node` is the old fog-side ingress node for C2 messages. It subscribes to mission init/status/vehicle/environment topics and turns them into orchestrator actions.

Source:

```text
legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/c2_interface_node.cpp
legacy_ros/fog/centralized-coordination/src/centralized_coordination/include/centralized_coordination/c2_interface_header.hpp
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `/multi_robot/mission_init_request` | `c2_msgs/msg/InitMissionRequest` | New mission config JSON |
| `/multi_robot/change_mission_status_request` | `c2_msgs/msg/ChangeMissionStatusRequest` | Mission status request enum |
| `/multi_robot/change_mission_vehicle_request` | `c2_msgs/msg/ChangeMissionVehicleRequest` | Add/remove vehicles from a mission |
| `/multi_robot/environment_data_reset_request` | `environment_msgs/msg/EnvironmentDataResetRequest` | Tell missions the environment changed |
| `/multi_robot/environment_data_upload_request` | `environment_msgs/msg/EnvironmentDataUploadRequest` | Tell missions the environment changed |
| `/multi_robot/environment_data_get_version_request` | `environment_msgs/msg/EnvironmentDataGetVersionRequest` | Return current environment version |

## Outputs

| Output | Type | Notes |
| --- | --- | --- |
| In-memory `InterfaceC2State` | C++ struct | Polled by `/orchestrator_node` every 5 seconds |
| `/multi_robot/change_mission_vehicle_response` | `c2_msgs/msg/ChangeMissionVehicleResponse` | Published after vehicle change request |
| `/multi_robot/environment_data_*_response` | `environment_msgs/msg/*Response` | Published for reset/upload/version |
| `/multi_robot/swarm_log` | `c2_msgs/msg/SwarmLog` | Interface log topic |
| `/multi_robot/mission_feedback` | `c2_msgs/msg/MissionFeedback` | Publisher exists, but mission manager is the real feedback source |

The node creates `InitMissionResponse` and `ChangeMissionStatusResponse` objects in code, but the current init/status callbacks do not publish them. Status responses normally come from the dynamic mission manager.

## Internal Behavior

For mission init, the node parses `mission_config` with the generated legacy `MissionConfig` JSON parser, overwrites `MissionId` from the ROS UUID, and stores it in `InterfaceC2State` under `flag_new_mission=true`.

For mission status changes, it calls the orchestrator pointer directly:

```text
Interface::_changeMissionStatusCallback
-> OrchestratorNode::setRequestMissionChangeStatus(mission_id, request_status)
```

For vehicle changes, it stores `flag_vehicle_changes=true` so the orchestrator can pick it up on its next timer loop.

## Workflow Examples

### 1. Init Request Becomes Orchestrator State

Incoming ROS message:

```yaml
topic: /multi_robot/mission_init_request
mission_id: 11111111-2222-4333-8444-555555555555
mission_config: "{\"mission_id\":\"11111111-2222-4333-8444-555555555555\",\"behavior\":0,\"vehicles\":[\"f9992bb3-9871-451f-90a0-9207eb9fe6c5\"],\"objective\":{\"geometries\":[{\"geometry\":{\"geometry_type\":\"Point\",\"coordinates\":[4.392430,50.844050]}}]},\"transit\":{\"optimalization\":{\"road_usage\":1.0},\"desired_vehicle_constraints\":{\"max_speed\":1.3}}}"
```

Stored state for the orchestrator:

```yaml
flag_new_mission: true
mission_id: 11111111-2222-4333-8444-555555555555
mission_info.mission_config.behavior: 0
mission_info.mission_config.vehicles:
  - f9992bb3-9871-451f-90a0-9207eb9fe6c5
```

### 2. Start Request Is Forwarded Directly

Incoming ROS message:

```yaml
topic: /multi_robot/change_mission_status_request
mission_id: 11111111-2222-4333-8444-555555555555
mission_request_status: 2
```

Internal call:

```text
setRequestMissionChangeStatus("11111111-2222-4333-8444-555555555555", START)
```

The orchestrator then calls:

```text
multi_robot/mission_11111111_2222_4333_8444_555555555555/mission_status_change
```

### 3. Environment Upload Triggers Replanning

Incoming ROS message:

```yaml
topic: /multi_robot/environment_data_upload_request
request_id: 42
```

Internal action:

```text
Interface::_environmentUploadDataCallback
-> OrchestratorNode::_environmentChange()
-> every mission manager environment_change service
```

Response:

```yaml
topic: /multi_robot/environment_data_upload_response
request_id: 42
result_status: 0
```

## Gotchas

- Init/status response publishers exist, but the init and status callbacks currently build response messages without publishing them.
- Interface logs go to `/multi_robot/swarm_log`, while most other centralized nodes use `/multi_robot/log`.
- `vehicule_id_list` is misspelled in the legacy message and should be preserved for compatibility.
- The orchestrator only sees `flag_new_mission` and `flag_vehicle_changes` when it polls `getC2InterfaceStatus()`.
