import json
import math
from shapely.geometry import shape
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

    def set_graph(self, graph, projected_graph=None):
        """Install one immutable scenario graph and its read-only snap index."""
        self.graph = graph
        self.edge_snap_index = EdgeSnapIndex(graph, projected_graph=projected_graph)

    def update_mission(self, mission_id, mission_str, map_feature_collection):
        """
        Parse and store mission data by ID.
        :param mission_id: Unique mission identifier.
        :param mission_str: JSON string containing mission configuration.
        """
        data = json.loads(mission_str)

        # Get geometries from database
        for geometry_obj in data["objective"]["geometries"]:
            if "feature_id" in geometry_obj:
                feature_id = geometry_obj["feature_id"]
                fetched_features = self.read_features_from_db(
                    feature_collection = map_feature_collection, 
                    feature_id=feature_id, 
                    crs="epsg:4326"
                )
                if fetched_features:
                    geometry = fetched_features[0].geometry.iloc[0]
                    geometry_type = geometry.geom_type
                    if geometry_type == "Polygon":
                        coordinates = [list(geometry.exterior.coords)]
                        coordinates.extend(list(ring.coords) for ring in geometry.interiors)
                    else:
                        coordinates = list(geometry.coords)
                    geometry_obj["geometry"] = {"coordinates": coordinates, "geometry_type": geometry_type}

        self.missions[mission_id] = data

    def solve_mission(self, mission_id, agents_to_plan):
        # Check mission exists
        if mission_id not in self.missions:
            raise ValueError(f"Mission ID {mission_id} not found.")

        mission = self.missions[mission_id]
        behavior = mission["behavior"]
        vehicles = mission["vehicles"]
        geometries = mission["objective"]["geometries"]

        print("mission:")
        print(mission)
        print("geometries:")
        print(geometries)

        # Split geometries by type
        points = []
        polygons_or_lines = []
        for geometry_obj in geometries:
            geometry_type = geometry_obj["geometry"]["geometry_type"]
            coordinates = geometry_obj["geometry"]["coordinates"]

            if geometry_type == "Point":
                points.append(coordinates[0])
            elif geometry_type =="MultiPoint": # Convert multipoints to individual points
                points.extend(point_coordinates for point_coordinates in coordinates)  # Convert each to "Point"
            elif geometry_type in ["Polygon", "LineString"]:
                polygons_or_lines.append((geometry_type, coordinates))
            else:
                raise ValueError(f"Unsupported geometry type: {geometry_type}")

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
            return self._solve_polygon_coverage(
                mission,
                agents_to_plan,
                points,
                polygons_or_lines,
            )
    
        else:
            raise ValueError(f"Unsupported behavior: {behavior}")

        # return path_planning_algorithm(allocations, vehicles)

        
        # assume one waypoint per agent, for now just randomly allocated
        # destination_points= self.mission_parser.get_mission_destinations(self.current_mission_id) 
        # self.allocate_destinations_to_agents(agents_to_plan, destination_points, "random")



        new_paths = dict()

        # Single Agent
        if len(allocations) == 1:
            print("Only one agent detected --> SINGLE AGENT")
            
            # Get the agent and the destination assigned to this agent
            agent_id, destination = list(allocations.items())[0]  # Get the first (and only) agent-destination pair
            # agent = agents_to_plan[agent_id]  # Retrieve the agent object by agent_id
            agent = next(agent for agent in agents_to_plan if agent.agent_id == agent_id)

            
            # Perform A* pathfinding from the agent's current position to the destination
            route, route_graph = self._search_route(agent, destination)
            
            path = self._navigation_path_from_route(
                route,
                route_graph,
                agent.localization,
                destination,
            )
            
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
                route, route_graph = self._search_route(agent, destination)

                path = self._navigation_path_from_route(
                    route,
                    route_graph,
                    agent.localization,
                    destination,
                )

                # Store the computed path for the agent
                new_paths[agent_id] = path
                i += 1

        elif (self.mapf == "cbs"): # Conflict Based Search
            # assume one waypoint per agent, for now allocated by order
            cbs = CBS(self.graph)
            plan = cbs.search(agents_to_plan, allocations)
            for agent_id, route in plan.items():
                agent = next(agent for agent in agents_to_plan if agent.agent_id == agent_id)
                path = self._navigation_path_from_route(
                    route,
                    self.graph,
                    agent.localization,
                    allocations[agent_id],
                )
                new_paths[agent_id] = path
        return new_paths

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

    def _solve_polygon_coverage(self, mission, agents_to_plan, points, polygons_or_lines):
        """Plan complete lawnmower coverage for one Polygon objective."""
        if points:
            raise ValueError("Coverage behavior requires a Polygon objective, not Point geometry")
        if len(polygons_or_lines) != 1 or polygons_or_lines[0][0] != "Polygon":
            raise ValueError("Coverage behavior currently requires exactly one Polygon objective")
        if mission["objective"].get("maximize_coverage") is False:
            raise ValueError("Polygon coverage requires objective.maximize_coverage=true")

        widths_by_vehicle = self._coverage_widths_by_vehicle(mission)
        active_widths = [widths_by_vehicle[agent.agent_id] for agent in agents_to_plan]
        # When robots have different swaths, using the narrowest swath for the
        # shared pattern guarantees that the collective set of lanes has no
        # wider gaps than any selected robot can cover.
        swath_width = min(active_widths)
        _, coordinates = polygons_or_lines[0]
        coverage_path = lawnmower_coverage_path(
            coordinates,
            swath_width,
            risk_polygons=self.risk_polygons,
        )
        chunks = self._split_continuous_path(coverage_path, len(agents_to_plan))

        mission_vehicle_order = {
            vehicle_id: index for index, vehicle_id in enumerate(mission["vehicles"])
        }
        ordered_agents = sorted(
            agents_to_plan,
            key=lambda agent: mission_vehicle_order.get(agent.agent_id, len(mission_vehicle_order)),
        )

        paths = {}
        for agent, chunk in zip(ordered_agents, chunks):
            paths[agent.agent_id] = self._route_agent_to_coverage_chunk(agent, chunk)

        print(
            f"Generated Polygon lawnmower coverage with {len(coverage_path)} sweep waypoints, "
            f"{swath_width:.2f} m lane width, {len(self.risk_polygons)} risk exclusion(s), "
            f"and {len(paths)} agent path(s)",
            flush=True,
        )
        return paths

    @staticmethod
    def _coverage_widths_by_vehicle(mission):
        objective = mission["objective"]
        raw_widths = None
        for field_name in (
            "maximum_coverage_distances",
            "maximize_coverage_distances",
            "MaximizeCoverageDistances",
        ):
            if field_name in objective:
                raw_widths = objective[field_name]
                break

        if not isinstance(raw_widths, list) or not raw_widths:
            raise ValueError(
                "Polygon coverage requires objective.maximum_coverage_distances=[swath_width_m]"
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
        segment_count = len(path) - 1
        if segment_count <= 0:
            return [path[:] for _ in range(chunk_count)]

        chunks = []
        for index in range(chunk_count):
            start = round(index * segment_count / chunk_count)
            end = round((index + 1) * segment_count / chunk_count)
            chunks.append(path[start : end + 1])
        return chunks

    def _route_agent_to_coverage_chunk(self, agent, chunk):
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
                route, route_graph = self._search_route(agent, entry)
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

    def _search_route(self, agent, destination):
        """Run A* between query-local virtual nodes on the scenario graph."""
        if destination and isinstance(destination[0], (list, tuple)):
            destination = destination[0]
        if self.edge_snap_index is None:
            self.edge_snap_index = EdgeSnapIndex(self.graph)
        start_snap = self.edge_snap_index.snap(agent.localization, self.risk_polygons)
        destination_snap = self.edge_snap_index.snap(destination, self.risk_polygons)
        route_graph, resolved = add_virtual_endpoint_nodes(
            self.graph,
            [start_snap, destination_snap],
        )
        result = AStar(
            route_graph,
            agent,
            [destination],
            risk_polygons=self.risk_polygons,
            start_node=resolved[0]["node"],
            destination_node=resolved[1]["node"],
        ).search()
        if not result:
            raise RuntimeError(
                f"No route found for agent {agent.agent_id} "
                f"from {agent.localization} to {destination}"
            )

        route, _f_score = result
        if not route:
            raise RuntimeError(
                f"No route found for agent {agent.agent_id} "
                f"from {agent.localization} to {destination}"
            )
        return route, route_graph



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
