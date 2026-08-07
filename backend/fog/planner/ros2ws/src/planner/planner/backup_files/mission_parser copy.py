#!/usr/bin/env python3
# coding: utf-8


import json

class MissionParser:
    def __init__(self):
        self.missions = {}  # Store mission data by ID

    def update_mission(self, mission_id, mission_str):
        # Parse and store mission data by ID
        data = json.loads(mission_str)
        self.missions[mission_id] = {
            "data": data,
            "vehicle_ids": data['vehicles'],
            "mission_waypoints": data['objective']['geometry']['coordinates'],
            "max_speed": data['transit']['desired_vehicle_constraints']['max_speed'],
        }

    def get_mission_destinations(self, mission_id):
        # Return mission waypoints for the given ID
        mission = self.missions.get(mission_id)
        if mission:
            return mission['mission_waypoints']
        return None  # Or raise an exception if preferred

    def get_mission_agents(self, mission_id):
        # Return vehicle IDs for the given mission ID
        mission = self.missions.get(mission_id)
        if mission:
            return mission['vehicle_ids']
        return None  # Or raise an exception if preferred

    def get_max_speed(self, mission_id):
        # Return max speed for the given mission ID
        mission = self.missions.get(mission_id)
        if mission:
            return mission['max_speed']
        return None  # Or raise an exception if preferred


    def set_output_file(self,filename):
        self.output_file= filename

    def update(self,mission):
        self.data= json.loads(mission)
        self.vehicle_ids= self.data['vehicles']
        self.mission_waypoints = self.data['objective']['geometry']['coordinates']
        self.max_speed= self.data['transit']['desired_vehicle_constraints']['max_speed']


    


    def path_to_plan_json(self,paths, mission_id):
        tasks = []
        for agent_id , path in paths.items():
            waypoint_list = []

            for waypoint in path:
                waypoint_list.append({"position":waypoint,
                                    "speed":self.get_max_speed(mission_id)})
            tasks.append({
                        "agent_id": agent_id,
                        "std":"",
                        "waypoints":waypoint_list})
            
        mission={"tasks":tasks}
        to_json= json.dumps(mission)
        
        return to_json


