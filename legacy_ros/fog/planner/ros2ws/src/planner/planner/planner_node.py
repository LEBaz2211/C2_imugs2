import rclpy
import json
import uuid

import os
import threading

import matplotlib.pyplot as plt
from cv_bridge import CvBridge
import cv2
import glob

from datetime import date, datetime
import random

import pymongo
from pymongo import MongoClient, ReadPreference
import osmnx as ox
from shapely.ops import unary_union
import geopandas as gpd

from rclpy.node import Node

from path_planning_lib.utils import *
from path_planning_lib.graph import *
from path_planning_lib.mapf import *
from path_planning_lib.models import *

from path_planning_lib.multi_robot_path_planning import *


from std_msgs.msg import String
from geographic_msgs.msg import GeoPose
from geometry_msgs.msg import Twist


from sensor_msgs.msg import NavSatFix
from sensor_msgs.msg import CompressedImage
# from .mission_parser import MissionParser

# Custom messages
from centralized_msgs.srv import (CreatePlanner,
                                    GetPlan,
                                    DeletePlanner)
from centralized_msgs.msg import Agent


class PlannerNode(Node):
    def __init__(self):
        super().__init__('planner_node')

        # ROS parameters
        self.declare_parameters(namespace='',
                                parameters=[
                                    ('map_radius',rclpy.Parameter.Type.DOUBLE),
                                    ('epsg',rclpy.Parameter.Type.STRING),
                                    ('mapf',rclpy.Parameter.Type.STRING),
                                    ("initial_position",rclpy.Parameter.Type.DOUBLE_ARRAY),
                                    ('poly_graph_connect_max_distance',rclpy.Parameter.Type.DOUBLE),
                                    ('line_graph_connect_max_distance',rclpy.Parameter.Type.DOUBLE),
                                    ('merge_nodes',rclpy.Parameter.Type.BOOL),
                                    ('merge_nodes_max_distance',rclpy.Parameter.Type.DOUBLE),
                                    ('populate_graph',rclpy.Parameter.Type.BOOL),
                                    ('populate_min_distance',rclpy.Parameter.Type.DOUBLE),
                                    ('points_in_polygon_dist',rclpy.Parameter.Type.DOUBLE),
                                    ('map_folder',rclpy.Parameter.Type.STRING),
                                    ('mongodb_url',rclpy.Parameter.Type.STRING),
                                    ('map_feature_collection',rclpy.Parameter.Type.STRING),
                                    ('load_map_from_database',rclpy.Parameter.Type.BOOL),
                                    ('load_map_from_local_folder',rclpy.Parameter.Type.BOOL),

                                ])
        # Load ROS parameters
        self.epsg= self.get_parameter("epsg").value
        self.mapf= self.get_parameter("mapf").value
        self.map_radius= self.get_parameter("map_radius").value
        self.poly_G_max_distance = self.get_parameter("poly_graph_connect_max_distance").value
        self.line_G_max_distance = self.get_parameter("line_graph_connect_max_distance").value
        self.merge_nodes= self.get_parameter("merge_nodes").value
        self.merge_nodes_max_distance= self.get_parameter("merge_nodes_max_distance").value
        self.populate_graph= self.get_parameter("populate_graph").value
        self.populate_min_distance= self.get_parameter("populate_min_distance").value
        self.points_in_polygon_dist= self.get_parameter("points_in_polygon_dist").value
        point=self.get_parameter("initial_position").value

        

        self.map_folder = self.get_parameter("map_folder").value
        self.mongodb_url = self.get_parameter("mongodb_url").value
        self.load_map_from_database= self.get_parameter("load_map_from_database").value
        self.load_map_from_local_folder= self.get_parameter("load_map_from_local_folder").value

        self.mongo_client = MongoClient(self.mongodb_url, read_preference=ReadPreference.PRIMARY)  # Set read preference
        self.map_database = self.mongo_client["MapDB"]
        map_feature_collection = self.get_parameter("map_feature_collection").value
        self.map_feature_collection = self.map_database[map_feature_collection]
        self.mongodb_features_count = 0
        # Start a MongoDB watcher in a separate thread
        # self.watch_thread = threading.Thread(target=self.watch_db_changes(2), daemon=True)
        # self.watch_thread.start()

        self.plans = {}  # Dictionary to store plans with ID as the key
        self.current_mission_id = ""
        self.planner_states = dict()

        self.agents = dict()

        self.path = []
        self.paths = dict()
        self.paths_mutex = threading.Lock()
        self.path_image_saved = False

        self.G = None
        self.G_projected= None
        self.obstacle_gdf= None
        self.init= False


        self.initialize_map()
        

        

        self.mission_defined = False

        # Create timers
        self.state_timer = self.create_timer(1, self.state_timer_callback)
        self.planning_timer = self.create_timer(1,self.planning_timer_callback)
        
        # Create the publishers
        self.state_publisher = self.create_publisher(String, '/multi_robot/planner/state', 10)

        # Create subscribers
        self.agent_subscription = self.create_subscription(
            Agent,
            '/multi_robot/planner/agent',
            self.agent_subscriber_callback,
            10)
        # self.subscription  # prevent unused variable warning



        # Create the services
        self.set_mission_service = self.create_service(
            CreatePlanner, '/multi_robot/planner/create', self.set_mission_service_callback
        )
        self.get_plan_service = self.create_service(
            GetPlan, '/multi_robot/planner/get_plan', self.get_plan_service_callback
        )
        self.delete_planner_service = self.create_service(
            DeletePlanner, '/multi_robot/planner/delete_planner', self.delete_planner_service_callback
        )


        # ROS2 Publisher for the graph image
        self.image_publisher = self.create_publisher(CompressedImage, '/multi_robot/planner/graph_image', 10)
        self.timer = self.create_timer(3.0, self.graph_timer_callback)

        # CV Bridge for converting OpenCV images to ROS2 CompressedImage messages
        self.bridge = CvBridge()
    
    # Watch for changes in map database
    def watch_db_changes(self):
        """ Polls the MongoDB collection for changes. """
        try:
            current_count = self.map_feature_collection.count_documents({})  # Get the current count
            if current_count != self.mongodb_features_count:
                self.get_logger().info("Detected change in database (polling).")
                self.initialize_map() # Or process the actual changes if you can get them
                self.mongodb_features_count = current_count  # Update the previous state
        except pymongo.errors.ConnectionFailure as e:
            self.get_logger().error(f"MongoDB connection error: {e}")
        except Exception as e:
            self.get_logger().error(f"Polling error: {e}")

    
    # def watch_db_changes(self):
    #     """ Watches the MongoDB 'features' collection for changes. """
    #     try:
    #         with self.map_feature_collection.watch() as stream:
    #             for change in stream:
    #                 self.handle_db_change(change)
    #     except Exception as e:
    #         self.get_logger().error(f"MongoDB watch error: {e}")

    def handle_db_change(self, change):
        """ Handles detected changes in the MongoDB collection. """
        self.get_logger().info(f"Detected change in database: {change}")
        self.initialize_map()

    # ROS callbacks

    def agent_subscriber_callback(self, msg):
        if (not msg.agent_id in self.agents.keys()):
            self.get_logger().info('Adding new agent: "%s"' % msg.agent_id)
            
            # new_agent = Agent(msg.agent_id)
            # self.agents[msg.agent_id] = new_agent
        
        agent = Buddy(msg.agent_id, localization = [msg.odometry.pose.pose.position.x, msg.odometry.pose.pose.position.y], current_speed = msg.odometry.twist.twist.linear.x)
        self.agents.update({msg.agent_id : agent})
        # agent_pose = msg.pose
        # self.get_logger().info('Localisation received for agent: "%s"' % msg.agent_id)


    def state_timer_callback(self):
        msg = String()
        msg.data = json.dumps({
            "planners": [
                {
                    "mission_id": mission_id,
                    "state": state
                }
                for mission_id, state in self.planner_states.items()
            ]
        })
        self.state_publisher.publish(msg)

    def planning_timer_callback(self):
        if (self.mission_defined):

            self.planner_states.update({self.current_mission_id: 1})  # Planning state


            self.paths_mutex.acquire()
            
            # consider agents that are detected and included in the mission
            agents_to_plan = [agent for agent in self.agents.values() if agent.agent_id in self.mr_path_planner.get_mission_agents(self.current_mission_id)]
            self.get_logger().info(
                f'Planning mission "{self.current_mission_id}" for {len(agents_to_plan)} detected agent(s)'
            )
            if not agents_to_plan:
                self.get_logger().warn("Mission is defined, but no matching agents have reported to the planner yet.")
                self.paths_mutex.release()
                return
            
            # Set max speed of mission as nominal speed for now
            self.set_agents_nominal_speeds(agents_to_plan, self.mr_path_planner.get_max_speed(self.current_mission_id), "max_speed")

            # Compute Multi Robot Paths
            new_paths = self.mr_path_planner.solve_mission(self.current_mission_id, agents_to_plan)

            self.planner_states.update({self.current_mission_id: 2})  # Planned state

            waypoint_count = sum(len(path) for path in new_paths.values())
            self.get_logger().info(
                f'Planner produced {len(new_paths)} path(s) with {waypoint_count} waypoint(s)'
            )
            
            self.paths = new_paths
            self.paths_mutex.release()

            # Plot the result
            if (not self.path_image_saved):
                self.plot_graph_service(paths=self.paths)

            self.mission_defined = False
            self.get_logger().info(
                f'Planning completed for mission "{self.current_mission_id}". Cached plan is ready for execution.'
            )
                

    def set_mission_service_callback(self, request, response):
        # Process the CreatePlanner service request here
        self.get_logger().info('Received CreatePlanner request')

        mission_id = request.id
        mission_config = request.config

        try:
            # Parse and store the mission using ID as the key
            self.mr_path_planner.update_mission(mission_id, mission_config, self.map_feature_collection)

            self.planner_states.update({mission_id: 0})  # initialized state


            # Store the corresponding plan (placeholder logic)
            self.plans[mission_id] = json.dumps({"plan": None}) 

            self.mission_defined = True
            self.path_image_saved = False


            response.id = mission_id
            response.state = 1  # Assuming successful creation

            self.current_mission_id = mission_id
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Failed to parse mission config: {e}")
            response.state = 0  # Indicate failure

        return response



    def path_to_plan_json(self, paths):
        tasks = {}

        for agent_id, path in paths.items():
            task_id = str(uuid.uuid4())  # Unique task ID for each agent
            primitives = []
            objectives = []

            primitive_id = str(uuid.uuid4())  # Unique ID for waypoint primitive
            waypoint_primitive = {
                    "primitive_id": primitive_id,
                    "primitive_type": "waypoint",
                    "continuous": False,
                    "primitive_inputs": [],
                    "primitive_outputs": [],
                    "completion": {
                        "ends_objective": True,
                        "ends_task": False,
                        "followed_by_primitives": [],
                        "inherit_other_primitives": False,
                        "resume_after": False
                    }
                }
            
            primitives.append(waypoint_primitive)

            for waypoint in path:
                
                objective_id = str(uuid.uuid4())  # Unique ID for each objective
                objective = {
                    "objective_id": objective_id,
                    "objective_type": "combined_primitives",
                    "parallel_execution": True,
                    "primitives": [
                        {
                            "primitive_id": primitive_id,
                            "parameters": {
                                "coordinates": waypoint,
                                "speed": self.mr_path_planner.get_max_speed(self.current_mission_id),
                                "max_speed": self.mr_path_planner.get_max_speed(self.current_mission_id),
                                "mobility_profile": 0,
                                "wait_time": 0
                            }
                        }
                    ]
                }
                objectives.append(objective)

            tasks[agent_id] = {
                "task_id": task_id,
                "primitives": primitives,
                "objectives": objectives
            }

        mission = {"mission_id": self.current_mission_id, "tasks": tasks}
        json_string = json.dumps(mission, indent=4)
        objective_count = sum(len(task["objectives"]) for task in tasks.values())
        self.get_logger().info(
            f'Generated plan JSON for mission "{self.current_mission_id}" '
            f'with {len(tasks)} task(s) and {objective_count} objective(s)'
        )
        
        return json_string


    def get_plan_service_callback(self, request, response):

        self.get_logger().info('Received GetPlan request')
        plan_json = self.path_to_plan_json(paths=self.paths)

        response.id = request.id
        response.plan = plan_json  # Placeholder for the actual plan
        return response


    def delete_planner_service_callback(self, request, response):
        # Process the DeletePlanner service request here
        self.get_logger().info('Received DeletePlanner request')
        response.id = request.id
        response.state = 1  # Assuming successful deletion
        return response


    def graph_timer_callback(self):
        self.watch_db_changes()
        self.publish_latest_image()

    def publish_latest_image(self):
        """Publishes the latest saved image """
        # Assuming you have already saved the image using matplotlib
        if self.path_image_saved:
            image_dir = "data/.planresults/"
            image_files = glob.glob(os.path.join(image_dir, "plan_*.png"))

            if not image_files:
                self.get_logger().warn("No images found in the directory.")
                return None
            
            # Get the latest file based on modification time
            latest_image_path = max(image_files, key=os.path.getmtime)
        else: # Only show the graph
            latest_image_path = 'data/.planresults/graph.png'

        # Read image with OpenCV
        image = cv2.imread(latest_image_path)
        # image = cv2.resize(image, (640, 480))  # Resize to smaller size
        


        if image is not None:
            # Convert OpenCV image to ROS message
            try:
                ros_image = self.bridge.cv2_to_compressed_imgmsg(image, dst_format='jpg')
                self.image_publisher.publish(ros_image)
                # self.get_logger().info("Published the graph image!")
            except Exception as e:
                self.get_logger().error(f"Error while converting image: {str(e)}")
        else:
            self.get_logger().warn("Image not found or could not be loaded.")



    # Methods
    def initialize_map(self):

        if self.load_map_from_local_folder:
            self.get_logger().info("Loading map from folder: "+ self.map_folder)
        else:
            self.get_logger().info("Loading map from database: "+ self.mongodb_url)

        # Free Roads
        if self.load_map_from_local_folder:
            free_lines=read_free_linestrings_from_disk(self.map_folder,crs=self.epsg)
        else:
            free_lines = read_features_from_db(geometry_type = "LineString",feature_type = "road", feature_collection = self.map_feature_collection, crs=self.epsg)
        self.line_graphs=[]
        
        for line in free_lines:
           line_graph = generate_graph_from_linestring(line)
           self.mark_graph_edges(line_graph, road=True)
           self.line_graphs.append(line_graph)

        # Free Polygons
        if self.load_map_from_local_folder:
            free_polys=read_free_polygons_from_disk(self.map_folder,crs=self.epsg)
        else:
            free_polys = read_features_from_db(geometry_type ="Polygon",feature_type = ["geofence", "workspace"], feature_collection = self.map_feature_collection, crs=self.epsg)
        self.poly_graphs=[]
        poly_pnts=[]
        for poly in free_polys:
            poly_pnts.append(generate_points_in_polygon(poly,self.points_in_polygon_dist,crs=self.epsg))
        for poly_point in poly_pnts:
            poly_graph = generate_delaunay_graph_from_points_in_polygon(poly_point,crs=self.epsg)
            self.mark_graph_edges(poly_graph, road=False)
            self.poly_graphs.append(poly_graph)

        # Risk Polygons
        if self.load_map_from_local_folder:
            risk_polys=read_risk_polygons_from_disk(self.map_folder,crs=self.epsg)
        else:
            risk_polys = read_features_from_db(geometry_type ="Polygon",feature_type = "risk", feature_collection = self.map_feature_collection, crs=self.epsg)
        self.risk_poly_graphs=[]
        self.risk_poly_gdfs=[]
        for gdf_poly in risk_polys:
            self.risk_poly_gdfs.append(gdf_poly)
            poly_graph = generate_graph_from_polygon(gdf_poly)
            self.risk_poly_graphs.append(poly_graph)
        
        # Collect all geometries
        geometries = []

        if free_lines:
            geometries.extend([line.geometry for line in free_lines if line is not None])
        if free_polys:
            geometries.extend([poly.geometry for poly in free_polys if poly is not None])
        if risk_polys:
            geometries.extend([poly.geometry for poly in risk_polys if poly is not None])

        if geometries:
            combined_geom = unary_union(geometries)  # Merge all geometries
            
            if combined_geom.is_empty:
                raise ValueError("Combined geometry is empty. Cannot compute centroid and radius.")

            central_point = combined_geom.centroid   # Compute centroid
            print("central point:")
            print(central_point)

        else:
            raise ValueError("No valid geometries found to compute central point and map radius.")

        # Generate OSMNX Graph (left, bottom, right, top)
        # bbox, *, network_type='all', simplify=True, retain_all=False, truncate_by_edge=False, custom_filter=None
        # self.G = ox.graph_from_bbox((2.881738450702528, 51.23322886000847 , 2.938772513420844, 51.25868020804094), simplify=False, 
        #                             network_type="all_private")
        self.G = ox.graph_from_point((central_point.y, central_point.x), simplify=False, 
                                    network_type="all_private", dist=self.map_radius)
        self.obstacle_gdf = ox.features_from_point((central_point.y, central_point.x),{"building":True,"amentity":True},dist=self.map_radius)

        #populate basic graph
        if(self.populate_graph):
            self.G = populate_graph(self.G,self.populate_min_distance)
        self.mark_graph_edges(self.G, road=True)
            
        #connect graphs
        for line_graph in self.line_graphs:
            self.G = connect_graphs(self.G,line_graph,self.line_G_max_distance)


        for poly_graph in self.poly_graphs:
            self.G = connect_graphs(self.G,poly_graph,self.poly_G_max_distance)
        
        # for risk_poly_graph in self.risk_poly_graphs:
        #     self.G = connect_graphs(self.G,risk_poly_graph,self.poly_G_max_distance)

        # Initially set all edges to non-risk
        for u, v, key, data in self.G.edges(keys=True, data=True):
            data['risk'] = False

        for risk_poly_gdf in self.risk_poly_gdfs:
            self.G = add_risks_to_edges(self.G,risk_poly_gdf)

        # # Iterate over the edges of the graph
        # for u, v, key, data in self.G.edges(keys=True, data=True):
        #     # Check if the "risk" attribute is True
        #     if data.get('risk'):
        #         print(f"Edge ({u} - {v}, key={key}) has a risk.")


        
        # Rename nodes for consistent naming (1, 2, 3, ... N)
        self.G=recalculate_node_ids(self.G)



        # Projected graph:
        G_proj = ox.project_graph(self.G)
        # self.G_projected = ox.consolidate_intersections(G_proj, rebuild_graph=True, tolerance=5, dead_ends=False)

        if(self.merge_nodes):
            self.G_projected = ox.consolidate_intersections(G_proj, rebuild_graph=True, tolerance=self.merge_nodes_max_distance, dead_ends=False)
        else:
            self.G_projected = G_proj

        self.init = True

        self.get_logger().info('MAP IS LOADED ')
        self.plot_graph_service()
        self.get_logger().info('Graph Image Saved ')

        # Initialize Multi-Robot Paths Planner
        self.mr_path_planner = MultiRobotPathPlanning(self.mapf , self.mongodb_url, "MapDB")
        self.mr_path_planner.graph = self.G
        self.mr_path_planner.local_feature_geometries = self.load_local_feature_geometries()

    @staticmethod
    def mark_graph_edges(graph, road):
        for _u, _v, _key, data in graph.edges(keys=True, data=True):
            data["road"] = bool(road)
        return graph


    def load_local_feature_geometries(self):
        feature_geometries = {}
        if not self.load_map_from_local_folder:
            return feature_geometries

        geojson_paths = glob.glob(os.path.join(self.map_folder, "**", "*.geojson"), recursive=True)
        for geojson_path in geojson_paths:
            try:
                with open(geojson_path, "r", encoding="utf-8") as file:
                    payload = json.load(file)
            except (OSError, json.JSONDecodeError) as exc:
                self.get_logger().warn(f"Could not load local GeoJSON feature file {geojson_path}: {exc}")
                continue

            features = payload.get("features", [payload]) if isinstance(payload, dict) else []
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                properties = feature.get("properties") or {}
                feature_id = properties.get("feature_id") or feature.get("id")
                geometry = feature.get("geometry")
                if feature_id and isinstance(geometry, dict):
                    feature_geometries[str(feature_id)] = geometry

        self.get_logger().info(f"Loaded {len(feature_geometries)} local feature geometries for mission feature_id lookup")
        return feature_geometries



    def allocate_destinations_to_agents(self, agents_to_plan, destinations, allocation_type):
        if allocation_type == "random":
            random.shuffle(destinations)
            for i, agent in enumerate(agents_to_plan):
                agent.destination = destinations[i % len(destinations)]
        elif allocation_type == "by_order":
            for i, agent in enumerate(agents_to_plan):
                agent.destination = destinations[i % len(destinations)]
    def set_agents_nominal_speeds(self, agents_to_plan, max_speed, speed_mode):
        if speed_mode=="max_speed":
            for agent in agents_to_plan:
                agent.nominal_speed = max_speed


    def calculate_shortest_path(self,origin,destination):
        starting_node= ox.nearest_nodes(self.G,origin[0],origin[1])
        destination_node= ox.nearest_nodes(self.G,destination[0],destination[1])
        if(self.G.nodes[starting_node]['x']==origin[0] and self.G.nodes[starting_node]['y']==origin[1]):
            path=[]
        else:
            path=[origin]

        a_star = AStar(self.G)
        self.get_logger().info('---- Performing A* search')
        route = a_star.search(starting_node, destination_node)
        # route = ox.shortest_path(self.G, starting_node, destination_node,weight="length")
        
        for node in route:
            path.append([self.G.nodes[node]['x'],self.G.nodes[node]['y']])

        if(self.G.nodes[destination_node]['x']!=destination[0] or self.G.nodes[destination_node]['y']!=destination[1]):
            path.append(destination)
        return path #list of lists [[1,2],[2,3]..]
    

    def get_total_path_for_ordered_waypoints(self,points):
        total_path=[]
        for i in range(1,len(points)):
            total_path += self.calculate_shortest_path(points[i-1],points[i])[:-1]
        # self.get_logger().info("get path:")
        # self.get_logger().info("%s"%str(total_path))
        return total_path    
    
    def plot_graph_service(self,paths=None):
        current_date = date.today().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        graph=self.G

        fig, ax = ox.plot_footprints(self.obstacle_gdf,figsize=(50, 50),alpha=0.4,show=False)
        fig2, ax2 = ox.plot_graph(graph, ax=ax, node_size=10, edge_color=["red" if data.get('risk') else "white" for u, v, key, data in graph.edges(keys=True, data=True)], edge_linewidth=0.7, node_color="red", show=False)
        # fig2,ax2=ox.plot_graph(graph,ax=ax,node_size=4,edge_color="w",edge_linewidth=0.7, node_color="r",show=False,save=True,filepath="./map.png")

        if paths is not None:
            self.paths_mutex.acquire()  # acquire the lock
            try:
                j = 0
                colors = ['r', 'g', 'y', 'c', 'm', 'k']
                # waypoints = self.mission_parser.get_mission_destinations(self.current_mission_id)
                # for waypoint in waypoints: 
                #     ax2.scatter(waypoint[0], waypoint[1], color='white', s=500)                  

                for agent_id, path in paths.items():
                    self.get_logger().info('plotting agent %s' % agent_id)
                    color = colors[j]  # Choose a color from the list
                    j += 1

                    # Plot the path with thick lines
                    path_x = [float(pt[0]) for pt in path]
                    path_y = [float(pt[1]) for pt in path]
                    
                    # Draw the path as a thick line
                    ax2.plot(path_x, path_y, color=color, linewidth=3)  # Adjust linewidth for thickness
                    
                    # Annotate waypoints with text
                    for i, pt in enumerate(path):
                        x = float(pt[0])
                        y = float(pt[1])
                        ax2.annotate(str(i), (x, y), c=color, fontsize=20)
                        
                        if i == 0:  # Annotate the agent ID at the first waypoint
                            ax2.annotate(str(agent_id), (x, y), c=color, fontsize=20)

                
                fig2.savefig("data/.planresults/plan_result_"+current_date+"-"+current_time+".png", format="png", dpi=100, bbox_inches="tight")
                self.path_image_saved = True

            finally:
                # Release the lock after accessing the paths is done
                self.paths_mutex.release()
            
        else:
            # Plot the node names
            for node in graph.nodes:
                text = str(node)
                x=graph.nodes[node]['x']
                y=graph.nodes[node]['y']
                # print(x,y)
                ax2.annotate(text, (x, y), c="r",fontsize=10)
            
            # Plot the edge lengths
            for edge in self.G.edges:
                # for edge in self.G.edges:
                node1= self.G.nodes[edge[0]]
                node2= self.G.nodes[edge[1]]
                x = (node1['x']+ node2['x'])/2
                y = (node1['y']+ node2['y'])/2
                txt = str(self.G.edges[edge]['length'])    
                ax2.annotate(txt, (x, y), c="g",fontsize=6)  
            
            fig2.savefig("data/.planresults/graph.png", format="png", dpi=100, bbox_inches="tight")  
            # fig2.savefig("data/.planresults/graph_"+current_date+"-"+current_time+".png", format="png", dpi=100, bbox_inches="tight")             
            # fig2.savefig("data/.planresults/graph_"+current_date+"-"+current_time+".png")
            

def main(args=None):
    rclpy.init(args=args)
    planner_node = PlannerNode()
    rclpy.spin(planner_node)
    planner_node.mongo_client.close()
    planner_node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
