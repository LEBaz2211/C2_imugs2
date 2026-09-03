import json
import math
import networkx as nx
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import transform
import geopandas as gpd

from .models import *
from .mapf import *
from .graph import EdgeSnapIndex, add_virtual_endpoint_nodes
from .task_allocation import *
from .max_coverage import *

class MultiRobotPathPlanning:
    def __init__(self, mapf, mongodb_url, db, risk_polygons=None):
        """
        Initialize the MultiRobotPathPlanning with database parameters.
        :param mongodb_url: URL of the MongoDB database.
        :param db: Name of the database.
        """
        self.missions = {}  # Store mission data by ID
        self.mapf = mapf
        self.graph = None
        self.mongodb_url = mongodb_url
        self.db = db
        self.risk_polygons = list(risk_polygons or [])
        self.edge_snap_index = None
        self.plan_metadata = {}

    def set_graph(self, graph, projected_graph=None):
        """Install one immutable map snapshot graph and its read-only snap index."""
        self.graph = graph
        self.edge_snap_index = EdgeSnapIndex(graph, projected_graph=projected_graph)

    def update_mission(self, mission_id, mission_str, map_feature_collection):
        """
        Parse and store mission data by ID.
        :param mission_id: Unique mission identifier.
        :param mission_str: JSON string containing mission configuration.
        """
        data = json.loads(mission_str)
        transit = data.get("transit")
        if isinstance(transit, dict):
            if "optimization" not in transit and "optimalization" in transit:
                transit["optimization"] = transit["optimalization"]
            if (
                "geofence_maximize_coverage" not in transit
                and "geofence_maximum_coverage" in transit
            ):
                transit["geofence_maximize_coverage"] = transit[
                    "geofence_maximum_coverage"
                ]
        objective = data.get("objective")
        if isinstance(objective, dict):
            if (
                "maximum_coverage_distances" not in objective
                and "maximize_coverage_distances" in objective
            ):
                objective["maximum_coverage_distances"] = objective[
                    "maximize_coverage_distances"
                ]
            if "maximize_coverage" not in objective and int(data.get("behavior", 0)) == 1:
                objective["maximize_coverage"] = True

        # Resolve every geometry-bearing field from the exact active-world
        # collection. Objective-only resolution made LOS, orientation origins,
        # starts and geofences silently non-executable.
        objective = data["objective"]
        objective["geometries"] = [
            self._resolve_geometry_ref(item, map_feature_collection)
            for item in objective["geometries"]
        ]
        for key in ("vehicle_orientation_origin", "line_of_sight"):
            if isinstance(objective.get(key), dict):
                objective[key] = self._resolve_geometry_ref(
                    objective[key], map_feature_collection
                )
        start = data.get("start")
        if isinstance(start, dict) and isinstance(start.get("geometry"), dict):
            start["geometry"] = self._resolve_geometry_ref(
                start["geometry"], map_feature_collection
            )
        transit = data.get("transit")
        if isinstance(transit, dict):
            if isinstance(transit.get("geofence"), dict):
                transit["geofence"] = self._resolve_geometry_ref(
                    transit["geofence"], map_feature_collection
                )
            if isinstance(transit.get("roads"), list):
                transit["roads"] = [
                    self._resolve_geometry_ref(item, map_feature_collection)
                    for item in transit["roads"]
                ]

        self.missions[mission_id] = data

    def _resolve_geometry_ref(self, geometry_ref, feature_collection):
        if not isinstance(geometry_ref, dict) or "feature_id" not in geometry_ref:
            return geometry_ref
        feature_id = geometry_ref["feature_id"]
        fetched_features = self.read_features_from_db(
            feature_collection=feature_collection,
            feature_id=feature_id,
            crs="epsg:4326",
        )
        if not fetched_features:
            raise ValueError(
                f"Mission feature_id {feature_id!r} is not present in the active world"
            )
        geometry = fetched_features[0].geometry.iloc[0]
        geometry_type = geometry.geom_type
        if geometry_type == "Polygon":
            coordinates = [list(geometry.exterior.coords)]
            coordinates.extend(list(ring.coords) for ring in geometry.interiors)
        elif geometry_type == "MultiPoint":
            coordinates = [[point.x, point.y] for point in geometry.geoms]
        else:
            coordinates = list(geometry.coords)
        return {
            "feature_id": feature_id,
            "geometry": {"coordinates": coordinates, "geometry_type": geometry_type},
        }

    def solve_mission(self, mission_id, agents_to_plan):
        if mission_id not in self.missions:
            raise ValueError(f"Mission ID {mission_id} not found.")
        mission = self.missions[mission_id]
        points, shaped_geometries = self._mission_geometry_groups(mission)
        behavior = int(mission.get("behavior", 0))
        if behavior == 0:
            paths = self._solve_navigation(
                mission, agents_to_plan, points, shaped_geometries
            )
        elif behavior == 1:
            paths = self._solve_coverage(
                mission, agents_to_plan, points, shaped_geometries
            )
        else:
            raise ValueError(
                "NAVIGATE_NO_PLANNING is not executable by the editable path planner"
            )
        if not paths:
            raise RuntimeError("Mission produced no executable agent paths")
        self.plan_metadata[mission_id] = self._build_plan_metadata(mission, paths)
        return paths

    @staticmethod
    def _mission_geometry_groups(mission):
        points = []
        shaped_geometries = []
        for geometry_obj in mission["objective"]["geometries"]:
            geometry = geometry_obj.get("geometry") if isinstance(geometry_obj, dict) else None
            if not isinstance(geometry, dict):
                raise ValueError("Mission geometry was not resolved from the active world")
            geometry_type = geometry.get("geometry_type")
            coordinates = geometry.get("coordinates")
            if geometry_type == "Point":
                points.append(MultiRobotPathPlanning._point_coordinates(coordinates))
            elif geometry_type == "MultiPoint":
                points.extend(
                    MultiRobotPathPlanning._point_coordinates(point)
                    for point in coordinates
                )
            elif geometry_type in ("Polygon", "LineString"):
                shaped_geometries.append((geometry_type, coordinates))
            else:
                raise ValueError(f"Unsupported geometry type: {geometry_type}")
        return points, shaped_geometries

    @staticmethod
    def _point_coordinates(coordinates):
        while (
            isinstance(coordinates, (list, tuple))
            and len(coordinates) == 1
            and isinstance(coordinates[0], (list, tuple))
        ):
            coordinates = coordinates[0]
        if (
            not isinstance(coordinates, (list, tuple))
            or len(coordinates) < 2
            or not all(isinstance(value, (int, float)) for value in coordinates[:2])
        ):
            raise ValueError(f"Invalid Point coordinates: {coordinates!r}")
        return [float(coordinates[0]), float(coordinates[1])]

    def _solve_navigation(self, mission, agents_to_plan, points, shaped_geometries):
        objective = mission["objective"]
        deploy_point_as_group = bool(
            len(points) == 1
            and (
                objective.get("vehicle_formation")
                or objective.get("minimum_distance") is not None
                or objective.get("maximum_distance") is not None
                or objective.get("maximize_coverage") is True
            )
        )
        if deploy_point_as_group:
            point_placements = self._point_objective_placements(
                mission, points[0], len(agents_to_plan)
            )
            allocations = self._allocate_points(
                agents_to_plan,
                point_placements,
                preserve_order=bool(objective.get("vehicle_order")),
            )
            points = []
        else:
            allocations = self._allocate_points(
                agents_to_plan,
                points,
                preserve_order=bool(objective.get("vehicle_order")),
            )
        remaining_agents = [
            agent for agent in agents_to_plan if not allocations.get(agent.agent_id)
        ]
        if shaped_geometries:
            if not remaining_agents and not points:
                remaining_agents = list(agents_to_plan)
            geometry_groups = self._divide_agents(
                remaining_agents or list(agents_to_plan), len(shaped_geometries)
            )
            for (geometry_type, coordinates), group in zip(
                shaped_geometries, geometry_groups
            ):
                if not group:
                    continue
                placements = self._placement_points_for_geometry(
                    mission, geometry_type, coordinates, len(group)
                )
                group_allocations = self._allocate_points(
                    group,
                    placements,
                    preserve_order=bool(objective.get("vehicle_order")),
                )
                for agent_id, goals in group_allocations.items():
                    allocations.setdefault(agent_id, []).extend(goals)
        start_allocations = self._start_formation_allocations(
            mission, agents_to_plan
        )
        for agent_id, goals in start_allocations.items():
            allocations[agent_id] = [*goals, *allocations.get(agent_id, [])]
        return self._paths_for_allocations(mission, agents_to_plan, allocations)

    def _start_formation_allocations(self, mission, agents_to_plan):
        start = mission.get("start")
        if not isinstance(start, dict):
            return {}
        center_coordinates = self._representative_geometry_point(
            start.get("geometry")
        )
        if not center_coordinates:
            return {}
        ordered_agents = self._ordered_agents(mission, agents_to_plan)
        transit = mission.get("transit") or {}
        formation = int(
            start.get("vehicle_formation")
            or transit.get("vehicle_formation")
            or 0
        )
        spacing = float(
            start.get("vehicle_formation_distance")
            or transit.get("vehicle_formation_distance")
            or 5.0
        )
        if formation:
            placements = self._formation_points(
                Point(center_coordinates[0], center_coordinates[1]),
                len(ordered_agents),
                formation,
                spacing,
            )
        else:
            # A custom mission start is a real staging waypoint even when no
            # explicit formation is requested. Preserve order and use the
            # same point; the world author controls initial separation.
            placements = [list(center_coordinates) for _ in ordered_agents]
        return self._allocate_points(
            ordered_agents, placements, preserve_order=True
        )

    def _point_objective_placements(self, mission, coordinates, vehicle_count):
        objective = mission["objective"]
        point = Point(coordinates)
        minimum = max(0.0, float(objective.get("minimum_distance") or 0.0))
        maximum = objective.get("maximum_distance")
        radius = (
            (minimum + float(maximum)) / 2.0
            if maximum is not None
            else minimum
        )
        formation = int(objective.get("vehicle_formation") or 0)
        spacing = float(objective.get("vehicle_formation_distance") or 5.0)
        origin = self._representative_geometry_point(
            objective.get("vehicle_orientation_origin")
        )
        to_local, to_wgs84 = self._local_projection(point)
        local_point = transform(to_local.transform, point)
        if origin:
            origin_x, origin_y = to_local.transform(origin[0], origin[1])
            delta_x = origin_x - local_point.x
            delta_y = origin_y - local_point.y
            norm = math.hypot(delta_x, delta_y) or 1.0
            direction = (delta_x / norm, delta_y / norm)
        else:
            direction = (0.0, 1.0)
        center_x = local_point.x + direction[0] * radius
        center_y = local_point.y + direction[1] * radius

        if formation == 2:  # LINE: put the protective flank across the threat axis.
            perpendicular = (-direction[1], direction[0])
            middle = (vehicle_count - 1) / 2.0
            local_points = [
                (
                    center_x + perpendicular[0] * (index - middle) * spacing,
                    center_y + perpendicular[1] * (index - middle) * spacing,
                )
                for index in range(vehicle_count)
            ]
        elif formation:
            center_lon, center_lat = to_wgs84.transform(center_x, center_y)
            return self._formation_points(
                Point(center_lon, center_lat), vehicle_count, formation, spacing
            )
        else:
            # Spatial deployment around a Point uses an even ring when no
            # explicit formation is requested.
            local_points = [
                (
                    center_x + math.cos(2.0 * math.pi * index / vehicle_count) * spacing,
                    center_y + math.sin(2.0 * math.pi * index / vehicle_count) * spacing,
                )
                for index in range(vehicle_count)
            ]
        return [
            [float(lon), float(lat)]
            for lon, lat in (
                to_wgs84.transform(x_coord, y_coord)
                for x_coord, y_coord in local_points
            )
        ]

    @staticmethod
    def _divide_agents(agents, group_count):
        if group_count <= 0:
            return []
        return [
            agents[round(index * len(agents) / group_count): round((index + 1) * len(agents) / group_count)]
            for index in range(group_count)
        ]

    @staticmethod
    def _allocate_points(agents, points, preserve_order=False):
        if not agents or not points:
            return {}
        allocations = {agent.agent_id: [] for agent in agents}
        if preserve_order:
            for index, point in enumerate(points):
                allocations[agents[index % len(agents)].agent_id].append(point)
            return {agent_id: goals for agent_id, goals in allocations.items() if goals}

        remaining = list(points)
        current = {agent.agent_id: list(agent.localization) for agent in agents}
        one_to_one = len(points) <= len(agents)
        # Assign the globally closest remaining agent/goal pair, then continue
        # from each agent's last assigned goal. This handles both one-responder
        # selection and true multi-stop missions without the inherited mTSP
        # index bug.
        while remaining:
            candidates = [
                (
                    MultiRobotPathPlanning._path_length_m([current[agent.agent_id], point]),
                    agent.agent_id,
                    point_index,
                )
                for point_index, point in enumerate(remaining)
                for agent in agents
            ]
            _, agent_id, point_index = min(candidates)
            point = remaining.pop(point_index)
            allocations[agent_id].append(point)
            current[agent_id] = point
            if one_to_one:
                agents = [agent for agent in agents if agent.agent_id != agent_id]
                if not agents:
                    break
        return {agent_id: goals for agent_id, goals in allocations.items() if goals}

    def _paths_for_allocations(self, mission, agents_to_plan, allocations):
        paths = {}
        optimization = ((mission.get("transit") or {}).get("optimization") or {})
        constraints = (
            (mission.get("transit") or {}).get("desired_vehicle_constraints") or {}
        )
        geofence = (mission.get("transit") or {}).get("geofence")
        for agent_id, goals in allocations.items():
            agent = next(agent for agent in agents_to_plan if agent.agent_id == agent_id)
            current = [float(agent.localization[0]), float(agent.localization[1])]
            path = [current]
            for destination in goals:
                route, route_graph = self._search_route(
                    agent,
                    destination,
                    start=current,
                    optimization=optimization,
                    constraints=constraints,
                    geofence=geofence,
                )
                segment = self._navigation_path_from_route(
                    route, route_graph, current, destination
                )
                path.extend(segment[1:])
                current = [float(destination[0]), float(destination[1])]
            paths[agent_id] = self._remove_collinear_waypoints(path)
        return paths

    def _placement_points_for_geometry(
        self, mission, geometry_type, coordinates, vehicle_count
    ):
        objective = mission["objective"]
        if geometry_type == "LineString":
            line = LineString(coordinates)
            separations = objective.get("maximum_coverage_distances")
            if isinstance(separations, list) and separations and vehicle_count > 1:
                maximum_separation = max(float(value) for value in separations)
                required_separation = self._path_length_m(coordinates) / (vehicle_count - 1)
                if required_separation > maximum_separation + 1e-6:
                    raise ValueError(
                        f"Line deployment requires {required_separation:.1f} m vehicle spacing, "
                        f"exceeding the requested {maximum_separation:.1f} m maximum"
                    )
            return [
                list(line.interpolate(index / max(vehicle_count - 1, 1), normalized=True).coords[0])
                for index in range(vehicle_count)
            ]

        polygon = self._polygon(coordinates)
        minimum_distance = max(0.0, float(objective.get("minimum_distance") or 0.0))
        maximum_distance = objective.get("maximum_distance")
        if minimum_distance > 0 or maximum_distance is not None:
            outer = float(maximum_distance) if maximum_distance is not None else minimum_distance
            distance = (minimum_distance + outer) / 2.0
            return self._polygon_standoff_points(polygon, vehicle_count, distance)

        formation = int(objective.get("vehicle_formation") or 0)
        if formation:
            return self._formation_points(
                polygon.representative_point(),
                vehicle_count,
                formation,
                float(objective.get("vehicle_formation_distance") or 5.0),
                polygon,
            )

        candidates = [
            Point(float(data["x"]), float(data["y"]))
            for _, data in self.graph.nodes(data=True)
            if polygon.covers(Point(float(data["x"]), float(data["y"])))
        ]
        if not candidates:
            candidates = [polygon.representative_point()]
        selected = [min(candidates, key=lambda point: point.distance(polygon.centroid))]
        while len(selected) < vehicle_count:
            selected.append(
                max(candidates, key=lambda point: min(point.distance(item) for item in selected))
            )
        return [[float(point.x), float(point.y)] for point in selected[:vehicle_count]]

    @staticmethod
    def _polygon(coordinates):
        rings = coordinates
        if rings and isinstance(rings[0][0], (int, float)):
            rings = [rings]
        polygon = Polygon(rings[0], holes=rings[1:] or None)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty:
            raise ValueError("Objective Polygon is empty")
        return polygon

    @staticmethod
    def _local_projection(geometry):
        centroid = geometry.centroid
        zone = min(60, max(1, int((centroid.x + 180.0) // 6.0) + 1))
        epsg = (32600 if centroid.y >= 0 else 32700) + zone
        local = CRS.from_epsg(epsg)
        to_local = Transformer.from_crs("EPSG:4326", local, always_xy=True)
        to_wgs84 = Transformer.from_crs(local, "EPSG:4326", always_xy=True)
        return to_local, to_wgs84

    def _polygon_standoff_points(self, polygon, vehicle_count, distance_m):
        to_local, to_wgs84 = self._local_projection(polygon)
        projected = transform(to_local.transform, polygon)
        ring = projected.buffer(distance_m).exterior
        points = []
        for index in range(vehicle_count):
            point = ring.interpolate(index / vehicle_count, normalized=True)
            lon, lat = to_wgs84.transform(point.x, point.y)
            points.append([float(lon), float(lat)])
        return points

    def _formation_points(
        self, center, vehicle_count, formation, spacing_m, containing_polygon=None
    ):
        to_local, to_wgs84 = self._local_projection(center)
        local_center = transform(to_local.transform, center)
        offsets = []
        middle = (vehicle_count - 1) / 2.0
        for index in range(vehicle_count):
            relative = index - middle
            if formation == 1:  # COLUMN
                offset = (0.0, -relative * spacing_m)
            elif formation == 2:  # LINE
                offset = (relative * spacing_m, 0.0)
            elif formation in (3, 4):  # WEDGE / VEE
                sign = -1.0 if formation == 3 else 1.0
                offset = (relative * spacing_m, sign * abs(relative) * spacing_m)
            elif formation == 5:  # LEFT_FLANK
                offset = (-index * spacing_m, -index * spacing_m)
            elif formation == 6:  # RIGHT_FLANK
                offset = (index * spacing_m, -index * spacing_m)
            else:
                offset = (relative * spacing_m, 0.0)
            lon, lat = to_wgs84.transform(
                local_center.x + offset[0], local_center.y + offset[1]
            )
            candidate = Point(lon, lat)
            if containing_polygon is not None and not containing_polygon.covers(candidate):
                candidate = containing_polygon.representative_point()
            offsets.append([float(candidate.x), float(candidate.y)])
        return offsets

    def _solve_coverage(self, mission, agents_to_plan, points, shaped_geometries):
        if mission["objective"].get("maximize_coverage") is False:
            return self._solve_navigation(
                mission, agents_to_plan, points, shaped_geometries
            )
        if points and not shaped_geometries:
            return self._solve_navigation(mission, agents_to_plan, points, [])
        if not shaped_geometries:
            raise ValueError("Coverage behavior requires Polygon or LineString geometry")

        paths = {}
        road_usage_value = (
            ((mission.get("transit") or {}).get("optimization") or {}).get(
                "road_usage"
            )
        )
        road_usage = 0.5 if road_usage_value is None else float(road_usage_value)
        ordered_agents = self._ordered_agents(mission, agents_to_plan)
        for geometry_type, coordinates in shaped_geometries:
            if geometry_type == "LineString":
                work_path = [[float(point[0]), float(point[1])] for point in coordinates]
                action = "line_patrol"
            elif road_usage >= 0.999:
                work_path = self._road_patrol_path(coordinates)
                action = "road_patrol"
            else:
                widths = self._coverage_widths_by_vehicle(mission)
                swath_width = min(widths[agent.agent_id] for agent in ordered_agents)
                work_path = lawnmower_coverage_path(
                    coordinates,
                    swath_width,
                    risk_polygons=self.risk_polygons,
                )
                action = "area_coverage"
            chunks = self._split_continuous_path(work_path, len(ordered_agents))
            for agent, chunk in zip(ordered_agents, chunks):
                routed = self._route_agent_to_coverage_chunk(
                    agent, chunk, mission=mission
                )
                if agent.agent_id in paths:
                    paths[agent.agent_id].extend(routed[1:])
                else:
                    paths[agent.agent_id] = routed
            mission.setdefault("planner_hints", {})["coverage_action"] = action
        return paths

    @staticmethod
    def _ordered_agents(mission, agents):
        order = {vehicle_id: index for index, vehicle_id in enumerate(mission["vehicles"])}
        return sorted(agents, key=lambda agent: order.get(agent.agent_id, len(order)))

    def _road_patrol_path(self, coordinates):
        polygon = self._polygon(coordinates)
        road_graph = nx.Graph()
        for start, end, data in self.graph.edges(data=True):
            if data.get("risk", False) or data.get("surface") != "road":
                continue
            start_point = Point(self.graph.nodes[start]["x"], self.graph.nodes[start]["y"])
            end_point = Point(self.graph.nodes[end]["x"], self.graph.nodes[end]["y"])
            if polygon.covers(start_point) and polygon.covers(end_point):
                road_graph.add_edge(start, end)
        if road_graph.number_of_edges() == 0:
            raise ValueError("Road patrol objective contains no active-world road edges")
        components = list(nx.connected_components(road_graph))
        if len(components) != 1:
            raise ValueError(
                "Road patrol objective contains disconnected active-world road components"
            )
        patrol_graph = road_graph.subgraph(components[0]).copy()
        # Traverse every eligible road edge, not only a DFS spanning tree.  An
        # Eulerized copy duplicates the minimum connecting edges needed to
        # produce one continuous closed patrol without changing the world graph.
        euler_graph = (
            patrol_graph if nx.is_eulerian(patrol_graph) else nx.eulerize(patrol_graph)
        )
        circuit = list(
            nx.eulerian_circuit(euler_graph, source=next(iter(euler_graph.nodes)))
        )
        walk = [circuit[0][0], *(end for _, end in circuit)]
        return [
            [float(self.graph.nodes[node]["x"]), float(self.graph.nodes[node]["y"])]
            for node in walk
        ]

    def _build_plan_metadata(self, mission, paths):
        objective = mission.get("objective") or {}
        headings = objective.get("vehicle_orientation") or []
        origin = self._representative_geometry_point(
            objective.get("vehicle_orientation_origin")
        )
        line_of_sight = self._representative_geometry_point(objective.get("line_of_sight"))
        ordered_ids = list(mission.get("vehicles") or [])
        metadata = {}
        for agent_id, path in paths.items():
            index = ordered_ids.index(agent_id) if agent_id in ordered_ids else 0
            requested_heading = headings[index] if len(headings) > 1 and index < len(headings) else (headings[0] if headings else None)
            final_heading = requested_heading
            if requested_heading is not None and origin and path:
                final_heading = (
                    self._bearing_degrees(path[-1], origin) + float(requested_heading)
                ) % 360.0
            metadata[agent_id] = {
                "phase": mission.get("phase"),
                "behavior": mission.get("behavior"),
                "required_capabilities": mission.get("required_capabilities") or [],
                "payload_action": mission.get("payload_action"),
                "start_vehicle_formation": (mission.get("start") or {}).get(
                    "vehicle_formation"
                ),
                "start_vehicle_formation_distance": (mission.get("start") or {}).get(
                    "vehicle_formation_distance"
                ),
                "transit_vehicle_formation": (mission.get("transit") or {}).get(
                    "vehicle_formation"
                ),
                "transit_vehicle_formation_distance": (mission.get("transit") or {}).get(
                    "vehicle_formation_distance"
                ),
                "coverage_action": (mission.get("planner_hints") or {}).get("coverage_action"),
                "vehicle_formation": objective.get("vehicle_formation"),
                "vehicle_formation_distance": objective.get("vehicle_formation_distance"),
                "desired_heading_deg": final_heading,
                "line_of_sight_target": line_of_sight,
                "line_of_sight_propagation": bool(objective.get("line_of_sight_propagation")),
                "start_time": (mission.get("start") or {}).get("start_time"),
                "arrival_time": objective.get("arrival_time"),
                "mission_end_time": mission.get("mission_end_time"),
                "desired_vehicle_constraints": (mission.get("transit") or {}).get("desired_vehicle_constraints") or {},
                "optimization": (mission.get("transit") or {}).get("optimization") or {},
            }
        return metadata

    @staticmethod
    def _representative_geometry_point(geometry_ref):
        if not isinstance(geometry_ref, dict):
            return None
        geometry = geometry_ref.get("geometry")
        if not isinstance(geometry, dict):
            return None
        geometry_type = geometry.get("geometry_type")
        coordinates = geometry.get("coordinates")
        if geometry_type == "Point":
            return MultiRobotPathPlanning._point_coordinates(coordinates)
        try:
            if geometry_type == "LineString":
                point = LineString(coordinates).centroid
            elif geometry_type == "Polygon":
                point = MultiRobotPathPlanning._polygon(coordinates).centroid
            else:
                return None
        except (TypeError, ValueError):
            return None
        return [float(point.x), float(point.y)]

    @staticmethod
    def _bearing_degrees(start, destination):
        mean_latitude = math.radians((start[1] + destination[1]) / 2.0)
        east = (destination[0] - start[0]) * math.cos(mean_latitude)
        north = destination[1] - start[1]
        return math.degrees(math.atan2(east, north)) % 360.0

    def get_path_metadata(self, mission_id, agent_id):
        return (self.plan_metadata.get(mission_id) or {}).get(agent_id) or {}

    def _navigation_path_from_route(self, route, route_graph, start, destination):
        """Attach a graph route to its exact endpoints and remove graph noise."""
        # Task allocation stores each robot's ordered goals as a list. Point
        # navigation currently plans the first goal in that list, matching
        # AStar's ordered-destination contract.
        if destination and isinstance(destination[0], (list, tuple)):
            destination = destination[0]
        path = [[float(start[0]), float(start[1])]]
        path.extend(
            [
                float(route_graph.nodes[state.get_node()]["x"]),
                float(route_graph.nodes[state.get_node()]["y"]),
            ]
            for state in route
        )
        path.append([float(destination[0]), float(destination[1])])

        deduplicated = []
        for point in path:
            if not deduplicated or point != deduplicated[-1]:
                deduplicated.append(point)
        return self._remove_collinear_waypoints(deduplicated)

    def _remove_collinear_waypoints(self, path, tolerance_m=0.05):
        """Collapse redundant lattice nodes without changing route geometry."""
        simplified = []
        for point in path:
            simplified.append(point)
            while len(simplified) >= 3:
                start, middle, end = simplified[-3:]
                if not self._is_between_on_same_line(
                    start,
                    middle,
                    end,
                    tolerance_m,
                ):
                    break
                if not self._connector_is_risk_free(start, end):
                    break
                simplified.pop(-2)
        return simplified

    @staticmethod
    def _is_between_on_same_line(start, middle, end, tolerance_m):
        """Test collinearity in a small local metric approximation."""
        mean_latitude = math.radians((start[1] + middle[1] + end[1]) / 3.0)
        metres_per_lon_degree = 111320.0 * math.cos(mean_latitude)
        metres_per_lat_degree = 110540.0

        first = (
            (middle[0] - start[0]) * metres_per_lon_degree,
            (middle[1] - start[1]) * metres_per_lat_degree,
        )
        second = (
            (end[0] - middle[0]) * metres_per_lon_degree,
            (end[1] - middle[1]) * metres_per_lat_degree,
        )
        combined = (first[0] + second[0], first[1] + second[1])
        combined_length = math.hypot(*combined)
        if combined_length == 0:
            return False

        perpendicular_distance = abs(
            first[0] * second[1] - first[1] * second[0]
        ) / combined_length
        continues_forward = first[0] * second[0] + first[1] * second[1] >= 0
        return continues_forward and perpendicular_distance <= tolerance_m

    @staticmethod
    def _coverage_widths_by_vehicle(mission):
        objective = mission["objective"]
        raw_widths = objective.get("coverage_swath_widths")

        if not isinstance(raw_widths, list) or not raw_widths:
            raise ValueError(
                "Polygon coverage requires sensor-derived objective.coverage_swath_widths"
            )

        widths = []
        for value in raw_widths:
            try:
                width = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Coverage swath widths must be numbers in metres") from exc
            if width <= 0:
                raise ValueError("Coverage swath widths must be greater than zero metres")
            widths.append(width)

        vehicles = mission["vehicles"]
        if len(widths) == 1:
            widths *= len(vehicles)
        elif len(widths) != len(vehicles):
            raise ValueError(
                "Coverage width list must contain one shared width or one width per mission vehicle"
            )
        return dict(zip(vehicles, widths))

    @staticmethod
    def _split_continuous_path(path, chunk_count):
        if chunk_count <= 0:
            raise ValueError("Coverage planning requires at least one live agent")
        if len(path) <= 1:
            return [path[:] for _ in range(chunk_count)]

        segment_lengths = [
            MultiRobotPathPlanning._path_length_m([start, end])
            for start, end in zip(path, path[1:])
        ]
        cumulative = [0.0]
        for length in segment_lengths:
            cumulative.append(cumulative[-1] + length)
        total_length = cumulative[-1]
        if total_length <= 0:
            return [[path[0]] for _ in range(chunk_count)]

        def point_at(distance):
            if distance <= 0:
                return [float(path[0][0]), float(path[0][1])]
            if distance >= total_length:
                return [float(path[-1][0]), float(path[-1][1])]
            for index, segment_end in enumerate(cumulative[1:]):
                if distance > segment_end:
                    continue
                segment_start = cumulative[index]
                segment_length = segment_lengths[index]
                fraction = 0.0 if segment_length <= 0 else (distance - segment_start) / segment_length
                return [
                    float(path[index][axis])
                    + fraction * (float(path[index + 1][axis]) - float(path[index][axis]))
                    for axis in (0, 1)
                ]
            return [float(path[-1][0]), float(path[-1][1])]

        chunks = []
        for index in range(chunk_count):
            start_distance = total_length * index / chunk_count
            end_distance = total_length * (index + 1) / chunk_count
            chunk = [point_at(start_distance)]
            chunk.extend(
                [float(path[point_index][0]), float(path[point_index][1])]
                for point_index in range(1, len(path) - 1)
                if start_distance < cumulative[point_index] < end_distance
            )
            end_point = point_at(end_distance)
            if end_point != chunk[-1]:
                chunk.append(end_point)
            chunks.append(chunk)
        return chunks

    def _route_agent_to_coverage_chunk(self, agent, chunk, mission=None):
        if not chunk:
            raise ValueError(f"Coverage path for agent {agent.agent_id} is empty")

        orientations = [chunk, list(reversed(chunk))]
        orientations.sort(
            key=lambda candidate: sum(
                (candidate[0][axis] - agent.localization[axis]) ** 2 for axis in (0, 1)
            )
        )
        failures = []
        candidates = []
        for coverage_points in orientations:
            entry = coverage_points[0]
            try:
                route, route_graph = self._search_route(
                    agent,
                    entry,
                    optimization=((mission or {}).get("transit") or {}).get("optimization") or {},
                    constraints=((mission or {}).get("transit") or {}).get("desired_vehicle_constraints") or {},
                    geofence=((mission or {}).get("transit") or {}).get("geofence"),
                )
            except RuntimeError as exc:
                failures.append(str(exc))
                continue

            path = self._navigation_path_from_route(
                route,
                route_graph,
                agent.localization,
                entry,
            )
            transit_length = self._path_length_m(path)
            for point in coverage_points[1:]:
                point = [float(point[0]), float(point[1])]
                if not path or point != path[-1]:
                    path.append(point)
            candidates.append((transit_length, path))

        if candidates:
            return min(candidates, key=lambda candidate: candidate[0])[1]

        raise RuntimeError(
            f"No route from agent {agent.agent_id} to either end of its coverage sweep: "
            + "; ".join(failures)
        )

    def _connector_is_risk_free(self, start, destination):
        connector = LineString([start, destination])
        return not any(risk_polygon.intersects(connector) for risk_polygon in self.risk_polygons)

    @staticmethod
    def _path_length_m(path):
        total = 0.0
        for start, end in zip(path, path[1:]):
            mean_latitude = math.radians((start[1] + end[1]) / 2.0)
            dx = (end[0] - start[0]) * 111320.0 * math.cos(mean_latitude)
            dy = (end[1] - start[1]) * 110540.0
            total += math.hypot(dx, dy)
        return total

    def _search_route(
        self,
        agent,
        destination,
        start=None,
        optimization=None,
        constraints=None,
        geofence=None,
    ):
        """Run A* between query-local virtual nodes on the map snapshot graph."""
        if destination and isinstance(destination[0], (list, tuple)):
            destination = destination[0]
        start = start or agent.localization
        route_base_graph = self._geofenced_graph(geofence)
        snap_index = (
            self.edge_snap_index
            if route_base_graph is self.graph and self.edge_snap_index is not None
            else EdgeSnapIndex(route_base_graph)
        )
        if route_base_graph is self.graph and self.edge_snap_index is None:
            self.edge_snap_index = snap_index
        start_snap = snap_index.snap(start, self.risk_polygons)
        destination_snap = snap_index.snap(destination, self.risk_polygons)
        route_graph, resolved = add_virtual_endpoint_nodes(
            route_base_graph,
            [start_snap, destination_snap],
        )
        result = AStar(
            route_graph,
            agent,
            [destination],
            risk_polygons=self.risk_polygons,
            start_node=resolved[0]["node"],
            destination_node=resolved[1]["node"],
            optimization=optimization,
            constraints=constraints,
        ).search()
        if not result:
            raise RuntimeError(
                f"No route found for agent {agent.agent_id} "
                f"from {start} to {destination}"
            )

        route, _f_score = result
        if not route:
            raise RuntimeError(
                f"No route found for agent {agent.agent_id} "
                f"from {start} to {destination}"
            )
        return route, route_graph

    def _geofenced_graph(self, geometry_ref):
        if not isinstance(geometry_ref, dict):
            return self.graph
        geometry = geometry_ref.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("geometry_type") != "Polygon":
            return self.graph
        polygon = self._polygon(geometry.get("coordinates"))
        allowed_edges = []
        tolerant = polygon.buffer(1e-10)
        for start, end, key in self.graph.edges(keys=True):
            segment = LineString(
                [
                    (self.graph.nodes[start]["x"], self.graph.nodes[start]["y"]),
                    (self.graph.nodes[end]["x"], self.graph.nodes[end]["y"]),
                ]
            )
            if tolerant.covers(segment):
                allowed_edges.append((start, end, key))
        graph = self.graph.edge_subgraph(allowed_edges).copy()
        graph.graph.update(self.graph.graph)
        if graph.number_of_edges() == 0:
            raise ValueError("Transit geofence contains no routable active-world edges")
        return graph



    def get_mission_agents(self, mission_id):
        """
        Return vehicle IDs for the given mission ID.
        :param mission_id: Unique mission identifier.
        :return: List of vehicle IDs or None if the mission is not found.
        """
        mission = self.missions.get(mission_id)
        if mission:
            return mission["vehicles"]
        return None

    def get_max_speed(self, mission_id):
        """
        Return max speed for the given mission ID.
        :param mission_id: Unique mission identifier.
        :return: Max speed or None if the mission is not found.
        """
        mission = self.missions.get(mission_id)
        if not mission:
            return None

        # ``transit`` is optional in the canonical mission contract.  The
        # adapter normally supplies a backend-only value derived from the
        # selected agents, but direct ROS clients must not crash the planner
        # when they omit it.
        transit = mission.get("transit")
        constraints = (
            transit.get("desired_vehicle_constraints")
            if isinstance(transit, dict)
            else None
        )
        configured = constraints.get("max_speed") if isinstance(constraints, dict) else None
        try:
            speed = float(configured)
        except (TypeError, ValueError):
            return 1.0
        return speed if math.isfinite(speed) and speed > 0 else 1.0

    @staticmethod
    def read_features_from_db(feature_collection, feature_id=None, crs="epsg:4326"):
        """
        Fetch features from the database.
        """
        

        query = {"properties.feature_id": feature_id} if feature_id else {}
        cursor = feature_collection.find(query)

        features = []
        for document in cursor:
            try:
                geom = shape(document["geometry"])
                if geom.is_empty:
                    continue
                gdf = gpd.GeoDataFrame(
                    [document["properties"]],
                    geometry=[geom],
                    crs=crs
                )
                features.append(gdf)
            except Exception as e:
                print(f"Error processing document: {document}, Error: {e}")
        
        return features


# Example external algorithms
def mock_optimal_allocation(vehicles, points):
    allocation = {}
    for i, vehicle in enumerate(vehicles):
        if i < len(points):
            allocation[vehicle] = [points[i]]
    return allocation


def mock_optimal_coverage(geometry_type, coordinates, num_robots, return_paths=False):
    if return_paths:
        return {f"robot_{i}": coordinates[i::num_robots] for i in range(num_robots)}
    return coordinates[:num_robots]


def mock_path_planning(allocations, vehicles):
    paths = {}
    for vehicle, goals in allocations.items():
        paths[vehicle] = {"path": goals}
    return paths


# Example usage
if __name__ == "__main__":
    mr_path_planner = MultiRobotPathPlanning("independent_agents", "mongodb://localhost:27017/", "MapDB")

    mission_str = '''
    {
      "objective": {
        "geometries": [
            {
                "geometry": {
                    "coordinates": [
                        [
                        4.391893297982506,
                        50.844115083630555
                        ],
                        [
                        4.391710170382453,
                        50.84427476662046
                        ],
                        [
                        4.392039364043569,
                        50.844318817004506
                        ]
                    ],
                    "geometry_type": "MultiPoint"
                }
            },
            {
                "feature_id": "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e2c"
            }
        ],
        "maximize_coverage": true
      },
      "transit": {
        "desired_vehicle_constraints": {
          "max_speed": 3
        }
      },
      "_id": "6718c6707ae5cc161092ea63",
      "mission_id": "dc19d601-9473-4bca-a029-e39861a21b3c",
      "__v": 0,
      "behavior":0,
      "name": "Delivery",
      "vehicles": [
        "4dd12623-3fb6-4ae4-91c2-1f4b10d2327d",
        "2b4a887b-95af-451d-bd85-e0dcacb72524",
        "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
        "8ef41dae-86d0-41f5-a65d-d8cc5bab1cf6"
      ]
    }
    '''

    mission_id = "dc19d601-9473-4bca-a029-e39861a21b3c"

    # Create fictive agents
    agents_to_plan = dict()
    agent1 = Buddy("4dd12623-3fb6-4ae4-91c2-1f4b10d2327d", localization = [4.39243509551298, 50.84401341425075], current_speed = 0)
    agents_to_plan.update({"4dd12623-3fb6-4ae4-91c2-1f4b10d2327d" : agent1})

    agent2 = Buddy("2b4a887b-95af-451d-bd85-e0dcacb72524", localization = [4.3925015304592705, 50.84417264999087], current_speed = 0)
    agents_to_plan.update({"2b4a887b-95af-451d-bd85-e0dcacb72524" : agent2})

    agent3 = Buddy("f9992bb3-9871-451f-90a0-9207eb9fe6c5", localization = [4.391471110885902, 50.84404509022096], current_speed = 0)
    agents_to_plan.update({"f9992bb3-9871-451f-90a0-9207eb9fe6c5" : agent3})

    agent4 = Buddy("8ef41dae-86d0-41f5-a65d-d8cc5bab1cf6", localization = [4.391728715778754, 50.84452536378049], current_speed = 0)
    agents_to_plan.update({"8ef41dae-86d0-41f5-a65d-d8cc5bab1cf6" : agent4})


    mr_path_planner.update_mission(mission_id, mission_str)
    results = mr_path_planner.solve_mission(mission_id, agents_to_plan)
    print(results)
