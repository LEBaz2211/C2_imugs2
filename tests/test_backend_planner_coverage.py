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


def test_coverage_dispatch_distinguishes_area_line_and_road_patrol() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    solve_source = ast.unparse(methods["solve_mission"])
    coverage_source = ast.unparse(methods["_solve_coverage"])

    assert "coverage_algorithm" not in solve_source
    assert "self._solve_coverage" in solve_source
    assert "lawnmower_coverage_path" in coverage_source
    assert "self._road_patrol_path" in coverage_source
    assert "LineString" in coverage_source
    assert "coverage_swath_widths" in ast.unparse(
        methods["_coverage_widths_by_vehicle"]
    )
    assert "maximum_coverage_distances" not in ast.unparse(
        methods["_coverage_widths_by_vehicle"]
    )


def test_patrol_work_is_complete_and_evenly_divided() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    road_source = ast.unparse(methods["_road_patrol_path"])
    split_source = ast.unparse(methods["_split_continuous_path"])

    assert "nx.eulerize" in road_source
    assert "nx.eulerian_circuit" in road_source
    assert "disconnected active-world road components" in road_source
    assert "total_length" in split_source
    assert "point_at" in split_source
    assert "segment_lengths" in split_source


def test_database_polygon_resolution_preserves_interior_holes() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    source = ast.unparse(methods["_resolve_geometry_ref"])

    assert "geometry.interiors" in source


def test_optional_transit_speed_cannot_crash_the_backend_planner() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    source = ast.unparse(methods["get_max_speed"])

    assert "mission['transit']" not in source
    assert "mission.get('transit')" in source
    assert "math.isfinite(speed)" in source
    assert "return 1.0" in source


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
    solve_source = ast.unparse(methods["_solve_coverage"])
    connector_source = ast.unparse(methods["_connector_is_risk_free"])
    astar_methods = _class_methods(MAPF_SOURCE, "AStar")
    search_source = ast.unparse(astar_methods["search"])
    step_cost_source = ast.unparse(astar_methods["step_cost"])
    edge_source = ast.unparse(astar_methods["best_routable_edge"])

    assert "risk_polygons=self.risk_polygons" in solve_source
    assert "risk_polygon.intersects(connector)" in connector_source
    assert "get('risk', False)" in edge_source
    assert "continue" in search_source
    assert "float('inf')" in step_cost_source
    assert "self.nearest_routable_node(self.agent.localization, for_start=True)" in search_source
    assert "self.nearest_routable_node(self.destination, for_start=False)" in search_source


def test_navigation_attaches_exact_endpoints_and_collapses_lattice_noise() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    allocation_source = ast.unparse(methods["_paths_for_allocations"])
    path_source = ast.unparse(methods["_navigation_path_from_route"])
    simplify_source = ast.unparse(methods["_remove_collinear_waypoints"])
    search_source = ast.unparse(methods["_search_route"])
    astar_methods = _class_methods(MAPF_SOURCE, "AStar")
    snap_source = ast.unparse(astar_methods["nearest_routable_node"])

    assert "self._navigation_path_from_route" in allocation_source
    assert "float(start[0])" in path_source
    assert "float(destination[0])" in path_source
    assert "self._remove_collinear_waypoints" in path_source
    assert "self._connector_is_risk_free(start, end)" in simplify_source
    assert "risk_polygons=self.risk_polygons" in search_source
    assert "self.connector_is_risk_free(location, node_location)" in snap_source


def test_navigation_and_coverage_use_query_local_virtual_edge_endpoints() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    search_source = ast.unparse(methods["_search_route"])
    coverage_source = ast.unparse(methods["_route_agent_to_coverage_chunk"])
    navigation_source = ast.unparse(methods["_navigation_path_from_route"])
    planner_methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    initialize_source = ast.unparse(planner_methods["initialize_map"])

    assert "EdgeSnapIndex" in search_source
    assert "add_virtual_endpoint_nodes" in search_source
    assert "start_node=resolved[0]['node']" in search_source
    assert "destination_node=resolved[1]['node']" in search_source
    assert "self._navigation_path_from_route" in coverage_source
    assert "agent.localization" in coverage_source
    assert "route_graph.nodes" in navigation_source
    assert "set_graph(self.G, projected_graph=G_proj)" in initialize_source


def test_successful_plan_is_cached_until_an_explicit_new_request() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    planning_source = ast.unparse(methods["planning_timer_callback"])
    create_source = ast.unparse(methods["set_mission_service_callback"])

    planned_state = "self.planner_states.update({mission_id: 2})"
    stop_planning = "self.mission_defined = False"
    assert planned_state in planning_source
    assert planning_source.index(stop_planning, planning_source.index(planned_state)) > planning_source.index(planned_state)
    assert "self.mission_defined = True" in create_source


def test_multi_vehicle_planning_waits_for_every_selected_agent() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    planning_source = ast.unparse(methods["planning_timer_callback"])

    assert "missing_agents" in planning_source
    assert "agent_id not in live_agents" in planning_source
    assert "agents_to_plan = [live_agents[agent_id] for agent_id in mission_agents]" in planning_source


def test_custom_start_geometry_is_an_executable_staging_waypoint() -> None:
    methods = _class_methods(
        PATH_LIBRARY / "multi_robot_path_planning.py",
        "MultiRobotPathPlanning",
    )
    source = ast.unparse(methods["_start_formation_allocations"])

    assert "start.get('geometry')" in source
    assert "transit.get('vehicle_formation')" in source
    assert "placements = [list(center_coordinates) for _ in ordered_agents]" in source


def test_planner_injects_world_risk_polygons_into_mission_planner() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")
    source = ast.unparse(methods["initialize_map"])

    assert "self.risk_poly_gdfs" in source
    assert "risk_polygons=risk_polygons" in source


def test_diagnostic_graph_rendering_never_blocks_planner_callbacks() -> None:
    methods = _class_methods(PLANNER_SOURCE, "PlannerNode")

    assert "plot_graph_service" not in ast.unparse(methods["initialize_map"])
    assert "plot_graph_service" not in ast.unparse(
        methods["planning_timer_callback"]
    )
