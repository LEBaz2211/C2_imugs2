import json
from pymongo import MongoClient
from shapely.geometry import shape
import geopandas as gpd

# from path_planning_lib.utils import read_features_from_db


class MissionInterpreter:
    def __init__(self, optimal_allocation_algorithm, optimal_coverage_algorithm, mongodb_url, db):
        """
        Initialize the MissionInterpreter with algorithms for allocation and coverage and database parameters.
        :param optimal_allocation_algorithm: Function for optimal allocation of points to robots.
        :param optimal_coverage_algorithm: Function for determining optimal coverage points for polygons/linestrings.
        :param mongodb_url: URL of the MongoDB database.
        :param db: Name of the database.
        :param collection: Name of the collection containing features.
        """
        self.missions = {}  # Store mission data by ID
        self.optimal_allocation = optimal_allocation_algorithm
        self.optimal_coverage = optimal_coverage_algorithm
        self.mongodb_url = mongodb_url
        self.db = db

    def update_mission(self, mission_id, mission_str, feature_collection):
        """
        Parse and store mission data by ID.
        :param mission_id: Unique mission identifier.
        :param mission_str: JSON string containing mission configuration.
        """
        data = json.loads(mission_str)

        # Process geometries with feature IDs
        for geometry_obj in data["objective"]["geometries"]:
            if "feature_id" in geometry_obj:
                feature_id = geometry_obj["feature_id"]
                fetched_features = self.read_features_from_db(feature_collection = feature_collection, feature_id=feature_id, crs="epsg:4326")

                if fetched_features:
                    geometry = fetched_features[0].geometry.iloc[0]
                    geometry_type = geometry.geom_type
                    coordinates = list(geometry.coords) if geometry_type != "Polygon" else [list(geometry.exterior.coords)]
                    geometry_obj["geometry"] = {"coordinates": coordinates, "geometry_type": geometry_type}

        self.missions[mission_id] = data

    def interpret_mission(self, mission_id):
        """
        Interpret a mission and allocate points or paths to robots based on the mission configuration.
        :param mission_id: Unique mission identifier.
        :return: Dictionary containing robot allocations or paths.
        """
        if mission_id not in self.missions:
            raise ValueError(f"Mission ID {mission_id} not found.")

        mission = self.missions[mission_id]
        behavior = mission["behavior"]
        vehicles = mission["vehicles"]
        geometries = mission["objective"]["geometries"]

        # Split geometries by type
        points = []
        polygons_or_lines = []
        for geometry_obj in geometries:
            geometry_type = geometry_obj["geometry"]["geometry_type"]
            coordinates = geometry_obj["geometry"]["coordinates"]

            if geometry_type in ["Point", "MultiPoint"]:
                points.append((geometry_type, coordinates))
            elif geometry_type in ["Polygon", "LineString"]:
                polygons_or_lines.append((geometry_type, coordinates))
            else:
                raise ValueError(f"Unsupported geometry type: {geometry_type}")

        if behavior == 0:  # "go to" behavior
            allocations = {}
            if points:
                point_coordinates = [coord for _, coords in points for coord in coords]
                allocations.update(self.optimal_allocation(vehicles, point_coordinates))

            if polygons_or_lines:
                remaining_vehicles = list(set(vehicles) - set(allocations.keys()))
                for geometry_type, coords in polygons_or_lines:
                    coverage_points = self.optimal_coverage(geometry_type, coords, len(remaining_vehicles))
                    allocations.update(self.optimal_allocation(remaining_vehicles, coverage_points))

            return allocations

        elif behavior == 1:  # "explore" behavior
            if points and not polygons_or_lines:
                point_coordinates = [coord for _, coords in points for coord in coords]
                return self.optimal_allocation(vehicles, point_coordinates)

            return self.optimal_coverage("Mixed", geometries, len(vehicles), return_paths=True)
        else:
            raise ValueError(f"Unsupported behavior: {behavior}")

    @staticmethod
    def read_features_from_db(
        mongodb_url, db, collection, 
        feature_id=None, geometry_type=None, feature_type=None, crs="epsg:4326"
    ):
        """
        Fetch features from the database based on optional filtering criteria: feature_id, geometry_type, feature_type.

        Args:
            mongodb_url (str): URL to the MongoDB instance.
            db (str): Name of the database.
            collection (str): Name of the collection.
            feature_id (str, optional): Specific feature ID to filter.
            geometry_type (str, optional): Specific geometry type (e.g., 'Point', 'Polygon').
            feature_type (str, optional): Specific feature type to filter.
            crs (str): Coordinate reference system for returned geometries (default: 'epsg:32633').

        Returns:
            List[gpd.GeoDataFrame]: List of GeoDataFrames containing matching features.
        """
        # print(f"Searching for features with criteria: feature_id={feature_id}, geometry_type={geometry_type}, feature_type={feature_type}")

        client = MongoClient(mongodb_url)
        database = client[db]
        feature_collection = database[collection]

        # Build the query dynamically based on provided arguments
        query = {}
        if feature_id:
            query["properties.feature_id"] = feature_id
        if geometry_type:
            query["geometry.type"] = geometry_type
        if feature_type:
            query["properties.feature_type"] = feature_type

        cursor = feature_collection.find(query)

        features = []
        for document in cursor:
            try:
                # Convert GeoJSON geometry to Shapely geometry
                geom = shape(document["geometry"])

                # Verify geometry type and structure
                if geom.is_empty:
                    print(f"Warning: Empty geometry found in document with ID: {document.get('_id')}")
                    continue

                # Create a GeoDataFrame with geometry and properties
                gdf = gpd.GeoDataFrame(
                    [document["properties"]],
                    geometry=[geom],
                    crs=crs
                )
                features.append(gdf)

            except Exception as e:
                print(f"Error processing document: {document}")
                print(e)

        print("Features found:")
        for gdf in features:
            print(gdf)

        return features

    def get_mission_destinations(self, mission_id):
        """
        Return mission waypoints (objective geometries) for the given mission ID.
        :param mission_id: Unique mission identifier.
        :return: List of geometries or None if the mission is not found.
        """
        mission = self.missions.get(mission_id)
        if mission:
            return mission["objective"]["geometries"]
        return None

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


