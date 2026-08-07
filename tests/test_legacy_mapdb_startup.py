from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FEATURE_IDS = {
    "60bae762-6c7a-4b11-8803-556fdfee4425",
    "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e",
    "5711e91f-f8e5-4ae2-b4a0-8ceb7e73d098",
}
SUPPORTED_GEOMETRY = {
    "objective": {"Point"},
    "road": {"LineString"},
    "geofence": {"Polygon"},
    "workspace": {"Polygon"},
    "risk": {"Polygon"},
}


def _records(document: dict) -> list[dict]:
    if document.get("type") == "Feature":
        return [document]
    if document.get("type") == "FeatureCollection":
        return document.get("features", [])
    return []


def _is_seedable(feature: dict) -> bool:
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if feature.get("type") != "Feature" or not isinstance(properties, dict) or not isinstance(geometry, dict):
        return False
    if any(not isinstance(properties.get(field), str) or not properties[field].strip() for field in ("feature_id", "feature_type", "name")):
        return False
    return geometry.get("type") in SUPPORTED_GEOMETRY.get(properties["feature_type"], set()) and isinstance(geometry.get("coordinates"), list)


def test_rma_seed_flattens_to_the_three_valid_baseline_features() -> None:
    seed_root = REPO_ROOT / "legacy_ros" / "config" / "data" / "map" / "rma"
    valid: dict[str, dict] = {}
    skipped: list[str] = []

    for filename in sorted(seed_root.rglob("*.geojson")):
        document = json.loads(filename.read_text(encoding="utf-8"))
        for index, feature in enumerate(_records(document)):
            if _is_seedable(feature):
                feature_id = feature["properties"]["feature_id"]
                assert feature_id not in valid
                valid[feature_id] = feature
            else:
                skipped.append(f"{filename.relative_to(seed_root)}#{index}")

    assert set(valid) == EXPECTED_FEATURE_IDS
    assert {(feature["properties"]["feature_type"], feature["geometry"]["type"]) for feature in valid.values()} == {
        ("road", "LineString"),
        ("geofence", "Polygon"),
        ("risk", "Polygon"),
    }
    assert skipped == ["virtual_geofences/geofence1.geojson#0"]


def test_legacy_compose_seeds_mapdb_before_starting_planner() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.legacy-ros.yml").read_text(encoding="utf-8"))
    seed = compose["services"]["mapdb-seed"]
    planner = compose["services"]["planner"]

    assert seed["image"] == "mongo:7"
    assert seed["depends_on"]["mongodb"]["condition"] == "service_healthy"
    assert any("seed-mapdb.js" in volume for volume in seed["volumes"])
    assert set(seed["environment"]["MAP_REQUIRED_FEATURE_IDS"].split(",")) == EXPECTED_FEATURE_IDS
    assert planner["depends_on"]["mapdb-seed"]["condition"] == "service_completed_successfully"


def test_create_planner_has_a_nonfatal_map_readiness_guard() -> None:
    planner_path = (
        REPO_ROOT
        / "legacy_ros"
        / "fog"
        / "planner"
        / "ros2ws"
        / "src"
        / "planner"
        / "planner"
        / "planner_node.py"
    )
    module = ast.parse(planner_path.read_text(encoding="utf-8"))
    planner_class = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "PlannerNode")
    methods = {node.name: node for node in planner_class.body if isinstance(node, ast.FunctionDef)}
    callback = methods["set_mission_service_callback"]

    called_methods = {
        node.func.attr
        for node in ast.walk(callback)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    caught_errors = {
        handler.type.id
        for handler in (node for node in ast.walk(callback) if isinstance(node, ast.ExceptHandler))
        if isinstance(handler.type, ast.Name)
    }

    assert "_ensure_map_ready" in methods
    assert "_set_create_planner_failure" in methods
    assert "_ensure_map_ready" in called_methods
    assert "_set_create_planner_failure" in called_methods
    assert "Exception" in caught_errors
    assert any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Attribute) and target.attr == "state" for target in node.targets)
        and isinstance(node.value, ast.Constant)
        and node.value.value == 4
        for node in ast.walk(methods["_set_create_planner_failure"])
    )
