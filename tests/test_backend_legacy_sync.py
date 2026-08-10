from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNCED_RUNTIME_PATHS = (
    "config/config_planner.yaml",
    "docker/Dockerfile.planner",
    "docker/seed-mapdb.js",
    "fog/planner/.config/install_dependencies.sh",
    "fog/planner/ros2ws/src/path_planning_lib/build_lib.sh",
    "fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/graph.py",
    "fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/mapf.py",
    "fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py",
    "fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/utils.py",
    "fog/planner/ros2ws/src/planner/planner/planner_node.py",
)


def test_backend_contains_the_latest_legacy_planner_runtime_files() -> None:
    for relative_path in SYNCED_RUNTIME_PATHS:
        legacy = REPO_ROOT / "legacy_ros" / relative_path
        backend = REPO_ROOT / "backend" / relative_path

        assert backend.read_bytes() == legacy.read_bytes(), relative_path


def test_backend_compose_preserves_mapdb_and_scenario_startup_behavior() -> None:
    compose = yaml.safe_load(
        (REPO_ROOT / "docker-compose.backend.yml").read_text(encoding="utf-8")
    )
    seed = compose["services"]["mapdb-seed"]
    planner = compose["services"]["planner"]

    assert seed["container_name"] == "c2-imugs2-backend-mapdb-seed"
    assert any("backend/docker/seed-mapdb.js" in volume for volume in seed["volumes"])
    assert planner["depends_on"]["mapdb-seed"]["condition"] == "service_completed_successfully"
    assert "./data/runtime:/runtime:ro" in planner["volumes"]
    assert "active_planner.yaml" in planner["command"]