# Mock algorithms for testing
def mock_optimal_allocation(vehicles, points):
    # Naive allocation algorithm (round-robin assignment for simplicity)
    allocation = {}
    for i, vehicle in enumerate(vehicles):
        allocation[vehicle] = points[i % len(points)]
    return allocation

def mock_optimal_coverage(geometry_type, coordinates, num_robots, return_paths=False):
    # Naive coverage algorithm: evenly split coordinates into num_robots groups
    if geometry_type in ["Polygon", "LineString", "Mixed"]:
        if return_paths:
            return {f"robot_{i}": coordinates[i::num_robots] for i in range(num_robots)}
        else:
            return coordinates[:num_robots]
    return []

# Example usage
if __name__ == "__main__":
    mission_str = '''
    {
      "objective": {
        "geometries": [
            {
                "feature_id": "f31403c6-5537-4adb-a870-ee531afda7cc"
            },
            {
                "geometry": {
                    "coordinates": [
                        [4.391893297982506, 50.844115083630555],
                        [4.391710170382453, 50.84427476662046],
                        [4.392039364043569, 50.844318817004506]
                    ],
                    "geometry_type": "MultiPoint"
                }
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
      "behavior": 0,
      "name": "Delivery",
      "vehicles": [
        "4dd12623-3fb6-4ae4-91c2-1f4b10d2327d",
        "2b4a887b-95af-451d-bd85-e0dcacb72524",
        "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
        "8ef41dae-86d0-41f5-a65d-d8cc5bab1cf6"
      ]
    }
    '''
    mongodb_url = "mongodb://localhost:27017/"
    db = "MapDB"
    interpreter = MissionInterpreter(mock_optimal_allocation, mock_optimal_coverage, mongodb_url, db)
    interpreter.update_mission("671eae59-f010-40a6-90f3-02938d052049", mission_str)
    allocations = interpreter.interpret_mission("671eae59-f010-40a6-90f3-02938d052049")
    print("Allocations:", allocations)
