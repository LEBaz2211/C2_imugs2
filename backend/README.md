# Editable ROS Backend Fork

> **Documentation label: CURRENT**
> Operational entry point for the evolving editable ROS runtime. Architecture
> and ownership rules are defined in [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

This directory is the editable backend fork of `legacy_ros/`. It keeps the
real ROS nodes and compatibility contracts while giving the project a place to
make future backend changes without turning `legacy_ros/` into the development
target.

The fork started from the tracked runtime source in `legacy_ros/`, including
its MapDB startup seed, planner readiness/error handling, route-failure
safeguards, bidirectional local roads, map-snapshot parameters, and
graph-connection settings. That relationship is historical provenance, not an
ongoing synchronization contract. `backend/` is now the only writable ROS
backend source; `legacy_ros/` must remain unchanged. See
[FORK_PROVENANCE.md](FORK_PROVENANCE.md) for the baseline history.

The source was copied from `../multi-agent-framework` and trimmed to keep:

- fog centralized coordination package and message packages
- fog planner package, planner algorithms, and message package
- fog command-control ROS REST/rosbridge package
- edge agent task supervisor and autonomy simulator packages. The default compose runs both actual old edge executables in one container for one simulated UGV.
- Single-Robotnik configs, launch scripts, and map data
- simplified Dockerfiles under `backend/docker/`

It intentionally excludes old build/install/log folders, Git internals, and unrelated full-stack scaffolding.

Only one ROS stack can use the shared host ports and ROS domain at a time. Run
the editable backend with:

```bash
docker compose -f docker-compose.legacy-ros.yml down
docker compose -f docker-compose.backend.yml up --build
```

Check:

```bash
./scripts/check_backend_ros_stack.sh
```

The backend stack uses its own MongoDB and planner-result directories under
`data/backend-mongo/` and `data/backend-planresults/`.
