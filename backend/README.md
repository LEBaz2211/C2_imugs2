# Vendored Legacy ROS Runtime

This directory contains the minimal old ROS code needed to build and run the real legacy nodes from inside this repository.

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
