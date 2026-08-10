# Editable ROS Backend Fork

This directory is the editable backend fork of `legacy_ros/`. It keeps the
real ROS nodes and compatibility contracts while giving the project a place to
make future backend changes without turning `legacy_ros/` into the development
target.

The fork is currently synchronized with the tracked runtime source in
`legacy_ros/`, including its MapDB startup seed, planner readiness/error
handling, route-failure safeguards, bidirectional local roads, scenario
activation parameters, and graph-connection settings. See
[FORK_PROVENANCE.md](FORK_PROVENANCE.md) for the baseline and synchronization
history.

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
