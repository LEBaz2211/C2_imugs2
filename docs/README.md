# Documentation Index

> **Documentation label: PRIMARY**
> This is the navigation and authority index for repository documentation.

Start with [Architecture](ARCHITECTURE.md). It is the primary description of
the current system, its ownership boundaries, and the relationship between the
adapter, editable ROS runtime, and frozen compatibility reference.

## Labels

| Label | Meaning | How to use it |
| --- | --- | --- |
| `PRIMARY` | Entry point or authority map | Read first and follow its links. |
| `CURRENT` | Describes the evolving implementation | Confirm volatile details against code, Compose, and tests. |
| `CONTRACT` | Stable interface or compatibility requirement | Do not change without an explicit contract migration. |
| `REFERENCE` | Frozen comparison evidence | Inspect for compatibility; never copy fixes into `legacy_ros/`. |
| `GENERATED` | Mechanically extracted from checked-in sources | Useful for discovery, but not proof that an interface was observed at runtime. |
| `FUTURE` | Proposed later architecture | Not authorization to implement it now. |
| `NEEDS REVIEW` | Known to contain stale or unverified details | Do not use as implementation authority. |

Unlabelled package READMEs and `new_codebase_legacy_context_bundle/` are
upstream or historical material. They are not current project guidance.

## Authority Order

When documents disagree, use this order:

1. Explicit user requirements.
2. [Architecture](ARCHITECTURE.md) for current boundaries and ownership.
3. [Project Planning](../PROJECT_PLANNING.md) for priorities and migration rules.
4. JSON Schemas and the [ROS Compatibility ICD](ROS_COMPATIBILITY_ICD.md) for stable contracts.
5. Current source, Compose files, tests, and verified runtime observations for implementation behavior.
6. `REFERENCE`, `GENERATED`, and `NEEDS REVIEW` material only for their stated scope.

## Current System

| Document | Label | Purpose |
| --- | --- | --- |
| [Architecture](ARCHITECTURE.md) | `PRIMARY` | Current runtime, ownership, scenario model, and replacement boundaries |
| [Project Planning](../PROJECT_PLANNING.md) | `CURRENT` | Project priorities and non-negotiable migration rules |
| [UI to Editable ROS Adapter](UI_BACKEND_LEGACY_ADAPTER.md) | `CURRENT` | Browser-to-adapter-to-ROS integration |
| [UI to Simulation Interface](UI_SIMULATION_INTERFACE.md) | `CONTRACT` | Stable UI-facing boundary and state semantics |
| [Editable Runtime Walkthrough](SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md) | `NEEDS REVIEW` | Detailed walkthrough pending revalidation against the evolving planner |

## Contracts

| Document | Label | Purpose |
| --- | --- | --- |
| [ROS Compatibility ICD](ROS_COMPATIBILITY_ICD.md) | `CONTRACT` | Interfaces and data rules that must remain compatible |
| [Generated Contract Browser](generated/index.md) | `GENERATED` | Static source and schema inventory, with separately identified runtime examples |

## Frozen Reference

These pages describe `legacy_ros/`, the read-only compatibility reference. They
do not describe where new backend work belongs.

| Document | Label | Purpose |
| --- | --- | --- |
| [Legacy Mission Walkthrough](LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md) | `REFERENCE` | Verified frozen-runtime mission path |
| [Legacy ROS Mission Flow](LEGACY_ROS_MISSION_FLOW_DIAGRAM.md) | `REFERENCE` | Frozen runtime flow diagram |
| [Upstream Comparison](LEGACY_ROS_UPSTREAM_COMPARISON.md) | `REFERENCE` | Provenance and pinned differences |
| [Legacy Node Contracts](legacy_nodes/README.md) | `REFERENCE` | Per-node source evidence |

## Future Work

| Document | Label | Purpose |
| --- | --- | --- |
| [LLM Assistant Context Architecture](LLM_ASSISTANT_CONTEXT_ARCHITECTURE.md) | `FUTURE` | Backend-scoped natural-language mission, operational context, persistence, and retrieval design |

## Change Discipline

Prefer the smallest change that satisfies the requirement and preserves the
documented boundaries and contracts. Do not combine a focused fix with an
unrelated refactor, broad rename, contract cleanup, or legacy synchronization.
When backend behavior changes, update only the affected `CURRENT` description,
test, or generated evidence; do not rewrite frozen reference history.
