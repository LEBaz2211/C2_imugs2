# `/orchestrator_node`

## Purpose

`/orchestrator_node` owns mission lifecycle at the fog level. It registers mission configs in MongoDB, creates one dynamic mission manager node per mission, routes status/environment/vehicle changes, and records swarm logs.

Source:

```text
legacy_ros/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp
legacy_ros/fog/centralized-coordination/src/centralized_coordination/include/centralized_coordination/orchestrator_header.hpp
```

## Inputs

| Input | Type | Meaning |
| --- | --- | --- |
| `InterfaceC2State` from `/c2_interface_node` | in-process C++ state | New missions and vehicle changes |
| `multi_robot/delete_mission` | `c2_msgs/srv/ChangeMissionStatus` | Delete mission config from DB |
| `/multi_robot/log` | `c2_msgs/msg/SwarmLog` | Logs from mission/fleet/orchestrator |

## Outputs

| Output | Type | Meaning |
| --- | --- | --- |
| Dynamic `/mission_<id>` node | `MissionManager` | Runtime manager for one mission |
| `RuntimeDB.MissionConfig` | Mongo collection | Mission JSON storage |
| `RuntimeDB.Logs` | Mongo collection | Swarm log history |
| `multi_robot/mission_<id>/mission_status_change` client | `c2_msgs/srv/ChangeMissionStatus` | Route status requests |
| `multi_robot/mission_<id>/environment_change` client | `std_srvs/srv/Trigger` | Ask mission to replan |
| `multi_robot/mission_<id>/vehicle_change` client | `std_srvs/srv/Trigger` | Ask mission to replan with changed vehicles |

## Internal Behavior

The orchestrator runs a 5 second timer. On the first loop it recovers mission ids already present in MongoDB and recreates mission manager nodes. On every loop it polls `c2_interface_node`, then:

- adds or updates mission config when `flag_new_mission=true`,
- creates a `MissionManager` node if needed,
- adds/removes vehicles in mission config when `flag_vehicle_changes=true`,
- calls the mission manager's vehicle-change service after vehicle DB updates.

Mission manager nodes are spun in detached threads.

## Workflow Examples

### 1. New Mission Creates A Dynamic Mission Node

Input from `c2_interface_node`:

```yaml
flag_new_mission: true
mission_id: 11111111-2222-4333-8444-555555555555
mission_config.behavior: 0
mission_config.vehicles:
  - f9992bb3-9871-451f-90a0-9207eb9fe6c5
```

Actions:

```text
1. RuntimeDB.MissionConfig upsert by mission_id.
2. Create MissionManager("11111111_2222_4333_8444_555555555555", false).
3. Create clients to:
   multi_robot/mission_11111111_2222_4333_8444_555555555555/mission_status_change
   multi_robot/mission_11111111_2222_4333_8444_555555555555/environment_change
   multi_robot/mission_11111111_2222_4333_8444_555555555555/vehicle_change
```

### 2. Start Request Is Routed To The Mission Manager

Input from `c2_interface_node`:

```yaml
mission_id: 11111111-2222-4333-8444-555555555555
mission_request_status: 2
```

Service request sent by orchestrator:

```yaml
service: multi_robot/mission_11111111_2222_4333_8444_555555555555/mission_status_change
mission_id: 11111111-2222-4333-8444-555555555555
mission_request_status: 2
```

The mission manager converts request `2` to mission status `STARTED=5`.

### 3. Vehicle Change Updates Mission Config

Input from `c2_interface_node`:

```yaml
mission_id: 11111111-2222-4333-8444-555555555555
vehicle_changes: 1
vehicule_id_list:
  - 22222222-3333-4444-8555-666666666666
```

Actions:

```text
1. Add vehicle to RuntimeDB.MissionConfig.vehicles.
2. Call multi_robot/mission_11111111_2222_4333_8444_555555555555/vehicle_change.
3. Mission manager pauses and marks replanning needed.
```

## Gotchas

- The 5 second timer means mission creation from C2 can feel delayed.
- The orchestrator has a delete-planner client for `multi_robot/planner/delete`, but the active planner node exposes `/multi_robot/planner/delete_planner`.
- Mission deletion removes the mission config from MongoDB, but the dynamic mission manager node is not fully torn down.
- `getMissionStatus()` reads a `"status"` object from the mission DB; depending on stored JSON shape, status responses can lag or be incomplete.

