from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PATH_LIBRARY = (
    REPO_ROOT
    / "backend"
    / "fog"
    / "planner"
    / "ros2ws"
    / "src"
    / "path_planning_lib"
    / "path_planning_lib"
)
MAPF_SOURCE = PATH_LIBRARY / "mapf.py"
PLANNER_SOURCE = (
    REPO_ROOT
    / "backend"
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


def test_coverage_branch_uses_the_polygon_lawnmower_planner() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    solve_source = ast.unparse(methods["solve_mission"])
    coverage_source = ast.unparse(methods["_solve_polygon_coverage"])

    assert "coverage_algorithm" not in solve_source
    assert "self._solve_polygon_coverage" in solve_source
    assert "lawnmower_coverage_path" in coverage_source
    assert "maximum_coverage_distances" in ast.unparse(
        methods["_coverage_widths_by_vehicle"]
    )


def test_database_polygon_resolution_preserves_interior_holes() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    source = ast.unparse(methods["update_mission"])

    assert "geometry.interiors" in source


def test_lawnmower_algorithm_projects_metres_and_stays_inside_polygon() -> None:
    module = ast.parse((PATH_LIBRARY / "max_coverage.py").read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
    }

    assert "lawnmower_coverage_path" in functions
    assert "_project_polygon_to_local_utm" in functions
    assert "_shortest_inside_path" in functions
    assert "_order_lane_fragments" in functions
    source = ast.unparse(functions["lawnmower_coverage_path"])
    assert "math.ceil(usable_extent / width)" in source
    assert "DEFAULT_BOUNDARY_INSET_M" in source
    assert "_order_lane_fragments(lane_fragments, aligned)" in source
    assert "[aligned.exterior, *aligned.interiors]" not in source


def test_lawnmower_subtracts_buffered_risk_polygons() -> None:
    module = ast.parse((PATH_LIBRARY / "max_coverage.py").read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
    }
    coverage_source = ast.unparse(functions["lawnmower_coverage_path"])
    exclusion_source = ast.unparse(functions["_subtract_risk_polygons"])

    assert "risk_polygons" in coverage_source
    assert "_subtract_risk_polygons" in coverage_source
    assert ".buffer(clearance" in exclusion_source
    assert ".difference(" in exclusion_source


def test_coverage_transit_and_sweep_treat_risks_as_hard_obstacles() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    solve_source = ast.unparse(methods["_solve_polygon_coverage"])
    connector_source = ast.unparse(methods["_connector_is_risk_free"])
    astar_methods = _class_methods(MAPF_SOURCE, "AStar")
    search_source = ast.unparse(astar_methods["search"])
    step_cost_source = ast.unparse(astar_methods["step_cost"])

    assert "risk_polygons=self.risk_polygons" in solve_source
    assert "risk_polygon.intersects(connector)" in connector_source
    assert "get('risk', False)" in search_source
    assert "continue" in search_source
    assert "float('inf')" in step_cost_source
    assert "self.nearest_routable_node(self.agent.localization, for_start=True)" in search_source
    assert "self.nearest_routable_node(self.destination, for_start=False)" in search_source


def test_navigation_attaches_exact_endpoints_and_collapses_lattice_noise() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    solve_source = ast.unparse(methods["solve_mission"])
    path_source = ast.unparse(methods["_navigation_path_from_route"])
    simplify_source = ast.unparse(methods["_remove_collinear_waypoints"])
    search_source = ast.unparse(methods["_search_route"])
    astar_methods = _class_methods(MAPF_SOURCE, "AStar")
    snap_source = ast.unparse(astar_methods["nearest_routable_node"])

    assert solve_source.count("self._navigation_path_from_route") == 3
    assert "float(start[0])" in path_source
    assert "float(destination[0])" in path_source
    assert "self._remove_collinear_waypoints" in path_source
    assert "self._connector_is_risk_free(start, end)" in simplify_source
    assert "risk_polygons=self.risk_polygons" in search_source
    assert "self.connector_is_risk_free(location, node_location)" in snap_source


def test_successful_plan_is_cached_until_an_explicit_new_request() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    planning_source = ast.unparse(methods["planning_timer_callback"])
    create_source = ast.unparse(methods["set_mission_service_callback"])

    planned_state = "self.planner_states.update({mission_id: 2})"
    stop_planning = "self.mission_defined = False"
    assert planned_state in planning_source
    assert planning_source.index(stop_planning, planning_source.index(planned_state)) > planning_source.index(planned_state)
    assert "self.mission_defined = True" in create_source


def test_planner_injects_scenario_risk_polygons_into_mission_planner() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    source = ast.unparse(methods["initialize_map"])

    assert "self.risk_poly_gdfs" in source
    assert "risk_polygons=risk_polygons" in source
