# Editable ROS Backend Fork

> **Documentation label: REFERENCE**
> Provenance record for the editable runtime fork; not a description of all
> current runtime behavior.

This directory is the working copy of the legacy ROS backend. It exists so the
backend can evolve separately from the runnable compatibility runtime in
`legacy_ros/`.

## Baseline

`backend/` contains all 627 version-controlled files from `legacy_ros/`,
copied byte-for-byte from repository commit
`9db7b44d70ce89c8dbf58e85320cf43f69e948bf` on 2026-08-04. Ignored build
outputs, caches, generated ROS workspaces, and editor files were deliberately
not copied.

```text
Source commit: 9db7b44d70ce89c8dbf58e85320cf43f69e948bf
Source tree:   194be54b33c3c3d90418e3b31bbbbdb9c098498b
Tracked files: 627
```

The initial copy includes the complete runtime source needed by the current
stack:

```text
backend/
  fog/centralized-coordination/  lifecycle, mission manager, fleet manager
  fog/planner/                   planner node and path-planning library
  fog/command-control/           C2 HTTP-to-ROS bridge
  edge/agent-tasks-supervisor/   edge supervisor and autonomy simulator
  config/                        ROS parameters, launch scripts, and maps
  docker/                        reproducible ROS 2 Humble images
```

This is intentionally a placeholder fork, not a redesigned architecture. Its
ROS message/service definitions, topic/service names, numeric enums, and JSON
contracts were unchanged at the copy point.

## Last Historical Synchronization Point

The fork was resynchronized on 2026-08-10 with the tracked runtime files in
`legacy_ros/` at repository commit `1fb453f`. This brought across the later
upstream resynchronization and repository-local runtime fixes: deterministic
`MapDB.rma` seeding, guarded map readiness and error state `4`, explicit
no-route handling, stale-path prevention, bidirectional local roads, the RMA
graph-connection thresholds, and map-snapshot-specific planner loading.

The directory-specific README/provenance files intentionally differ, and
`docker-compose.backend.yml` keeps backend-specific container names and data
directories. This records the last baseline comparison only. Backend sources
are expected to diverge from this point forward and must never be copied back
into `legacy_ros/`. See
[`docs/LEGACY_ROS_UPSTREAM_COMPARISON.md`](../docs/LEGACY_ROS_UPSTREAM_COMPARISON.md).

## Run The Fork

The editable fork exposes the same host ports and ROS domain as the baseline,
so only one of the two stacks may run at a time.

```bash
docker compose -f docker-compose.legacy-ros.yml down
docker compose -f docker-compose.backend.yml up --build
./scripts/check_backend_ros_stack.sh
```

The existing FastAPI/UI stack can then be started normally; it talks to the
same REST and rosbridge endpoints:

```bash
docker compose up -d --build c2-imugs2-api c2-imugs2-ui
```

The fork uses its own Mongo and planner-result directories:

```text
data/backend-mongo/
data/backend-planresults/
```

These are runtime data and should not be treated as source.

The FastAPI map reader and experimental Map snapshot Lab launcher still default to
paths and an edge image named for `legacy_ros/`. Those dependencies must
become configurable before later backend changes to maps, launch scripts, or
the edge image are selected as the default UI runtime.

## Divergence Policy

Intentional differences are expected. Implement and test all ROS fixes and
features in `backend/`, record significant compatibility decisions in the
relevant design document, and run the frozen legacy stack only as a comparison
reference. Do not add parity tests that require backend files to equal legacy
files, and do not resynchronize either tree in either direction.
