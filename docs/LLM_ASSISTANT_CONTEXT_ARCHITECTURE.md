# LLM Assistant Context And Memory Architecture

This is a future design for natural-language mission generation and runtime explanation. It does not authorize current benchmark work. Project priorities and compatibility rules are in [PROJECT_PLANNING.md](../PROJECT_PLANNING.md).

## Core Rule

```text
The LLM does not read ROS or MongoDB directly.
It calls backend tools that return small, verified, source-labelled context.
```

Legacy feedback and log collections grow quickly and contain many repeated rows. Raw access would waste context and make answers less reliable.

## Current Data Sources

| Source | Useful content |
| --- | --- |
| `RuntimeDB.MissionConfig` | Accepted mission configurations |
| `RuntimeDB.Planning` | Current planner task JSON per mission |
| `RuntimeDB.MissionFeedback` | Periodic mission snapshots; high volume |
| `RuntimeDB.Logs` | Swarm logs; high volume |
| `RuntimeDB.ConnectedVehicles` | Connected agent ids |
| `VehicleDB.Vehicles` | Latest agent profiles |
| Legacy map files or `MapDB` | Known tactical features |
| `docs/legacy_nodes/`, ICD, schemas | Stable contracts and behavior |

The FastAPI adapter already provides normalized diagnostic and trace data. Future assistant access should extend that pattern with read-only, filtered endpoints.

## Assistant Tools

The assistant needs a small operational tool set:

| Tool | Result |
| --- | --- |
| `get_operational_snapshot()` | Connected agents, selected mission, latest status, planner and health summary |
| `list_missions(filters)` | Mission ids, timestamps, statuses, and path availability |
| `get_mission_context(id)` | Config, plan summary, latest feedback, grouped warnings, and source ids |
| `get_fleet_context()` | Capabilities, locations, connectivity, and task state |
| `search_map_features(query)` | Matching features, geometry summaries, and bounds |
| `retrieve_contracts(query)` | Relevant schema, ICD, or documented node contract |
| `validate_mission_definition(json)` | Schema, legacy, map, and fleet errors/warnings |
| `propose_mission(json)` | A staged proposal; never an automatic ROS command |

Every response should identify its sources and observation time.

## Safe Mission Pipeline

```text
natural language
  -> candidate mission JSON
  -> JSON Schema validation
  -> legacy compatibility checks
  -> map and fleet checks
  -> optional planner preflight
  -> operator review
  -> explicit Init / Approve / Start
```

Deterministic checks must cover:

- valid behavior and mission enums,
- connected and capable vehicle ids,
- geometry type and `[lon, lat]` coordinates,
- supported task primitives,
- resolvable baseline features or inline runtime geometry,
- speed and vehicle constraints,
- road usage/snapping rules,
- non-empty information required by the planner.

An LLM repair loop may respond to validator errors, but it must not bypass them.

## Context Packing

Return the latest state, not a raw history:

- group repeated logs and include count plus latest occurrence,
- summarize paths by agent, waypoint count, distance, and endpoints,
- include raw coordinates only when explicitly needed,
- keep mission status separate from `path_status`,
- label missing or stale data,
- include document or database source ids,
- use live tools for runtime state and retrieval for stable docs.

A compact context object should contain the selected mission, connected fleet, plan summary, recent grouped warnings, and sources. Large telemetry documents are opt-in debugging data.

## Memory Strategy

Use three complementary stores:

1. **Normalized live tools** for current ROS, map, fleet, and mission state.
2. **Search over stable knowledge** for schemas, ICDs, node documents, and selected source explanations.
3. **Compact mission timelines** that turn repeated feedback/log rows into durable events for debugging and after-action review.

Start with simple read-only queries and full-text search. Choose a vector database only when evaluation shows that semantic retrieval materially improves results.

## Recommended Build Order

1. Add read-only context endpoints with strict limits and source labels.
2. Add deterministic mission validation and legacy compatibility checks.
3. Add a UI proposal panel with validation results and explicit operator actions.
4. Add search over schemas and documentation.
5. Add compact event-sourced mission timelines.
6. Build a verified natural-language-to-mission evaluation set.
7. Compare hosted, local, or fine-tuned models after the benchmark exists.

The first useful assistant should explain runtime state and draft safe proposals. Autonomous mission execution is not a goal.
