# C2 iMUGS2

> **Documentation label: PRIMARY**
> Repository entry point. Continue with the [documentation index](docs/README.md)
> and then [Architecture](docs/ARCHITECTURE.md).

This repository contains a web UI and FastAPI adapter for a ROS 2 multi-robot
system. It also contains two copies of the ROS backend: one for development and
one retained as a legacy reference.

This README is only the repository entry point. Use the
[documentation index](docs/README.md) to distinguish current, contract,
reference, generated, and historical material.

## Where to start

| Area | Purpose | Documentation |
|---|---|---|
| `backend/` | Editable ROS backend used for new backend work | [Backend README](backend/README.md) |
| `legacy_ros/` | Frozen compatibility/reference copy | [Legacy ROS README](legacy_ros/README.md) |
| `frontend/` | React mission and scenario UI | UI structure is described in [UI/backend adapter](docs/UI_BACKEND_LEGACY_ADAPTER.md) |
| `src/c2_imugs2/` | FastAPI adapter and Python modules | [Architecture](docs/ARCHITECTURE.md) |
| `schemas/` | JSON contracts for missions, plans, agents, and map features | [Generated contract reference](docs/generated/index.md) |
| `docs/legacy_nodes/` | Per-node ROS inputs, outputs, and examples | [ROS node README](docs/legacy_nodes/README.md) |

More specific backend package notes are available for:

- [Centralized coordination](backend/fog/centralized-coordination/README.md)
- [Planner](backend/fog/planner/README.md)
- [Edge task supervisor](backend/edge/agent-tasks-supervisor/README.md)

Some package-level README files came from the original source repositories and
may describe their old standalone build process. For this repository, use the
top-level Compose files and the [backend README](backend/README.md).

Frontend contributions should use the shared shadcn-style primitives and the
compact operator-UI conventions documented in
[Architecture](docs/ARCHITECTURE.md#frontend-ui-conventions).

## Runtime layout

```text
Browser UI (:5173)
  -> FastAPI adapter (:8000)
  -> ROS REST bridge (:5001) and rosbridge (:9090)
  -> centralized coordination, planner, fleet, edge, and autonomy nodes
  -> MongoDB
```

The editable and legacy ROS stacks use the same host ports and ROS domain, so
they cannot run at the same time.

## Run the editable backend

Start the ROS backend:

```bash
docker compose -f docker-compose.legacy-ros.yml down
docker compose -f docker-compose.backend.yml up --build
./scripts/check_backend_ros_stack.sh
```

Start the API and UI in another terminal:

```bash
docker compose up -d --build c2-imugs2-api c2-imugs2-ui
```

Open `http://localhost:5173`.

Health and diagnostic endpoints:

```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool
curl -s http://localhost:8000/api/diagnostics | python3 -m json.tool
curl -s http://localhost:8000/api/legacy/trace | python3 -m json.tool
```

To run the frozen legacy stack instead, follow the
[legacy ROS instructions](legacy_ros/README.md).

## Contract documentation

The contract reference is generated from the editable backend, adapter,
frontend API calls, Compose configuration, and JSON Schemas.

```bash
.venv/bin/python -m pip install -e ".[docs]"
.venv/bin/python -m c2_imugs2.contract_docs generate
.venv/bin/mkdocs serve
```

Open `http://127.0.0.1:8001`. Source changes are watched while MkDocs is
running. The single-page reference includes a source-extracted module data-flow
diagram and real verified payload examples. Its interface inventory is also
available as `docs/generated/interface-inventory.csv`. CI checks that the
committed generated files are current.

## Tests

Python and adapter tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -q
```

Frontend build:

```bash
cd frontend
npm run build
```

Backend ROS changes should also be checked with:

```bash
./scripts/check_backend_ros_stack.sh
```

## Project guidance

Read [Architecture](docs/ARCHITECTURE.md) first, then
[PROJECT_PLANNING.md](PROJECT_PLANNING.md) before changing architecture, ROS
contracts, or compatibility behavior. Prefer the smallest targeted change that
solves the stated problem. `legacy_ros/` is permanently frozen and read-only;
make every ROS backend implementation change in `backend/`.
Compatibility tests may run or inspect the legacy stack, but must not modify it
or synchronize backend changes into it.

Additional technical documents:

- [ROS compatibility ICD](docs/ROS_COMPATIBILITY_ICD.md)
- [Editable backend mission walkthrough](docs/SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md)
- [Frozen-reference mission walkthrough](docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md)
- [Backend/legacy comparison](docs/LEGACY_ROS_UPSTREAM_COMPARISON.md)
