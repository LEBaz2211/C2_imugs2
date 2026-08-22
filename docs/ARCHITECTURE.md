# Architecture

> **Documentation label: PRIMARY**
> This is the most important technical document for coding agents and human
> maintainers. It describes the current system boundaries; implementation
> details still need confirmation against source, Compose, and tests.

C2 iMUGS2 uses a stable adapter boundary around the editable ROS runtime in `backend/`. That runtime preserves the required legacy contracts while evolving independently. The long-term replacement code remains modular, but compatibility work must not require the browser to understand ROS or the core domain to depend on legacy infrastructure. `legacy_ros/` is a frozen, read-only comparison reference.

Read [PROJECT_PLANNING.md](../PROJECT_PLANNING.md) before changing these boundaries.

## Change Discipline

Prefer the smallest change that satisfies the requirement. Modify only the
owning layer, preserve stable contracts by default, and avoid adjacent
refactors, broad renames, or legacy-tree synchronization unless they are
explicitly requested. Because the editable backend is a work in progress,
record current behavior without presenting it as permanent architecture.

## Runtime Layers

```text
React/Vite/Leaflet UI
  -> FastAPI JSON + SSE adapter
     -> legacy REST client for mission commands
     -> rosbridge client for ROS diagnostics and live reads
     -> scenario activation + immutable MapDB snapshots
  -> Dockerized editable ROS backend (`docker-compose.backend.yml`)
     -> C2 -> interface -> orchestrator -> mission manager
     -> planner -> fleet manager -> edge supervisor -> autonomy sim
```

The UI never constructs ROS messages or connects directly to rosbridge. The backend owns partial structural validation, legacy alias translation, coordinate conversion, feature inlining, and feedback normalization. The canonical JSON Schemas are currently design contracts rather than validators executed by the mission endpoint.

## Frontend UI Conventions

The frontend uses Tailwind with shadcn-style shared primitives from
`frontend/src/components/ui/`. New UI work should compose those primitives
before introducing local visual variants. Buttons, badges, tabs, inputs,
alerts, and cards should share the existing neutral surfaces, border radii,
focus behavior, spacing scale, and semantic tones.

Operator controls should favor compact, glanceable state over permanently
expanded explanation. Dense runtime information belongs in small status chips
or summaries with accessible hover/focus text; longer raw or diagnostic detail
belongs in the Diagnostics view or an explicit disclosure. Responsive panels
must preserve access to every action without forcing the map below its useful
minimum size.

## Replacement Core

The independent core is organized around ports in `src/c2_imugs2/ports.py`:

- `PlannerPort`
- `AgentRepositoryPort`
- `MapRepositoryPort`
- `MissionRepositoryPort`
- `PlanRepositoryPort`
- `EdgeDispatcherPort`

`MissionService` orchestrates these ports. `SimplePlanner` and the file-backed repositories are development implementations, not substitutes for the real editable ROS backend during integration testing.

Any future planner adapter should preserve the logical boundary:

```text
mission_config + selected agents -> validated task_plan
```

## Code Ownership

| Area | Main files | Responsibility |
| --- | --- | --- |
| UI | `frontend/src/App.tsx`, `MapView.tsx`, `api.ts` | Operator workflow, map rendering, API/SSE consumption |
| Compatibility API | `src/c2_imugs2/api.py` | Stable UI endpoints and normalized runtime state |
| Legacy command adapter | `legacy_rest.py` | Old REST actions and canonical-to-legacy field translation |
| ROS read adapter | `rosbridge.py` | Diagnostics and topic subscriptions |
| Map adapter | `legacy_map.py` | Legacy GeoJSON, runtime features, explicit polygon-bounded OSM queries |
| Scenario runtime | `scenario_runtime.py`, `scenario_launch.py` | Freeze a scenario version, switch the planner, replace and verify robot containers |
| Domain contracts | `domain.py`, `mission_config.py`, `task_plan.py`, `schemas/` | Enums, normalization, and validation |
| Modular core | `mission_service.py`, `ports.py`, `repositories.py`, `planner.py` | Replaceable non-ROS orchestration |
| Editable ROS runtime | `backend/` | Writable ROS nodes, planner, edge runtime, configuration, and embedded interfaces |
| Frozen legacy reference | `legacy_ros/` | Read-only historical runtime used only for inspection and compatibility comparison |

