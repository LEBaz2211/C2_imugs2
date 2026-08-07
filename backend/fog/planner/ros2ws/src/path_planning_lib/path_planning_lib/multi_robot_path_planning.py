import json
import math
import networkx as nx
from shapely.geometry import shape
import geopandas as gpd

from .models import *
from .mapf import *
from .task_allocation import *
from .max_coverage import *
from .utils import add_edge_lengths, distance_between_coordinates

class MultiRobotPathPlanning:
    def __init__(self , mapf , mongodb_url , db):
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
        self.local_feature_geometries = {}
        self.mission_road_connect_max_distance = 45.0
        self.mission_road_max_connectors_per_endpoint = 4
        self.path_simplification_tolerance_m = 12.0

    def update_mission(self, mission_id, mission_str, map_feature_collection):
        """
        Parse and store mission data by ID.
        :param mission_id: Unique mission identifier.
        :param mission_str: JSON string containing mission configuration.
        """
        data = json.loads(mission_str)

        # Resolve legacy feature_id references into inline geometry. The original
        # stack usually resolved these through MongoDB; the slim Docker stack uses
        # local GeoJSON files instead.
        for geometry_obj in data["objective"]["geometries"]:
            if "feature_id" in geometry_obj and "geometry" not in geometry_obj:
                feature_id = str(geometry_obj["feature_id"])
                geometry = self.local_feature_geometries.get(feature_id)
                if geometry is None:
                    fetched_features = self.read_features_from_db(
                        feature_collection = map_feature_collection,
                        feature_id=feature_id,
                        crs="epsg:4326"
                    )
                    if fetched_features:
                        geometry = fetched_features[0].geometry.iloc[0]

                if geometry is not None:
                    geometry_obj["geometry"] = self._to_mission_geometry(geometry)
                else:
                    print(f"Could not resolve feature_id '{feature_id}' to geometry.")

        transit = data.get("transit") or {}
        roads = transit.get("roads") if isinstance(transit, dict) else None
        if isinstance(roads, list):
            transit["roads"] = [self._resolved_geometry_ref(road, map_feature_collection) for road in roads]

        self.missions[mission_id] = data

    def solve_mission(self, mission_id, agents_to_plan):
        if mission_id not in self.missions:
            raise ValueError(f"Mission ID {mission_id} not found.")

        base_graph = self.graph
        self.graph = self._graph_with_mission_roads(self.missions[mission_id])
        try:
            return self._solve_mission_with_graph(mission_id, agents_to_plan)
        finally:
            self.graph = base_graph

    def _solve_mission_with_graph(self, mission_id, agents_to_plan):
        # Check mission exists
        if mission_id not in self.missions:
            raise ValueError(f"Mission ID {mission_id} not found.")

        mission = self.missions[mission_id]
        behavior = mission["behavior"]
        vehicles = mission["vehicles"]
        geometries = mission["objective"]["geometries"]
        road_usage = self.get_road_usage(mission_id)

        # Split geometries by type
        points = []
        polygons_or_lines = []
        for geometry_obj in geometries:
            geometry = geometry_obj.get("geometry")
            if not geometry:
                print(f"Skipping unresolved mission geometry: {geometry_obj}")
                continue

            geometry_type = geometry.get("geometry_type") or geometry.get("type")
            coordinates = geometry["coordinates"]

            if geometry_type == "Point":
                if coordinates and isinstance(coordinates[0], (int, float)):
                    points.append(coordinates)
                else:
                    points.append(coordinates[0])
            elif geometry_type =="MultiPoint": # Convert multipoints to individual points
                points.extend(point_coordinates for point_coordinates in coordinates)  # Convert each to "Point"
            elif geometry_type in ["Polygon", "LineString"]:
                polygons_or_lines.append((geometry_type, coordinates))
            else:
                raise ValueError(f"Unsupported geometry type: {geometry_type}")

        if behavior == 0 and points:
            # In point-navigation missions, LineStrings in objective.geometries
            # are route graph inputs. They have already been added to the graph
            # by _graph_with_mission_roads and should not become coverage goals.
            polygons_or_lines = [
                (geometry_type, coords)
                for geometry_type, coords in polygons_or_lines
                if geometry_type != "LineString"
            ]

        # Interpretation
        if behavior == 0:  # "go to" behavior
            allocations = {}
            allocator = TaskAllocator(distance_mode="euclidean")

            if points: # allocate an agent to every point
                # Case 1: More agents than points (Linear Sum Assignment)
                if len(points) <= len (vehicles):
                    allocations.update(allocator.hungarian_allocation(agents_to_plan,points))

                if len(points) > len (vehicles): # Multiple Traveling Salesmen Problem
                    allocations.update(allocator.solve_mtsp(agents_to_plan,points))


            if polygons_or_lines: # Remaining agents will go to the polygons or lines
                remaining_agents = [agent for agent in agents_to_plan if agent.agent_id not in allocations]
                max_cov = MaximizeCoverage(self.graph)
                for geometry_type, coords in polygons_or_lines:
                    candidate_nodes = max_cov.get_nodes_inside_geometry(geometry_type, coords)
                    coverage_points = max_cov.solve_mclp(candidate_nodes, len(remaining_agents))
                    allocations.update(allocator.hungarian_allocation(remaining_agents, coverage_points))


        elif behavior == 1:  # "explore" behavior
            allocations = {}
            allocator = TaskAllocator(distance_mode="euclidean")

            if points:
                allocations.update(allocator.hungarian_allocation(agents_to_plan, points))

            remaining_agents = [agent for agent in agents_to_plan if agent.agent_id not in allocations]
            if polygons_or_lines and remaining_agents:
                max_cov = MaximizeCoverage(self.graph)

                if len(remaining_agents) == 1:
                    agent = remaining_agents[0]
                    candidate_points = []
                    for geometry_type, coords in polygons_or_lines:
                        candidate_nodes = max_cov.get_nodes_inside_geometry(geometry_type, coords)
                        candidate_points.extend(self._candidate_points_for_nodes(candidate_nodes))

                    path = self._first_reachable_path(agent, candidate_points, road_usage)
                    if path:
                        return {agent.agent_id: path}

                    print(
                        f"No reachable risk-free coverage point found for agent {agent.agent_id}; "
                        "returning the current position only.",
                        flush=True,
                    )
                    return {agent.agent_id: [list(agent.localization)]}

                coverage_points = []
                for geometry_type, coords in polygons_or_lines:
                    candidate_nodes = max_cov.get_nodes_inside_geometry(geometry_type, coords)
                    selected_points = max_cov.solve_mclp(candidate_nodes, max(len(remaining_agents), 1))
                    if not selected_points:
                        selected_points = [self._representative_point(geometry_type, coords)]
                    coverage_points.extend(selected_points)
                allocations.update(allocator.hungarian_allocation(remaining_agents, coverage_points))
    
        else:
            raise ValueError(f"Unsupported behavior: {behavior}")

        # return path_planning_algorithm(allocations, vehicles)

        
        # assume one waypoint per agent, for now just randomly allocated
        # destination_points= self.mission_parser.get_mission_destinations(self.current_mission_id) 
        # self.allocate_destinations_to_agents(agents_to_plan, destination_points, "random")



        new_paths = dict()

        # Single Agent
        if len(allocations) == 1:
            # Get the agent and the destination assigned to this agent
            agent_id, destination = list(allocations.items())[0]  # Get the first (and only) agent-destination pair
            # agent = agents_to_plan[agent_id]  # Retrieve the agent object by agent_id
            agent = next(agent for agent in agents_to_plan if agent.agent_id == agent_id)

            
            # Perform A* pathfinding from the agent's current position to the destination
            path = self._a_star_or_direct_path(agent, destination, road_usage)
            
            # Store the calculated path for the agent
            new_paths[agent_id] = path
            

        # Multi-Agent
        elif (self.mapf == "independent_agents"):
            i = 0
            for agent_id, destination in allocations.items():
                # Retrieve the agent object using the agent_id
                # agent = agents_to_plan[agent_id]
                agent = next(agent for agent in agents_to_plan if agent.agent_id == agent_id)


                # Create an A* pathfinder for this agent, considering its assigned destination
                path = self._a_star_or_direct_path(agent, destination, road_usage)

                # Store the computed path for the agent
                new_paths[agent_id] = path
                i += 1

        elif (self.mapf == "cbs"): # Conflict Based Search
            # assume one waypoint per agent, for now allocated by order
            cbs = CBS(self.graph)
            plan = cbs.search(agents_to_plan, allocations)
            for agent_id, route in plan.items():
                path = []
                for state in route:
                    node = state.get_node()
                    path.append([self.graph.nodes[node]['x'],self.graph.nodes[node]['y']])
                # if(self.graph.nodes[destination_node]['x']!=destination[0] or self.graph.nodes[destination_node]['y']!=destination[1]):
                #     path.append(destination)
                new_paths[agent_id] = path
        return new_paths

    def _a_star_or_direct_path(self, agent, destination, road_usage=0.5):
        exact_destination = destination[0] if destination and isinstance(destination[0], list) else destination
        path = self._path_to_point(agent, exact_destination, road_usage, log_failure=True)
        if not path:
            print("A* failed to find a risk-free graph route; returning the current position only.")
            return [list(agent.localization)]
        return path

    def _graph_with_mission_roads(self, mission):
        road_geometries = self._mission_road_geometries(mission)
        if not road_geometries:
            return self.graph

        augmented = self.graph.copy()
        cell_size = self._connector_cell_size(self.mission_road_connect_max_distance)
        base_road_nodes = [node for node in augmented.nodes if self._node_has_road_edge(augmented, node)]
        mission_graph = nx.MultiDiGraph()
        next_node_id = self._next_mission_node_id(augmented)
        line_node_sources = {}
        connector_nodes = []
        total_edges = 0
        for index, coordinates in enumerate(road_geometries):
            line_graph, next_node_id = self._mission_line_graph(coordinates, index, next_node_id)
            if line_graph is None:
                continue
            endpoints = self._connector_nodes_for_line_graph(line_graph)
            connector_nodes.extend((node, index) for node in endpoints)
            for node in line_graph.nodes:
                line_node_sources[node] = index
            total_edges += line_graph.number_of_edges()
            mission_graph.add_nodes_from(line_graph.nodes(data=True))
            mission_graph.add_edges_from(line_graph.edges(keys=True, data=True))

        if mission_graph.number_of_edges() == 0:
            return self.graph
        augmented = nx.compose(augmented, mission_graph)

        road_node_index = {}
        existing_road_nodes = base_road_nodes + list(line_node_sources.keys())
        self._index_road_nodes(road_node_index, augmented, existing_road_nodes, cell_size)
        total_connectors = 0
        for mission_node, index in connector_nodes:
            mission_lat = augmented.nodes[mission_node]["y"]
            mission_lon = augmented.nodes[mission_node]["x"]
            for graph_node, distance_m in self._nearby_road_nodes(
                road_node_index,
                augmented,
                mission_lat,
                mission_lon,
                cell_size,
                line_node_sources=line_node_sources,
                exclude_line_source=index,
                exclude_nodes={mission_node},
            )[: self.mission_road_max_connectors_per_endpoint]:
                augmented.add_edge(
                    mission_node,
                    graph_node,
                    length=round(distance_m, 3),
                    road=True,
                    road_source="mission_connector",
                    risk=False,
                    feature_id=f"mission-road-{index}-connector",
                )
                total_connectors += 1
        print(
            f"Added {len(road_geometries)} mission road(s) with {total_edges} edge(s) and {total_connectors} connector(s).",
            flush=True,
        )
        return augmented

    def _mission_road_geometries(self, mission):
        candidates = []
        transit = mission.get("transit") or {}
        roads = transit.get("roads") if isinstance(transit, dict) else None
        if isinstance(roads, dict):
            roads = [roads]
        if isinstance(roads, list):
            candidates.extend(roads)

        objective = mission.get("objective") or {}
        objective_geometries = objective.get("geometries") if isinstance(objective, dict) else None
        if isinstance(objective_geometries, list):
            candidates.extend(objective_geometries)

        geometries = []
        seen = set()
        for candidate in candidates:
            clean_coordinates = self._line_coordinates_from_geometry_ref(candidate)
            if not clean_coordinates:
                continue
            key = tuple((round(point[0], 9), round(point[1], 9)) for point in clean_coordinates)
            if key in seen:
                continue
            seen.add(key)
            geometries.append(clean_coordinates)
        return geometries

    @staticmethod
    def _line_coordinates_from_geometry_ref(geometry_ref):
        geometry = geometry_ref.get("geometry") if isinstance(geometry_ref, dict) and isinstance(geometry_ref.get("geometry"), dict) else geometry_ref
        if not isinstance(geometry, dict):
            return None
        geometry_type = geometry.get("geometry_type") or geometry.get("type")
        coordinates = geometry.get("coordinates")
        if geometry_type != "LineString" or not isinstance(coordinates, list) or len(coordinates) < 2:
            return None

        clean_coordinates = []
        for point in coordinates:
            if isinstance(point, list) and len(point) >= 2:
                try:
                    clean_coordinates.append([float(point[0]), float(point[1])])
                except (TypeError, ValueError):
                    return None
        return clean_coordinates if len(clean_coordinates) >= 2 else None

    @staticmethod
    def _next_mission_node_id(graph):
        graph_nodes = [node for node in graph.nodes if isinstance(node, int)]
        return (min(graph_nodes) if graph_nodes else 0) - 1

    def _mission_line_graph(self, coordinates, index, next_node_id):
        line_graph = nx.MultiDiGraph()
        previous_node = None
        for coordinate in coordinates:
            node = next_node_id
            next_node_id -= 1
            line_graph.add_node(node, x=float(coordinate[0]), y=float(coordinate[1]))
            if previous_node is not None:
                line_graph.add_edge(
                    previous_node,
                    node,
                    road=True,
                    road_source="mission_line",
                    risk=False,
                    feature_id=f"mission-road-{index}",
                )
            previous_node = node
        if line_graph.number_of_edges() == 0:
            return None, next_node_id
        add_edge_lengths(line_graph)
        return line_graph, next_node_id

    @staticmethod
    def _connector_nodes_for_line_graph(line_graph):
        endpoint_nodes = [node for node in line_graph.nodes if line_graph.degree(node) <= 1]
        return set(endpoint_nodes or line_graph.nodes)

    @staticmethod
    def _connector_cell_size(max_distance_m):
        return max(float(max_distance_m) / 111_320.0, 1e-6)

    def _index_road_nodes(self, road_node_index, graph, nodes, cell_size):
        for node in nodes:
            data = graph.nodes[node]
            key = self._road_node_cell(data["y"], data["x"], cell_size)
            road_node_index.setdefault(key, set()).add(node)

    @staticmethod
    def _road_node_cell(lat, lon, cell_size):
        return (math.floor(float(lat) / cell_size), math.floor(float(lon) / cell_size))

    def _nearby_road_nodes(
        self,
        road_node_index,
        graph,
        lat,
        lon,
        cell_size,
        line_node_sources=None,
        exclude_line_source=None,
        exclude_nodes=None,
    ):
        line_node_sources = line_node_sources or {}
        exclude_nodes = exclude_nodes or set()
        latitude_window = self.mission_road_connect_max_distance / 111_320.0
        latitude_scale = max(0.2, abs(math.cos(math.radians(float(lat)))))
        longitude_window = self.mission_road_connect_max_distance / (111_320.0 * latitude_scale)
        cell_lat, cell_lon = self._road_node_cell(lat, lon, cell_size)
        cell_radius = max(1, math.ceil(max(latitude_window, longitude_window) / cell_size))

        candidates = []
        for lat_offset in range(-cell_radius, cell_radius + 1):
            for lon_offset in range(-cell_radius, cell_radius + 1):
                candidates.extend(road_node_index.get((cell_lat + lat_offset, cell_lon + lon_offset), ()))

        nearby = []
        seen = set()
        for graph_node in candidates:
            if graph_node in seen or graph_node in exclude_nodes:
                continue
            seen.add(graph_node)
            if exclude_line_source is not None and line_node_sources.get(graph_node) == exclude_line_source:
                continue
            graph_lat = graph.nodes[graph_node]["y"]
            graph_lon = graph.nodes[graph_node]["x"]
            if not self._within_distance_window(lat, lon, graph_lat, graph_lon, self.mission_road_connect_max_distance):
                continue
            distance_m = distance_between_coordinates(lat, lon, graph_lat, graph_lon)
            if distance_m <= self.mission_road_connect_max_distance:
                nearby.append((graph_node, distance_m))
        return sorted(nearby, key=lambda item: item[1])

    @staticmethod
    def _within_distance_window(lat1, lon1, lat2, lon2, max_distance_m):
        latitude_window = max_distance_m / 111_320.0
        latitude_scale = max(0.2, abs(math.cos(math.radians((lat1 + lat2) / 2.0))))
        longitude_window = max_distance_m / (111_320.0 * latitude_scale)
        return abs(lat1 - lat2) <= latitude_window and abs(lon1 - lon2) <= longitude_window

    def _node_has_road_edge(self, graph, node):
        neighbor_nodes = set(graph.neighbors(node))
        if hasattr(graph, "predecessors"):
            neighbor_nodes |= set(graph.predecessors(node))
        for neighbor in neighbor_nodes:
            edge = self._best_edge_data_in_graph(graph, node, neighbor)
            if edge is not None and edge.get("road") and not edge.get("risk"):
                return True
        return False

    def _best_edge_data_in_graph(self, graph, current_node, neighbor_node):
        if graph.has_edge(current_node, neighbor_node):
            edges = graph.get_edge_data(current_node, neighbor_node)
        elif graph.has_edge(neighbor_node, current_node):
            edges = graph.get_edge_data(neighbor_node, current_node)
        else:
            return None
        return min(edges.values(), key=lambda edge: edge.get("length", float("inf")))

    def _resolved_geometry_ref(self, geometry_ref, map_feature_collection):
        if not isinstance(geometry_ref, dict):
            return geometry_ref
        if isinstance(geometry_ref.get("geometry"), dict):
            return geometry_ref["geometry"]
        if geometry_ref.get("geometry_type") or geometry_ref.get("type"):
            return geometry_ref

        feature_id = str(geometry_ref.get("feature_id") or "")
        if not feature_id:
            return geometry_ref

        geometry = self.local_feature_geometries.get(feature_id)
        if geometry is None:
            fetched_features = self.read_features_from_db(
                feature_collection=map_feature_collection,
                feature_id=feature_id,
                crs="epsg:4326",
            )
            if fetched_features:
                geometry = fetched_features[0].geometry.iloc[0]

        if geometry is not None:
            return self._to_mission_geometry(geometry)
        print(f"Could not resolve mission road feature_id '{feature_id}' to geometry.", flush=True)
        return geometry_ref

    def _path_to_point(self, agent, destination, road_usage=0.5, log_failure=False):
        if not destination:
            return None
        destination = list(destination)
        a_star = AStar(self.graph, agent, [destination], road_usage=road_usage)
        result = a_star.search(log_failure=log_failure)
        if not result:
            return None
        route, _f_score = result
        route_graph = a_star.graph
        path = []
        for state in route:
            node = state.get_node()
            path.append([route_graph.nodes[node]['x'], route_graph.nodes[node]['y']])
        preserve_indices = {0}
        if path and self._points_differ(path[-1], destination):
            preserve_indices.add(len(path) - 1)
            path.append(destination)
        preserve_indices.add(len(path) - 1)
        return self._simplify_path(path, preserve_indices)

    @staticmethod
    def _points_differ(first, second, tolerance=1e-9):
        if not first or not second or len(first) < 2 or len(second) < 2:
            return True
        return abs(float(first[0]) - float(second[0])) > tolerance or abs(float(first[1]) - float(second[1])) > tolerance

    def _simplify_path(self, path, preserve_indices=None):
        if len(path) <= 2:
            return path
        preserve_indices = sorted(index for index in (preserve_indices or {0, len(path) - 1}) if 0 <= index < len(path))
        if not preserve_indices or preserve_indices[0] != 0:
            preserve_indices.insert(0, 0)
        if preserve_indices[-1] != len(path) - 1:
            preserve_indices.append(len(path) - 1)

        simplified = []
        for start_index, end_index in zip(preserve_indices, preserve_indices[1:]):
            segment = path[start_index : end_index + 1]
            simplified_segment = self._rdp_simplify(segment, self.path_simplification_tolerance_m)
            if simplified:
                simplified.extend(simplified_segment[1:])
            else:
                simplified.extend(simplified_segment)
        return self._dedupe_close_points(simplified)

    def _rdp_simplify(self, points, tolerance_m):
        if len(points) <= 2:
            return points

        start = points[0]
        end = points[-1]
        max_distance = -1.0
        split_index = 0
        for index, point in enumerate(points[1:-1], start=1):
            distance = self._point_to_segment_distance_m(point, start, end)
            if distance > max_distance:
                max_distance = distance
                split_index = index

        if max_distance <= tolerance_m:
            return [start, end]

        left = self._rdp_simplify(points[: split_index + 1], tolerance_m)
        right = self._rdp_simplify(points[split_index:], tolerance_m)
        return left[:-1] + right

    def _dedupe_close_points(self, points, tolerance_m=0.5):
        if len(points) <= 1:
            return points
        deduped = [points[0]]
        for point in points[1:]:
            if self._distance_between_points_m(deduped[-1], point) > tolerance_m:
                deduped.append(point)
        if self._points_differ(deduped[-1], points[-1]):
            deduped.append(points[-1])
        return deduped

    @classmethod
    def _point_to_segment_distance_m(cls, point, start, end):
        origin_lat = (float(point[1]) + float(start[1]) + float(end[1])) / 3.0
        p = cls._lonlat_to_local_meters(point, origin_lat)
        a = cls._lonlat_to_local_meters(start, origin_lat)
        b = cls._lonlat_to_local_meters(end, origin_lat)
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        projection = [a[0] + t * dx, a[1] + t * dy]
        return math.hypot(p[0] - projection[0], p[1] - projection[1])

    @staticmethod
    def _distance_between_points_m(first, second):
        return distance_between_coordinates(float(first[1]), float(first[0]), float(second[1]), float(second[0]))

    @staticmethod
    def _lonlat_to_local_meters(point, origin_lat):
        longitude_scale = max(0.2, abs(math.cos(math.radians(float(origin_lat)))))
        return [float(point[0]) * 111_320.0 * longitude_scale, float(point[1]) * 111_320.0]

    def _first_reachable_path(self, agent, candidate_points, road_usage=0.5, max_candidates=75):
        candidate_points = self._sort_points_by_agent_distance(agent, candidate_points)
        for point in candidate_points[:max_candidates]:
            path = self._path_to_point(agent, point, road_usage, log_failure=False)
            if path and len(path) > 1:
                print(
                    f"Selected reachable coverage point {point} for agent {agent.agent_id}.",
                    flush=True,
                )
                return path
        return None

    def _candidate_points_for_nodes(self, candidate_nodes):
        points = []
        for node in candidate_nodes:
            if self._node_has_non_risk_edge(node):
                points.append([self.graph.nodes[node]['x'], self.graph.nodes[node]['y']])
        return points

    def _node_has_non_risk_edge(self, node):
        neighbor_nodes = set(self.graph.neighbors(node))
        if hasattr(self.graph, "predecessors"):
            neighbor_nodes |= set(self.graph.predecessors(node))

        for neighbor in neighbor_nodes:
            edge = self._best_edge_data(node, neighbor)
            if edge is not None and not bool(edge.get("risk", False)):
                return True
        return False

    def _best_edge_data(self, current_node, neighbor_node):
        if self.graph.has_edge(current_node, neighbor_node):
            edges = self.graph.get_edge_data(current_node, neighbor_node)
        elif self.graph.has_edge(neighbor_node, current_node):
            edges = self.graph.get_edge_data(neighbor_node, current_node)
        else:
            return None
        return min(edges.values(), key=lambda edge: edge.get("length", float("inf")))

    @staticmethod
    def _sort_points_by_agent_distance(agent, points):
        agent_x = float(agent.localization[0])
        agent_y = float(agent.localization[1])
        unique_points = []
        seen = set()
        for point in points:
            if not point or len(point) < 2:
                continue
            normalized = (float(point[0]), float(point[1]))
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_points.append([normalized[0], normalized[1]])

        return sorted(
            unique_points,
            key=lambda point: ((agent_x - point[0]) ** 2) + ((agent_y - point[1]) ** 2),
        )

    def get_road_usage(self, mission_id):
        mission = self.missions.get(mission_id)
        if not mission:
            return 0.5
        transit = mission.get("transit") or {}
        if not isinstance(transit, dict):
            return 0.5
        optimization = transit.get("optimization") or transit.get("optimalization") or {}
        if not isinstance(optimization, dict):
            return 0.5
        value = optimization.get("road_usage")
        try:
            road_usage = float(value)
        except (TypeError, ValueError):
            return 0.5
        if road_usage > 1.0:
            road_usage = road_usage / 100.0
        return min(max(road_usage, 0.0), 1.0)

    @staticmethod
    def _to_mission_geometry(geometry):
        if isinstance(geometry, dict):
            geometry_type = geometry.get("geometry_type") or geometry.get("type")
            coordinates = geometry.get("coordinates")
        else:
            geometry_type = geometry.geom_type
            if geometry_type == "Polygon":
                coordinates = [list(geometry.exterior.coords)]
            elif geometry_type == "MultiPoint":
                coordinates = [[point.x, point.y] for point in geometry.geoms]
            elif geometry_type == "Point":
                coordinates = [geometry.x, geometry.y]
            else:
                coordinates = list(geometry.coords)

        coordinates = MultiRobotPathPlanning._listify_coordinates(coordinates)
        return {"coordinates": coordinates, "geometry_type": geometry_type}

    @staticmethod
    def _listify_coordinates(value):
        if isinstance(value, tuple):
            return [MultiRobotPathPlanning._listify_coordinates(item) for item in value]
        if isinstance(value, list):
            return [MultiRobotPathPlanning._listify_coordinates(item) for item in value]
        return value

    @staticmethod
    def _representative_point(geometry_type, coordinates):
        if geometry_type == "Polygon":
            coordinate_list = coordinates[0] if coordinates and isinstance(coordinates[0], list) else coordinates
        else:
            coordinate_list = coordinates

        points = [point for point in coordinate_list if isinstance(point, list) and len(point) >= 2]
        if not points:
            return [0.0, 0.0]
        lon = sum(float(point[0]) for point in points) / len(points)
        lat = sum(float(point[1]) for point in points) / len(points)
        return [lon, lat]



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
        if mission:
            return mission["transit"]["desired_vehicle_constraints"]["max_speed"]
        return None

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
