# Architecture

C2 iMUGS2 is organized around ports and adapters so the current simple implementation can be replaced module by module.

## Dependency Direction

```text
UI / CLI / ROS2 nodes / HTTP API
  -> MissionService
  -> ports: PlannerPort, repositories, EdgeDispatcherPort
  -> adapters: file repositories, simple planner, future ROS/Mongo/actual planner clients
```

Core modules do not depend on ROS 2, MongoDB, a web UI, or a specific planner.

## Core Ports

Defined in `src/c2_imugs2/ports.py`:

- `PlannerPort`
- `AgentRepositoryPort`
- `MapRepositoryPort`
- `MissionRepositoryPort`
- `PlanRepositoryPort`
- `EdgeDispatcherPort`

Anything that implements these method signatures can be swapped in.

## Planner Swap

The current planner is `SimplePlanner`. It preserves the old planner contract:

```text
mission_config + selected agents -> task_plan JSON
```

To use the actual planner later, implement:

```python
class ActualPlanner:
    def create_plan(self, mission_config, agents):
        ...
        return task_plan
```

Then pass it into `MissionService` instead of `SimplePlanner`. The adapter should validate output with `validate_task_plan`.

Good future adapters:

- direct Python import adapter
- ROS 2 service adapter for `/multi_robot/planner/create` and `/multi_robot/planner/get_plan`
- HTTP adapter
- subprocess/container adapter

## UI/API Boundary

The current UI lives in `frontend/`. It is a React/Vite/shadcn-style client that uses fixture data and mirrors the core mission/task-plan contracts for visualization and editing.

It should stay a client adapter. When the backend API is added, the UI should call an API layer that wraps `MissionService`; it should not call repositories or planner code directly.

Suggested future API endpoints:

```text
POST /missions/init
POST /missions/{mission_id}/status
GET  /missions/{mission_id}
GET  /missions/{mission_id}/plan
GET  /agents
GET  /map/features
```

Because `MissionService` is already independent from CLI and ROS, the same service can back:

- CLI
- FastAPI/Flask UI backend
- ROS 2 node
- later LLM benchmark harness

Current frontend modules:

`frontend/src/App.tsx`
: page composition, mission editor, task-plan preview, asset panel, and quiet LLM-assistant placeholder.

`frontend/src/MapView.tsx`
: fictive map, UGV motion playback, planned trajectories, objective markers, and polygon drawing.

`frontend/src/mission.ts`
: frontend contract normalization, legacy ICD aliases, validation, and task-plan preview generation.

`frontend/src/types.ts`
: TypeScript mission, map, agent, and task-plan contract shapes.

## Module Boundaries

`domain.py`
: enums and domain dataclasses.

`mission_config.py`
: mission normalization and validation.

`planner.py`
: current simple planner adapter.

`planner_adapters.py`
: adapter helpers for external planners.

`repositories.py`
: file-backed adapter implementations.

`mission_service.py`
: mission lifecycle and orchestration.

`task_plan.py`
: task-plan creation and validation helpers.

`cli.py`
: thin command-line adapter.
