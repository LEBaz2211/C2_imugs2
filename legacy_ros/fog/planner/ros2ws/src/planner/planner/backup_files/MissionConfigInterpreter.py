import json
from typing import List, Dict, Any
from shapely.geometry import Point, MultiPoint, Polygon, LineString
from shapely.ops import unary_union
from pymongo import MongoClient
from shapely.geometry import shape
import geopandas as gpd
from path_planning_lib.utils import read_features_from_db

# The behavior can be 0, 1, 2, ... where 0 is a navigate to geometries, 1 is explore geometries, ... Here are some examples:
# 1. For navigating to geometries (behavior 0):
  # a. if the maximize_coverage is true, it needs to first compute points (as many as there are vehicles)  to maximize the coverage on the geometries. 
      # if points or multipoints are part of the given geometries, these points become goals themselves. 
      # For polygons and linestrings, it's a maximum coverage problem to solve for the remaining vehicles. 
      # If there are more geometries than vehicles, run the random geometry selection to choose which ones to cover. 
      # Once goals are found, run the optimal allocation algorithm. once a goal is found for every vehicle, plan paths based on these goals. 

  # b. if maximize_coverage is false, it needs to first compute a point for each vehicle to reach the geometries. 
      # if points or multipoints are part of the given geometries, they become goals themselves. 
      # If there are more geometries than vehicles, run the random geometry selection to choose which ones to cover. 
      # If there are more vehicles than geometries, just make sure all geometries are assigned to a vehicle. 
      # Allocating the geometries to the agents is done by optimal allocation. 
      # once a goal is found for every vehicle, plan paths based on these goals. 

# 2. For exploring geometries (behavior 1):
# a. if maximize_coverage is true, it means all geometries need to be maximally covered. If there are more geometries than vehicles, some vehicles should cover multiple geometries sequentially. The allocation is done optimally by selecting the closest geometries for each agent. Then, paths are planned for each agent, simply navigating to points for Point or Multipoint geometries,  while for polygons or linestrings it should first go to the geometry, then cover the full polygon with mowing patterns or just following the linestring.  Once these paths are calculated, if there are remaining geometries, the agents with lowest number of waypoints have to do the same for the remaining geometries, which is added to their list waypoints.

# b.  if maximize_coverage is false, do the same as in a but for linestrings and polygons it should just reach the geometry, not survey the full geometry. 



class MissionConfig:
    def __init__(self, mission_config: Dict[str, Any], mongodb_url: str, db: str, collection: str):
        self.mission_config = mission_config
        self.mongodb_url = mongodb_url
        self.db = db
        self.collection = collection
        self._load_geometries()

    def _load_geometries(self):
        """
        Augments explicit geometries in the objective by fetching from the database for missing feature_ids.
        """
        objective = self.mission_config["objective"]
        feature_ids = objective.get("feature_ids", [])
        feature_geometries = []

        # Fetch geometries from the database based on feature_id
        for feature_id in feature_ids:
            db_features = read_features_from_db(
                feature_id=feature_id,
                mongodb_url=self.mongodb_url,
                db=self.db,
                feature_collection=self.collection
            )
            feature_geometries.extend([gdf.geometry.iloc[0] for gdf in db_features])

        # Combine explicit geometries and fetched ones
        explicit_geometries = objective.get("geometries", [])
        for geom in explicit_geometries:
            coords = geom["coordinates"]
            geom_type = geom["geometry_type"]
            if geom_type == "Point":
                feature_geometries.append(Point(coords))
            elif geom_type == "MultiPoint":
                feature_geometries.append(MultiPoint(coords))
            elif geom_type == "Polygon":
                feature_geometries.append(Polygon(coords))
            elif geom_type == "LineString":
                feature_geometries.append(LineString(coords))

        self.geometries = feature_geometries

    def update(self, new_config: str):
        """
        Reloads the mission configuration from a JSON string and updates the geometries.
        """
        self.mission_config = json.loads(new_config)
        self._load_geometries()

    def get_geometries(self):
        """
        Returns all geometries in a Shapely-compatible format.
        """
        return self.geometries

class MissionInterpreter:
    def __init__(self, mission_config: MissionConfig):
        self.mission_config = mission_config

    def interpret(self):
        """
        Determines the mission objectives and outputs the corresponding actions.
        """
        behavior = self.mission_config.mission_config["behavior"]
        geometries = self.mission_config.get_geometries()
        maximize_coverage = self.mission_config.mission_config["objective"].get("maximize_coverage", False)
        vehicles = self.mission_config.mission_config["vehicles"]

        print(f"Interpreting mission with behavior {behavior}, vehicles {vehicles}")
        if all(isinstance(geom, Point) or isinstance(geom, MultiPoint) for geom in geometries) and behavior == 0:
            print("Objective: Navigate to all points.")
            for point in geometries:
                print(f"Plan a path to Point at {point}.")
            print("Allocate vehicles to tasks.")
        elif any(isinstance(geom, Polygon) for geom in geometries) and maximize_coverage:
            print("Objective: Maximize coverage of areas.")
            for polygon in geometries:
                print(f"Plan coverage paths for Polygon at {polygon.bounds}.")
        elif any(isinstance(geom, LineString) for geom in geometries) and behavior == 0:
            print("Objective: Reach all LineStrings.")
            for line in geometries:
                print(f"Plan path to LineString starting at {line.coords[0]}.")
        else:
            print("Unknown or unsupported mission objective.")

# Example Usage
mongodb_url = "mongodb://localhost:27017"
db = "MapDB"
collection = "features"

mission_config_json = """
{
  "mission_id": "671eae59-f010-40a6-90f3-02938d052049",
  "__v": 0,
  "behavior": 0,
  "name": "Delivery",
  "vehicles": [
    "4dd12623-3fb6-4ae4-91c2-1f4b10d2327d",
    "2b4a887b-95af-451d-bd85-e0dcacb72524",
    "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
  ],
  "objective": {
    "feature_ids": [
      "aa31e4d4-d8fd-4d99-bdaa-68577f7e0142",
      "a410ea41-1450-482d-ac34-477e3b4b7352"
    ],
    "geometries": [
      {
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
    ],
    "maximize_coverage": false,
    "arrival_time": {
      "earliest": "2024-11-22T11:02:54Z",
      "latest": "2024-11-22T11:02:54Z",
      "target": "2024-11-22T11:02:54Z"
    }
  },
  "transit": {
    "desired_vehicle_constraints": {
      "max_speed": 3
    },
    "optimization": {
      "energy": 100,
      "road_usage": 50
    }
  }
}
"""
mission_config = MissionConfig(json.loads(mission_config_json), mongodb_url, db, collection)
interpreter = MissionInterpreter(mission_config)
interpreter.interpret()
