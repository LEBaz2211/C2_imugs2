from __future__ import annotations

from pathlib import Path

import yaml

from c2_imugs2.scenario_runtime import COORDINATION_CONTAINER, DEFAULT_EDGE_CONTAINER, PLANNER_CONTAINER

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def test_scenario_runtime_targets_only_editable_backend_containers() -> None:
    assert COORDINATION_CONTAINER == "c2-imugs2-backend-centralized-coordination"
    assert PLANNER_CONTAINER == "c2-imugs2-backend-planner"
    assert DEFAULT_EDGE_CONTAINER == "c2-imugs2-backend-edge-agent-sim-1"

    adapter_compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    api_volumes = adapter_compose["services"]["c2-imugs2-api"]["volumes"]
    assert "./backend/config/data/map:/app/backend/config/data/map:ro" in api_volumes
