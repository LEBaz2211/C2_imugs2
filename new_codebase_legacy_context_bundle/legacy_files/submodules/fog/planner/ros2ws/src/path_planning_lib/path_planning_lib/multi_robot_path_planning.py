import json
from shapely.geometry import shape
import geopandas as gpd

from .models import *
from .mapf import *
from .task_allocation import *
from .max_coverage import *

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
                    coordinates = list(geometry.coords) if geometry_type != "Polygon" else [list(geometry.exterior.coords)]
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
            if points and not polygons_or_lines:
                point_coordinates = [coord for _, coords in points for coord in coords]
                allocations= coverage_algorithm("Point", point_coordinates, len(vehicles), return_paths=True)
            else:
                allocations = coverage_algorithm("Mixed", polygons_or_lines, len(vehicles), return_paths=True)
    
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
            a_star = AStar(self.graph, agent, destination)
            route, f_score = a_star.search()
            
            # Extract the path from the route and convert it to coordinates
            path = []
            for state in route:
                node = state.get_node()
                path.append([self.graph.nodes[node]['x'], self.graph.nodes[node]['y']])
            
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
                a_star = AStar(self.graph, agent, destination)
                route, f_score = a_star.search()

                # Extract the path from the route and convert it to coordinates
                path = []
                for state in route:
                    node = state.get_node()
                    path.append([self.graph.nodes[node]['x'], self.graph.nodes[node]['y']])

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
