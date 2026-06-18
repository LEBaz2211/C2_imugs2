# Prompt For The Replacement-System Agent

You are building a clean replacement for an old multi-robot C2 / fog coordination / planner / edge-supervisor system.

The long-term purpose of the new system is to support **LLM benchmarking**: later, LLMs will be evaluated on whether they can turn natural-language mission requests into valid multi-robot `mission_config` JSON by using the framework's map, vehicle, mission, and planner context.

However, your first task is **not** to build the benchmark harness. Your first task is to rebuild the underlying multi-robot framework so it works like the old one, but cleanly:

```text
C2 submits mission_config JSON
-> fog/orchestrator stores and manages mission
-> mission manager requests a plan
-> planner returns per-agent task JSON
-> mission feedback is published
-> fleet manager sends tasks to edge agents
-> edge agents publish feedback and send objectives to autonomy
```

Once this replacement works, benchmarking can be added on top of it.

## Your Source Material

You do **not** have the full old repository as something to continue developing. You only have a curated set of legacy files that were deemed useful. These files exist only to inform and inspire your new implementation.

Treat the extracted legacy code as:

- examples of old behavior,
- interface references,
- schema references,
- mission/task examples,
- planner algorithm sketches,
- map and vehicle fixtures.

Do **not** treat it as:

- production code,
- a base to refactor,
- an architecture to preserve line-for-line,
- a source tree to patch until it works.

You must redo the implementation in a new, coherent structure. Reuse concepts and contracts, not the old code organization.

The old codebase is messy and inconsistent. Preserve useful behavior, interfaces, schemas, examples, and planner ideas. Rebuild everything else cleanly.

Run this first:

```bash
scripts/extract_relevant_legacy_context.sh
```

It creates `new_codebase_legacy_context_bundle/` with the relevant old files. Use that bundle instead of exploring the full old repo.

## Design Pressure From Future LLM Benchmarking

Even though you should not build the benchmark yet, design the replacement so that it can later support it easily.

That means:

- `mission_config` must have a canonical schema.
- planner output task JSON must have a canonical schema.
- map features and vehicle profiles must be queryable through clean interfaces.
- examples must be strict JSON, not informal JavaScript-style JSON.
- mission parsing and validation must be testable without ROS.
- planner core should be callable outside ROS.
- ROS nodes should be adapters around tested core logic.

The future benchmark will likely call the core system like this:

```text
natural language -> LLM-generated mission_config -> validation -> planning -> task plan
```

Your current job is to build the reliable `validation -> planning -> task plan -> ROS execution bridge` part.

## Old System Roles

### C2 / Command-Control

Old responsibility:

- Create/store map features.
- Create/store mission configs.
- Send mission init/status requests to ROS.

Relevant code:

```text
submodules/fog/command-control/src/backend/mongodb-server/mongodb-server.js
submodules/fog/command-control/src/backend/ros2-rest-api/ros2_ws/src/c2_ros2_rest_api/src/MissionHandler.cpp
submodules/fog/command-control/src/frontend/react-app/src/MissionTabs.js
```

Replacement:

- Provide a simple API or CLI to submit `mission_config`.
- UI can wait.
- Keep map/mission storage behavior, but hide storage behind repository interfaces.

### Orchestrator

Old responsibility:

- Receive new missions from C2 interface.
- Store mission config.
- Create/recover one mission manager per mission.
- Route mission status and vehicle changes.

Relevant code:

```text
submodules/fog/centralized-coordination/src/centralized_coordination/src/orchestrator_node.cpp
```

Replacement:

- Keep same role.
- Avoid fragile detached thread-per-mission design if possible.
- Keep mission recovery if persistence is enabled.

### Mission Manager

Old responsibility:

- Own mission state.
- Load mission config.
- Ask fleet manager for agents.
- Create planner.
- Request plan.
- Save planning result.
- Build mission feedback from planner task JSON.
- On approve/start, ask fleet manager to send/execute tasks.

Relevant code:

```text
submodules/fog/centralized-coordination/src/centralized_coordination/src/mission_manager.cpp
```

Replacement:

- This is the main behavior to reproduce.
- Implement mission state transitions explicitly and test them.

### Fleet Manager

Old responsibility:

- Track edge agent profiles and feedback.
- Provide selected agent states to mission manager/planner.
- Publish agent state to planner.
- Send task JSON to each edge agent.
- Send task state changes.

Relevant code:

```text
submodules/fog/centralized-coordination/src/centralized_coordination/src/fleet_manager_node.cpp
```

Replacement:

- Keep agent tracking and task dispatch.
- Separate mission status from task status; the old code conflates them.

### Planner

Old responsibility:

