from __future__ import annotations

import ast
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PATH_LIBRARY = (
    REPO_ROOT
    / "legacy_ros"
    / "fog"
    / "planner"
    / "ros2ws"
    / "src"
    / "path_planning_lib"
    / "path_planning_lib"
)
PLANNER_SOURCE = (
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


def _class_methods(path: Path, class_name: str) -> dict[str, ast.FunctionDef]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return {
        node.name: node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef)
    }


def test_free_linestring_graph_is_traversable_in_both_directions() -> None:
    module = ast.parse((PATH_LIBRARY / "graph.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "generate_graph_from_linestring"
    )
    edge_pairs = {
        tuple(ast.unparse(argument) for argument in call.args[:2])
        for call in ast.walk(function)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "add_edge"
        and len(call.args) >= 2
    }

    assert ("NODE_IDs + 1", "NODE_IDs") in edge_pairs
    assert ("NODE_IDs", "NODE_IDs + 1") in edge_pairs


def test_runtime_rma_connector_threshold_bridges_the_known_component_gap() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "legacy_ros" / "config" / "config_planner.yaml").read_text(
            encoding="utf-8"
        )
    )
    parameters = config["planner_node"]["ros__parameters"]

    # The seeded local graph is 21.450756 m from the current OSM component.
    assert parameters["line_graph_connect_max_distance"] > 21.450756
    assert parameters["poly_graph_connect_max_distance"] > 21.000237


def test_a_star_no_route_result_keeps_the_unpacking_contract() -> None:
    methods = _class_methods(PATH_LIBRARY / "mapf.py", "AStar")
    no_route_returns = [
        node
        for node in ast.walk(methods["search"])
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Tuple)
        and len(node.value.elts) == 2
        and isinstance(node.value.elts[0], ast.Constant)
        and node.value.elts[0].value is None
    ]

    assert no_route_returns


def test_unreachable_route_becomes_a_planning_error_not_a_type_error() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    helper = methods["_search_route"]
    solve = methods["solve_mission"]

    assert any(isinstance(node, ast.Raise) for node in ast.walk(helper))
    assert sum(
        1
        for node in ast.walk(solve)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_search_route"
    ) == 2


def test_planning_timer_releases_the_path_lock_and_publishes_failure_state() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    callback = methods["planning_timer_callback"]

    assert any(
        isinstance(node, ast.With)
        and any(
            isinstance(item.context_expr, ast.Attribute)
            and item.context_expr.attr == "paths_mutex"
            for item in node.items
        )
        for node in ast.walk(callback)
    )
    assert any(
        isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
        for handler in (
            node
            for node in ast.walk(callback)
            if isinstance(node, ast.ExceptHandler)
        )
    )
    assert any(
        isinstance(node, ast.Dict)
        and any(
            isinstance(value, ast.Constant) and value.value == 4
            for value in node.values
        )
        for node in ast.walk(callback)
    )
    assert any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute) and target.attr == "paths"
            for target in node.targets
        )
        and isinstance(node.value, ast.Dict)
        and not node.value.keys
        for node in ast.walk(callback)
    )


def test_failed_create_clears_cached_paths_and_binds_the_failed_mission() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    source = ast.unparse(methods["_set_create_planner_failure"])

    assert "self.current_mission_id = mission_id" in source
    assert "with self.paths_mutex" in source
    assert "self.paths = {}" in source
    assert "self.paths_mission_id = None" in source


def test_get_plan_never_returns_a_different_missions_cached_path() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    source = ast.unparse(methods["get_plan_service_callback"])

    assert "request.id == self.paths_mission_id" in source
    assert "self.planner_states.get(request.id) == 2" in source
    assert "{'mission_id': request.id, 'tasks': {}}" in source
    assert "self.path_to_plan_json(request.id, self.paths)" in source
