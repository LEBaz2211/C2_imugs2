import json

import os
import threading

import matplotlib.pyplot as plt

from datetime import date, datetime
import random

import osmnx as ox


import sys

from path_planning_lib.utils import *
from path_planning_lib.graph import *
from path_planning_lib.mapf import *
from path_planning_lib.models import *


from planner.mission_parser import MissionParser



class planner():
    def __init__(self):

        # ROS parameters
        self.mapf= "independent_agents"
        self.map_radius= 600.0
        self.epsg= "epsg:4326"
        self.initial_position= [59.44110222943638,25.863652970602914]
        self.poly_graph_connect_max_distance= 35.0
        self.line_graph_connect_max_distance= 35.0
        self.merge_nodes= True
        self.merge_nodes_max_distance= 1.0
        self.populate_graph= False
        self.populate_min_distance= 50.0
        self.points_in_polygon_dist= 15.0
        self.map_folder= "/map/estonia"

        self.parser= MissionParser()

        self.agents = dict()

        self.path = []
        self.paths = dict()
        self.paths_mutex = threading.Lock()
        self.path_image_saved = False

        self.G = None
        self.G_projected= None
        self.obstacle_gdf= None
        self.init= False

        txt=self.map_folder
        print("Loading map from folder: "+ txt)
        current_dir = os.getcwd()


        # Free Roads
        free_lines=read_free_linestrings_from_disk(self.map_folder,crs=self.epsg)
        self.line_graphs=[]
        
        for line in free_lines:
           self.line_graphs.append(generate_graph_from_linestring(line))

        # Free Polygons
        free_polys=read_free_polygons_from_disk(self.map_folder,crs=self.epsg)
        self.poly_graphs=[]
        poly_pnts=[]
        for poly in free_polys:
            poly_pnts.append(generate_points_in_polygon(poly,self.points_in_polygon_dist,crs=self.epsg))

        for poly_point in poly_pnts:
            self.poly_graphs.append(generate_delaunay_graph_from_points_in_polygon(poly_point,crs=self.epsg))
        # Risk Polygons
        risk_polys=read_risk_polygons_from_disk(self.map_folder,crs=self.epsg)
        self.risk_poly_graphs=[]
        self.risk_poly_gdfs=[]
        for gdf_poly in risk_polys:
            
            self.risk_poly_gdfs.append(gdf_poly)
            poly_graph = generate_graph_from_polygon(gdf_poly)
            # poly_graph = ox.graph_from_polygon(gdf_poly.geometry.values[0], network_type='all')
            self.risk_poly_graphs.append(poly_graph)



        self.initialize_map((self.initial_position[0],self.initial_position[1]))
        self.plot_graph_service()

        # Initialiaze fake agents
        agent1 = Buddy("agent_1", localization = [25.863652970602914, 59.44110222943638], current_speed = 0)
        agent2 = Buddy("agent_2", localization = [25.872700434810696,59.43666051657766], current_speed = 0)
        agent3 = Buddy("agent_3", localization = [25.87123071581121,59.43823652765113], current_speed = 0)
        self.agents.update({agent1.agent_id : agent1})
        self.agents.update({agent2.agent_id : agent2})
        self.agents.update({agent3.agent_id : agent3})

        # Read JSON data from mission.json file
        with open('mission.json', 'r') as file:
            mission_data = json.load(file)
        mission = json.dumps(mission_data)
        self.update_mission(mission)

        self.mission_defined = True
        self.path_image_saved = False

        self.state = 1


    # ROS callbacks


    def plan_mission(self):
        if (self.mission_defined):
            # consider agents that are detected and included in the mission
            agents_to_plan = [agent for agent in self.agents.values() if agent.agent_id in self.parser.get_mission_agents()]

            destination_points= self.parser.get_mission_destinations() 
            self.allocate_destinations_to_agents(agents_to_plan, destination_points, "random")
            self.set_agents_nominal_speeds(agents_to_plan, self.parser.get_max_speed(), "max_speed")
            
            new_paths = dict()

            # Single Agent
            if (len(agents_to_plan)==1):
                # only one agent for all given waypoints
                agent = agents_to_plan[0]
                agent_position = [agent.pose.position.longitude, agent.pose.position.latitude]
                waypoints= [agent_position] + self.parser.get_mission_destinations()
                new_paths[agent.agent_id] = self.get_total_path_for_ordered_waypoints(waypoints)

            # Multi-Agent
            elif (self.mapf == "independent_agents"):
                # assume one waypoint per agent, for now just randomly allocated
                i=0
                for agent in agents_to_plan:
                    a_star = AStar(self.G, agent)
                    print('---- Performing A* search')
                    route, f_score = a_star.search()
                    # route = ox.shortest_path(self.G, starting_node, destination_node,weight="length")
                    path = []
                    # print(type(route))
                    for state in route:
                        # print(type(state))
                        
                        node = state.get_node()
                        path.append([self.G.nodes[node]['x'],self.G.nodes[node]['y']])

                    # if(self.G.nodes[destination_node]['x']!=destination[0] or self.G.nodes[destination_node]['y']!=destination[1]):
                    #     path.append(destination)
                    # agent_position = [agent.pose.position.longitude, agent.pose.position.latitude]
                    new_paths[agent.agent_id] = path
                    
                    # print('calculated shortest path: "%s"' % str(agent_position))
                    # for pt in new_paths[agent.agent_id]:
                    #     print('path: ["%s", "%s"]' % (str(pt[0]), str(pt[1])))
                    i+=1

            elif (self.mapf == "cbs"): # Conflict Based Search
                # assume one waypoint per agent, for now allocated by order

                cbs = CBS(self.G)
                plan = cbs.search(agents_to_plan)
                for agent_id, route in plan.items():
                    path = []
                    for node in route:
                        path.append([self.G.nodes[node]['x'],self.G.nodes[node]['y']])
                    # if(self.G.nodes[destination_node]['x']!=destination[0] or self.G.nodes[destination_node]['y']!=destination[1]):
                    #     path.append(destination)
                    new_paths[agent_id] = path
                    

            # Update the paths with mutex lock
            self.paths_mutex.acquire()
            self.paths = new_paths
            self.paths_mutex.release()
            # Plot the result
            if (not self.path_image_saved):
                self.plot_graph_service(paths=self.paths)


    # Methods
    def initialize_map(self,point):
        self.G = ox.graph_from_point(point, simplify= False, network_type="all_private", dist=self.map_radius)
        self.obstacle_gdf = ox.features_from_point(point,{"building":True,"amentity":True},dist=self.map_radius)

        #populate basic graph
        if(self.populate_graph):
            self.G = populate_graph(self.G,self.populate_min_distance)
            
        #connect graphs
        for line_graph in self.line_graphs:
            self.G = connect_graphs(self.G,line_graph,self.line_graph_connect_max_distance)


        for poly_graph in self.poly_graphs:
            self.G = connect_graphs(self.G,poly_graph,self.poly_graph_connect_max_distance)
        
        # for risk_poly_graph in self.risk_poly_graphs:
        #     self.G = connect_graphs(self.G,risk_poly_graph,self.poly_graph_connect_max_distance)

        # Initially set all edges to non-risk
        for u, v, key, data in self.G.edges(keys=True, data=True):
            data['risk'] = False

        for risk_poly_gdf in self.risk_poly_gdfs:
            self.G = add_risks_to_edges(self.G,risk_poly_gdf)

        # Iterate over the edges of the graph
        # for u, v, key, data in self.G.edges(keys=True, data=True):
            # Check if the "risk" attribute is True
            # if data.get('risk'):
            #     print(f"Edge ({u} - {v}, key={key}) has a risk.")


        
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

        print('MAP IS LOADED ')


    def update_mission(self,mission_str):
        return self.parser.update(mission=mission_str)
    
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


    def calculate_shortest_path(self,graph, agent):
        

        a_star = AStar(self.G, agent)
        print('---- Performing A* search')
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
        # print("get path:")
        # print("%s"%str(total_path))
        return total_path    
    
    def plot_graph_service(self,paths=None):
        current_date = date.today().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H-%M-%S")

        graph=self.G

        fig, ax = ox.plot_footprints(self.obstacle_gdf,figsize=(50, 50),alpha=0.4,show=False)
        fig2, ax2 = ox.plot_graph(graph, ax=ax, node_size=4, edge_color=["red" if data.get('risk') else "white" for u, v, key, data in graph.edges(keys=True, data=True)], edge_linewidth=0.7, node_color="red", show=False)
        # fig2,ax2=ox.plot_graph(graph,ax=ax,node_size=4,edge_color="w",edge_linewidth=0.7, node_color="r",show=False,save=True,filepath="./map.png")

        if paths is not None:
            self.paths_mutex.acquire() # acquire the lock
            try:
                j = 0
                colors = ['r', 'g', 'y', 'c', 'm', 'k']
                waypoints= self.parser.get_mission_destinations()
                for waypoint in waypoints:                    
                    circle = plt.Circle((waypoint[0], waypoint[1]), 0.0001, color='white', alpha=0.5)
                    ax2.add_artist(circle)

                for agent_id, path in paths.items():
                    print('plotting agent %s'%agent_id)
                    color = colors[j]  # Choose a random color from the list
                    i=0
                    for pt in path:
                        text = str(i)
                        x=float(pt[0])
                        y=float(pt[1])
                        ax2.annotate(text, (x, y), c=color,fontsize=20)
                        if(i==0):
                            ax2.annotate(str(agent_id), (x, y), c=color,fontsize=20)
                        i+=1
                    j+=1
                
                fig2.savefig("plan_result_"+current_date+"-"+current_time+".png")
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

            fig2.savefig("graph___"+current_date+"-"+current_time+".png")
            

def main(args=None):
    planner = planner()
    planner.plan_mission()

if __name__ == '__main__':
    main()