- Receive mission config and agent states.
- Resolve objective `feature_id`s.
- Build/load map graph.
- Allocate goals to agents.
- Plan paths.
- Emit task-plan JSON.

Relevant code:

```text
submodules/fog/planner/ros2ws/src/planner/planner/planner_node.py
submodules/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py
submodules/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/mapf.py
submodules/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/task_allocation.py
submodules/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/graph.py
submodules/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/utils.py
```

Replacement:

- Keep planner service boundary.
- Move parsing/planning/task JSON generation into tested core code.
- ROS planner node should be thin glue.
- Start with simple point navigation and independent A*; add coverage/CBS later.

### Edge Agent Supervisor

Old responsibility:

- Receive `AddTask`.
- Parse task JSON into objectives/primitives.
- Publish current autonomy objective or null objective.
- Detect waypoint/objective completion.
- Publish task feedback.

Relevant code:

```text
submodules/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/agent_tasks_supervisor_node.cpp
```

Replacement:

- Keep primitive/objective task model.
- Add schema validation before accepting task JSON.
- An edge mock is enough for the first working system.

## Mission Config Contract

Mission config is the operator intent sent by C2.

Keep these fields:

```text
mission_id
behavior
vehicles
start optional
transit optional
objective required
mission_end_time optional
```

Behavior enum:

```text
0 NAVIGATE
1 COVERAGE
2 NAVIGATE_NO_PLANNING, optional legacy value
```

Vehicle formation enum:

```text
0 NONE
1 COLUMN
2 LINE
3 WEDGE
4 VEE
5 LEFT_FLANK
6 RIGHT_FLANK
```

Important warning:

The old repo has two objective shapes:

```text
objective.geometry       old examples
objective.geometries[]   newer README/frontend/planner path
```

Use `objective.geometries[]` in the replacement. Add a compatibility importer for old `objective.geometry`.

A geometry entry is either:

```json
{"feature_id": "feature-uuid"}
```

or:

```json
{"geometry": {"geometry_type": "Point", "coordinates": [4.3918, 50.8441]}}
```

Useful old schema references:

```text
submodules/fog/centralized-coordination/src/message_packages/c2_msgs/json/MissionConfig.hpp
submodules/fog/centralized-coordination/src/message_packages/c2_msgs/json/Enums.hpp
submodules/fog/centralized-coordination/src/message_packages/c2_msgs/test/Data
submodules/fog/centralized-coordination/test/json_backups/mission_config_backups
```

Known schema cleanup:

- Prefer `optimization`; accept old `optimalization`.
- Normalize `vehicle_formation_distance` / `vehicle_formation_distances`.
- Strict JSON only; old examples may contain comments.

## Task Plan Contract

Planner output is task JSON sent to edge agents:

```text
mission_id
tasks:
  agent_id:
    task_id
    primitives[]
    objectives[]
```

Primitive fields:

```text
primitive_id
primitive_type, e.g. waypoint
continuous
primitive_inputs
primitive_outputs
completion:
  ends_objective
  ends_task
  followed_by_primitives
  inherit_other_primitives
  resume_after
```

Objective fields:

```text
objective_id
objective_type
parallel_execution
primitives:
  primitive_id
  parameters
```

Waypoint parameters used by old planner/edge:

```text
coordinates: [lon, lat]
speed
max_speed
mobility_profile
wait_time
```

Useful old references:

```text
submodules/fog/planner/ros2ws/src/planner/planner/planner_node.py        # path_to_plan_json
submodules/fog/planner/ros2ws/src/planner/planner/tasks.json
submodules/edge/agent-tasks-supervisor/ros2ws/src/agent_tasks_supervisor/src/test/json_example/planning_result.json
submodules/edge/agent-tasks-supervisor/ros2ws/src/message_packages/autonomy_msgs/json/tasks
```

## ROS Interfaces To Preserve

Consolidate old duplicated message packages into one clean ROS interface package.

### C2 / Fog

Old files:

```text
c2_msgs/srv/InitMission.srv
c2_msgs/srv/ChangeMissionStatus.srv
c2_msgs/srv/ChangeMissionVehicle.srv
c2_msgs/msg/MissionFeedback.msg
c2_msgs/msg/SwarmLog.msg
```

Key service shapes:

```text
InitMission:
  UUID mission_id
  string mission_config
  ---
  UUID mission_id
  string mission_feedback

ChangeMissionStatus:
  UUID mission_id
  uint8 mission_request_status
  ---
  UUID mission_id
  uint8 mission_status
  string error_message
```

Mission status:

```text
0 NONE
1 PLANNED
2 PLANNED_ALTERNATIVE
3 PLANNED_FAILED
4 ACCEPTED
5 STARTED
6 PAUSED
7 FAILED
8 STOPPED
9 DELETED
10 COMPLETED
```

