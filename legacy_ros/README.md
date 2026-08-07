# Vendored Legacy ROS Runtime

This directory contains the minimal old ROS code needed to build and run the real legacy nodes from inside this repository.

Exact component revisions, comparison scope, and local packaging exceptions are
recorded in [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).

The source was copied from `../multi-agent-framework` and trimmed to keep:

- fog centralized coordination package and message packages
- fog planner package, planner algorithms, and message package
- fog command-control ROS REST/rosbridge package
- edge agent task supervisor and autonomy simulator packages. The default compose runs both actual old edge executables in one container for one simulated UGV.
- Single-Robotnik configs, launch scripts, and map data
- new simplified Dockerfiles under `legacy_ros/docker/`

It intentionally excludes old build/install/log folders, Git internals, and unrelated full-stack scaffolding.

Run:

```bash
docker compose -f docker-compose.legacy-ros.yml up --build
```

Check:

```bash
./scripts/check_legacy_ros_stack.sh
```

The compose stack now runs an idempotent one-shot seed that places the three
valid baseline RMA features in `MapDB.rma` before the planner starts. The
planner retains the upstream database-backed design and adds local readiness,
route-failure, bidirectional-road, and graph-connection compatibility patches.
The exact Themis validation mission reached planner state `2` with `10`
waypoints; an unreachable route reached state `4` without killing
`/planner_node`. See the
[comparison](../docs/LEGACY_ROS_UPSTREAM_COMPARISON.md) and
[code walkthrough](../docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md).