## Compatibility Boundary

Canonical data stays clean inside the UI/backend, while adapters preserve the old external contract. For example:

```text
canonical transit.optimization
  -> legacy_rest.py
  -> legacy transit.optimalization
```

Runtime user features are also converted at this boundary: the UI may refer to a saved feature, but the adapter sends inline geometry when the old planner cannot resolve that runtime `feature_id`.

Scenario roads are not mission geometry. The mission carries objectives and constraints; the active scenario's roads live in its MapDB snapshot.

## One Active Scenario

Scenario activation is the transaction boundary that changes simulated reality:

```mermaid
flowchart LR
    UI[Scenario Lab] -->|polygon OSM download| Draft[Browser scenario draft]
    Draft -->|POST /api/scenarios/activate| API[Scenario runtime manager]
    API --> Hash[Hash complete scenario version]
    Hash --> Map[(MapDB.scenario_id_version)]
    API --> Config[Write active planner config]
    Config --> Restart[Restart coordination and planner]
    API --> Robots[Replace robot containers]
    Restart --> Verify{Planner loaded exact collection?}
    Robots --> Verify2{All robot IDs registered?}
    Verify --> Ready[Active scenario READY]
    Verify2 --> Ready
    Ready --> Init[Mission Init allowed]
```

Only one scenario may be active. Each activation creates or reuses a content-addressed, immutable collection named `MapDB.scenario_<id>_<version>`. Old version collections are retained for reproducibility; they are not merged into the active graph. `MapDB.rma` remains the legacy seed and Scenario Lab authoring library, not the planner's source after activation. Central coordination is restarted during the switch so mission nodes from the previous reality cannot survive into the new one.

OSM has one operational path: the operator explicitly downloads roads inside a Scenario Lab polygon, the browser keeps those GeoJSON LineStrings in the scenario draft, and activation freezes them as `road` features in the versioned MapDB collection. The deployed planner has `load_osm_from_network: false`; it does not make a second live OSMnx download.

Mission endpoints may fall between graph junctions. The planner projects those endpoints onto risk-safe edges and splits the selected edges only in a request-local graph copy. These virtual endpoint nodes must never be written to, or reused to mutate, the active scenario's immutable MapDB snapshot or its base routing graph.

Activation stays non-ready unless both checks pass:

- the planner logs that it loaded the exact versioned MapDB collection and produced a non-empty graph;
- every configured robot container is running and its canonical ID appears in `RuntimeDB.ConnectedVehicles`.

Mission Init is rejected with HTTP `409` while no scenario is ready or when a mission names a robot outside the active scenario.

The old REST status command is stateful: its body has no mission id and `/c2_node` targets the last mission it initialized. FastAPI's mission-specific approve/start URLs do not remove that legacy limitation. Likewise, an HTTP success is only command acceptance; ROS mission feedback is the authoritative state.

Do not change message layouts, enum values, topic/service names, or mission/task JSON structures as an architectural shortcut. Add or replace an adapter instead.

## Live State

`GET /api/events` emits normalized SSE events:

```text
diagnostics.updated
mission.updated
agent.updated
planner.updated
```

Mission status and path availability are separate. Planner readiness is not evidence of a route; a usable route comes from mission feedback containing waypoint tasks.

## Replacement Strategy

Replace one boundary at a time:

1. Define and test the stable input/output contract.
2. Add the new implementation behind the existing port or adapter.
3. Compare it with the frozen legacy runtime without changing the legacy tree.
4. Switch callers only after compatibility is verified.

This lets the planner, ROS transport, storage, UI, and later LLM tooling evolve independently without a broad legacy rewrite.