Mission requests:

```text
0 INIT
1 APPROVE
2 START
3 PAUSE
4 STOP
5 DELETE
```

### Fog / Planner

Old files:

```text
centralized_msgs/srv/CreatePlanner.srv
centralized_msgs/srv/GetPlan.srv
centralized_msgs/srv/DeletePlanner.srv
centralized_msgs/msg/Agent.msg
```

Actual planner node implements:

```text
/multi_robot/planner/create
/multi_robot/planner/get_plan
/multi_robot/planner/delete_planner
/multi_robot/planner/state
/multi_robot/planner/agent
```

Old `Agent`:

```text
string agent_id
string agent_profile
nav_msgs/Odometry odometry
```

### Fog / Edge

Old files:

```text
task_msgs/srv/AddTask.srv
task_msgs/srv/ChangeState.srv
task_msgs/srv/ChangeTaskState.srv
task_msgs/msg/Feedback.msg
task_msgs/msg/TaskFeedback.msg
```

Old `AddTask` carries task JSON:

```text
string task_id
uint8 task_type
bool override
string task_config
string std
---
string task_id
uint8 task_state
```

### Edge / Autonomy

Old files:

```text
autonomy_msgs/msg/AutonomySetObjective.msg
autonomy_msgs/msg/AutonomyObjective.msg
autonomy_msgs/msg/AutonomyStatus.msg
autonomy_msgs/msg/AutonomyPrimitiveStatus.msg
autonomy_msgs/msg/VehicleProfile.msg
autonomy_msgs/action/SetObjective.action
```

Old supervisor uses topics, not the action, for objectives.

## Data And Persistence

Old Mongo collections:

```text
RuntimeDB.MissionConfig
RuntimeDB.Planning
RuntimeDB.ConnectedVehicles
RuntimeDB.MissionFeedback
RuntimeDB.Logs
VehicleDB.Vehicles
MapDB.<feature collections>
```

Replacement:

- Use repository interfaces.
- MongoDB is OK in Docker/full runtime.
- Tests should also work from fixture files.

Important map fixture paths:

```text
docker-compose-dir/Single-Robotnik-Full-Stack/data/map/rma
docker-compose-dir/Single-Robotnik-Full-Stack/data/map/estonia
docker-compose-dir/Single-Robotnik-Full-Stack/data/map/geojson_examples
submodules/fog/centralized-coordination/test/json_input/c2_sim/geojson
```

Map features should support:

```text
feature_id
feature_type
geometry
properties
```

## Planner Pieces Worth Reusing As Code Reference

Use these ideas:

- `TaskAllocator.hungarian_allocation`
- `TaskAllocator.solve_mtsp`
- A* shortest path with risk-weighted edges
- graph generation from LineString and Polygon
- risk polygon edge tagging
- GeoJSON and distance utilities

Do not reuse directly without cleanup:

- CBS implementation
- coverage behavior
- planner ROS node as core logic
- plotting/image publication
- live OSM downloads in tests
- direct Mongo access inside planner core

## Suggested New Repo Shape

```text
new-system/
  schemas/
    mission_config.schema.json
    task_plan.schema.json
  core/
    mission/
    planning/
    repositories/
    task_plan/
  ros2_ws/src/
    mrf_msgs/
    fog_orchestrator/
    mission_manager/
    fleet_manager/
    planner_node/
    edge_supervisor/
    edge_mock/
  fixtures/
    missions/
    maps/
    agents/
  docker-compose.yml
  tests/
```

## Build Order

1. Define mission and task-plan schemas.
2. Normalize old mission/task examples.
3. Implement repositories for missions, plans, agents, and map features.
4. Implement mission parser/validator.
5. Implement task-plan model.
6. Implement simple planner:
   - feature lookup
   - point allocation
   - waypoint task-plan output
7. Add ROS message package.
8. Add planner node.
9. Add orchestrator/mission manager/fleet manager.
10. Add edge mock or edge supervisor.
11. Add Docker Compose.

## Minimal Working Replacement

The first successful version should:

1. Start through Docker Compose.
2. Accept `InitMission` with mission config JSON.
3. Store the mission.
4. Request a plan.
5. Return valid task-plan JSON.
6. Publish mission feedback.
7. Accept `APPROVE` and `START`.
8. Send task JSON to an edge mock/supervisor.
9. Edge publishes feedback.

Only after this works should LLM benchmarking be added.

## Legacy Problems To Avoid

- Duplicate message packages.
- Inconsistent mission schema.
- Non-strict JSON examples.
- `optimalization` spelling.
- Planner core mixed with ROS, MongoDB, OSM, and plotting.
- Incomplete CBS and coverage logic.
- Mission status and task status conflation.
- Documented interfaces that are not actually implemented.
