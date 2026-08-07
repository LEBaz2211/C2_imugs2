# C2 iMUGS2

This repository keeps the original multi-robot C2/fog/planner/edge system runnable while building a cleaner UI and backend boundary around it. The current operational path uses the actual vendored legacy ROS 2 nodes; the replacement core remains available for modular development and tests.

Before changing architecture or compatibility behavior, read [Project Planning](PROJECT_PLANNING.md). In particular, legacy code and message contracts should remain unchanged unless a task explicitly requires a compatibility-preserving legacy fix.

## Current Runtime

```text
Browser UI (React, Vite, Leaflet)
  -> FastAPI adapter at http://localhost:8000/api/*
  -> legacy REST bridge at http://localhost:5001/mission_control
  -> rosbridge at ws://localhost:9090
  -> actual legacy ROS fog, planner, fleet, edge, and autonomy nodes
```

The browser uses JSON over HTTP and SSE. ROS message construction, legacy aliases, coordinate conversion, and runtime normalization stay in the backend adapter.

## Run It

Start the legacy ROS stack:

```bash
docker compose -f docker-compose.legacy-ros.yml up --build
./scripts/check_legacy_ros_stack.sh
```

Or start the initially identical, editable backend fork instead (the two ROS
stacks cannot run together):

```bash
docker compose -f docker-compose.backend.yml up --build
./scripts/check_backend_ros_stack.sh
```

Start the API and UI:

```bash
docker compose up -d --build c2-imugs2-api c2-imugs2-ui
```

Open `http://localhost:5173`. Useful checks:

```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool
curl -s http://localhost:8000/api/diagnostics | python3 -m json.tool
curl -s http://localhost:8000/api/legacy/trace | python3 -m json.tool
```

## Repository Areas

| Path | Purpose |
| --- | --- |
| `src/c2_imugs2/` | FastAPI adapter, mission normalization, ROS/REST adapters, maps, and modular replacement core |
| `frontend/` | Operator UI, mission composer, Leaflet map, diagnostics, and live state |
| `backend/` | Editable full-source fork of the legacy ROS backend |
| `legacy_ros/` | Actual copied legacy ROS code used by the compatibility runtime |
| `schemas/` | Canonical mission, task-plan, agent, and map-feature contracts |
| `docs/legacy_nodes/` | Detailed inputs, outputs, behavior, and examples for each legacy node |
| `data/runtime/` | Ignored adapter/runtime state |

The main mission commands are:

```text
Init    -> legacy request INIT=0
Approve -> legacy request APPROVE=1
Start   -> legacy request START=2
```

## Tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -q
cd frontend && npm run build
```

Legacy ROS changes also require:

```bash
docker compose -f docker-compose.legacy-ros.yml up --build
./scripts/check_legacy_ros_stack.sh
```

## Documentation

- [Project planning, objectives, and guardrails](PROJECT_PLANNING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Legacy ROS component functions and robot workflows](docs/LEGACY_BACKEND_FEATURES_AND_WORKFLOWS.md)
- [Complete single-robot mission code walkthrough](docs/SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md)
- [Editable backend fork provenance](backend/FORK_PROVENANCE.md)
- [UI/backend adapter](docs/UI_BACKEND_LEGACY_ADAPTER.md)
- [ROS compatibility ICD](docs/ROS_COMPATIBILITY_ICD.md)
- [Legacy mission flow](docs/LEGACY_ROS_MISSION_FLOW_DIAGRAM.md)
- [Legacy node contracts](docs/legacy_nodes/README.md)
- [Future LLM assistant context design](docs/LLM_ASSISTANT_CONTEXT_ARCHITECTURE.md)
