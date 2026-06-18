#!/usr/bin/env python3
# coding: utf-8
import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from libpysal import weights
# from shapely.prepared import prep
from shapely.geometry import Point, Polygon,LineString
from scipy.spatial import Delaunay
from itertools import combinations
from .utils import *


class State(object):
    def __init__(self, time, node):
        self.time = time
        self.node = node
    def get_node(self):
        return self.node
    def get_time(self):
        return self.time
    def set_time(self, new_time):
        self.time = new_time
    def __eq__(self, other):
        return self.time == other.time and self.node == other.node
    def __str__(self):
        return "time: "+str(self.time)+" node: " +str(self.node)
    def __hash__(self):
        return hash((self.time, self.node))
    def same_location_as(self, other):
        return self.node == other.node
    


#GLOBAL VARIABLE TO ADD UNIQUE IDs in the nodes
NODE_IDs=-1



#Renames all graph from nodes starting from 1 
def recalculate_node_ids(graph):
    res = {}
    
    i=1
    for key in graph.nodes:
        #EACH NODE WILL HAVE A UNIQUE NEGATIVE ID
        res[key]= i
        i=i+1
    return nx.relabel_nodes(graph,res,copy=True)



def populate_graph(G,minimum_distance):


    """
    Add nodes to graphs between long distance edges

    Parameters
    ----------
    G : networkx.MultiDiGraph
        unprojected, unsimplified input graph
    
    minimum_distance: float
        minimum distance threshold between edges to add node

    Returns
    -------
    out : networkx.MultiDiGraph
          populated graph
    """

    global NODE_IDs
    mg= nx.MultiGraph(G)
    temp = nx.MultiGraph()
    counter=0
    removed_edges=[]
    for edge in mg.edges:
    
        if(mg.edges[edge]['length']>minimum_distance):
            lat1=mg.nodes[edge[0]]['y']
            lon1=mg.nodes[edge[0]]['x']
            lat2=mg.nodes[edge[1]]['y']
            lon2=mg.nodes[edge[1]]['x']
            lat3,lon3= midpoint(lat1,lon1,lat2,lon2)
            
            removed_edges.append([edge[0],edge[1]])
#             G.remove_edge(edge[0],edge[1])
            
            NODE_IDs=NODE_IDs-1
            
            temp.add_node(NODE_IDs)
            temp.nodes[NODE_IDs]['y']= lat3
            temp.nodes[NODE_IDs]['x']= lon3
            
            temp.add_node(edge[0])
            temp.nodes[edge[0]]['y']=lat1
            temp.nodes[edge[0]]['x']=lon1
            
            
            temp.add_node(edge[1])
            temp.nodes[edge[1]]['y']=lat2
            temp.nodes[edge[1]]['x']=lon2
            
            temp.add_edge(edge[0],NODE_IDs)
            temp.add_edge(NODE_IDs,edge[1])
            counter+=1
            
    for edge in removed_edges:
        mg.remove_edge(edge[0],edge[1])
    

    out=nx.compose(mg,temp)
    out=nx.MultiDiGraph(out)
    out=add_edge_lengths(out)
    return out



def generate_distance_graph_from_points_(points_,maximum_distance):

    """
        Generate graph, creating nodes from points_ coordinates and edges based on distance between the points_


    Parameters
    ----------
    points_ : GeoPandas GeoDataFrame 
              using geometry['points']
        
    
    maximum_distance: float
        maximum distance threshold between nodes to create an edge

    Returns
    -------
    dist_graph : networkx.MultiDiGraph

    """



    global NODE_IDs
    coordinates = np.column_stack((points_.geometry.x, points_.geometry.y))
    cords= []
    for i in coordinates:
        cords.append((i[0],i[1]))
        
        
    #GENERATE CONNECTIONS BASED ON DISTANCE BETWEEN POINTS
    #threshold is divided by 100000 because our coordinates are confusing 
    #TODO 
    #LEARN MORE ABOUT COORDINATE TRANSFORMATIONS
    dist = weights.distance.DistanceBand.from_array(cords, threshold=maximum_distance/100000)
    dist_graph = dist.to_networkx()
    
    
    res = {}
    
#     i=-1
    for key in dist_graph.nodes:
        #EACH NODE WILL HAVE A UNIQUE NEGATIVE ID
        res[key]= NODE_IDs
#         i=i-1
        NODE_IDs = NODE_IDs - 1
        for value in cords:
            dist_graph.nodes[key]['y']= float(value[1])
            dist_graph.nodes[key]['x']= float(value[0])
            cords.remove(value)
            break
    #EACH GRAPH NODE HAS A UNIQUE ID, OPENSTREETMAP GRAPHS PRODUCES ONLY POSITIVE IDs, WE USE NEGATIVE IDs
    #BECAUSE WHEN WE MERGE GRAPHS WE DO NOT WANT TO HAVE UNDEFINED BEHAVIOR BETWEEN NODES WITH THE SAME IDs
    nx.relabel_nodes(dist_graph,res,copy=False)
    # set_node_coords_id(dist_graph,coordinates)
    
    dist_graph= nx.MultiDiGraph(dist_graph)
#     ox.distance.add_edge_lengths(dist_graph)
    dist_graph=add_edge_lengths(dist_graph)
    return dist_graph


def generate_graph_from_linestring(linestring):
    

    """
        Generate graph, from points in linestring, each point becomes a nodes


    Parameters
    ----------
        linestring: GeoPandas GeoDataFrame

    Returns
    -------
    graph : networkx.MultiDiGraph

    """


    global NODE_IDs
    coordinates = np.column_stack((linestring.geometry.geometry[0].coords.xy[0], linestring.geometry[0].coords.xy[1]))
    cords= []
    for i in coordinates:
        cords.append((float(i[0]),float(i[1]))) 

    graph= nx.MultiDiGraph()
#     i=-150
    NODE_IDs=NODE_IDs-1
    for k in range(len(cords)):
        
        graph.add_node(NODE_IDs)
        graph.nodes[NODE_IDs]['y']= float(cords[k][1])
        graph.nodes[NODE_IDs]['x']= float(cords[k][0])
        if(k>0):
            graph.add_edge(NODE_IDs+1,NODE_IDs)
#         i=i-1
        NODE_IDs=NODE_IDs-1
                    
    # ox.distance.add_edge_lengths(graph)
    graph=add_edge_lengths(graph)
    return graph

def generate_graph_from_polygon(polygon_gdf):
    

    """
        Generate graph, from points in polygons, each point becomes a nodes


    Parameters
    ----------
        polygon_gdf: GeoPandas GeoDataFrame

    Returns
    -------
    graph : networkx.MultiDiGraph

    """
    global NODE_IDs
    coordinates = np.column_stack((polygon_gdf.geometry[0].boundary.coords.xy[0], polygon_gdf.geometry[0].boundary.coords.xy[1]))
    cords= []
    for i in coordinates:
        cords.append((float(i[0]),float(i[1]))) 

    graph= nx.MultiDiGraph()
#     i=-150
    NODE_IDs=NODE_IDs-1
    for k in range(len(cords)):
        
        graph.add_node(NODE_IDs)
        graph.nodes[NODE_IDs]['y']= float(cords[k][1])
        graph.nodes[NODE_IDs]['x']= float(cords[k][0])
        if(k>0):
            graph.add_edge(NODE_IDs+1,NODE_IDs)
#         i=i-1
        NODE_IDs=NODE_IDs-1
                    
    graph=add_edge_lengths(graph)
    return graph




def generate_delaunay_graph_from_points_in_polygon(points,crs="epsg:4326"):
    """
        Generate dalaunay graph, creating nodes from points coordinates 


    Parameters
    ----------
    points_ : GeoPandas GeoDataFrame 
              using geometry['points']
        


    Returns
    -------
    G : networkx.MultiDiGraph

    """

   
    global NODE_IDs

    formated_points=[]

    for pnt in points['points']:
        formated_points.append(Point(pnt.x, pnt.y))

    gdf_del=gpd.GeoDataFrame(geometry=formated_points,crs=crs)

    pos = {i: (gdf_del.iloc[i].geometry.x, gdf_del.iloc[i].geometry.y) for i in range(len(gdf_del))}

    gdf_del['x'] = gdf_del.geometry.x
    gdf_del['y'] = gdf_del.geometry.y
    
    
    # Create a Delaunay triangulation of the points
    
    tri = Delaunay(gdf_del[['x', 'y']])#qhull_options=" QJ  Qbb Qc Qz Q12")#QJ  Qbb Qc Qz Q12

    # Create a Graph from the Delaunay triangulation
    G = nx.MultiGraph()
    G.add_nodes_from(range(len(gdf_del)))

    for simplex in tri.simplices:
        G.add_edges_from(combinations(simplex, 2))
                
    res_delaunay={}
#     n=-1       
    for i, node in enumerate(G.nodes()):
        if(i==len(pos)):
            break
            
        res_delaunay[node]=NODE_IDs
#         n=n-1
        NODE_IDs = NODE_IDs-1
        G.nodes[node]['y'] = pos[i][1]    
        G.nodes[node]['x'] = pos[i][0]    

    nx.relabel_nodes(G,res_delaunay,copy=False)
    G= nx.MultiDiGraph(G)
#     ox.distance.add_edge_lengths(G)
    G.graph['crs']=crs
    G= add_edge_lengths(G)
    return G



# It works with unprojected graphs
# def connect_polygon_graph_with_other_graph(polygon,polygon_graph,other_graph,maximum_distance,projected_graph=False):
    
#     """
#         Generate dalaunay graph, creating nodes from points coordinates 


#     Parameters
#     ----------
#     points_ : GeoPandas GeoDataFrame 
#               using geometry['points']
        


#     Returns
#     -------
#     G : networkx.MultiDiGraph

#     """
    
    
    
#     #CALCULATE DISTANCE BETWEEN ROAD NODES AND FREE SPACE POLYGON
#     if(projected_graph):
#         constant=1
#     else:
#         constant=100000
        
        
#     pre_graph= nx.compose(polygon_graph,other_graph)
#     t2=0
#     t=gpd.GeoSeries(polygon['geometry'][0])
#     G= nx.MultiDiGraph()
    
#     for node in other_graph.nodes:
#         t2=gpd.GeoSeries([Point(other_graph.nodes[node]['x'],other_graph.nodes[node]['y'])])
#         dist = t.distance(t2)
    
#         #DISTANCE THRESHOLD TO CONNECT A ROAD NODE TO A POLYGON NODE
#         if(dist[0]*constant<maximum_distance):
#             for node_p in polygon_graph.nodes:
#                 #CALCULATE WHICH EXACT NODE IS NEAREST TO YOU AND ADD IT TO THE GRAPH
#                 if(constant*np.linalg.norm(np.array((polygon_graph.nodes[node_p]['x'],polygon_graph.nodes[node_p]['y']))-np.array((other_graph.nodes[node]['x'],other_graph.nodes[node]['y'])))<=maximum_distance):
                   
#                     ##Check if node extist
#                     if node not in G.nodes:
#                         G.add_node(node)
#                         G.nodes[node]['y']= other_graph.nodes[node]['y']
#                         G.nodes[node]['x']= other_graph.nodes[node]['x']
                        
#                     if node_p not in G.nodes:  
#                         G.add_node(node_p)
#                         G.nodes[node_p]['y']= polygon_graph.nodes[node_p]['y']
#                         G.nodes[node_p]['x']= polygon_graph.nodes[node_p]['x']
                    
#                     G.add_edge(node,node_p)
# #                     break
    
#     out=nx.compose(pre_graph,G)
    
# #     print(out.nodes)
# #     ox.distance.add_edge_lengths(out)
#     out=add_edge_lengths(out)
#     return out


def connect_graphs(g1,g2,maximum_distance,projected_graph=False):
    
    """
        Connect two graphs, nodes between the graph are connected if their distance is less than maximum _distance 


        Parameters
        ----------
        g1 : networkx.MultiDiGraph
            unprojected, unsimplified input graph
        
        g2 : networkx.MultiDiGraph
            unprojected, unsimplified input graph

        maximum_distance : float
                maximum distance between to nodes to be connected

        
        projected_graph: bool

        Returns
        -------
        out : networkx.MultiDiGraph

    """
    
    
    if(projected_graph):
        constant=1
    else:
        constant=100000
        
        
    pre_graph= nx.compose(g1,g2)
    G= nx.MultiGraph()
    
    for node2 in g2.nodes:
        
#         t2=gpd.GeoSeries([Point(g2.nodes[node2]['x'],g2.nodes[node2]['y'])])
        lat2= g2.nodes[node2]['y']
        lon2=g2.nodes[node2]['x']
        
        for node1 in g1.nodes:
            lat1 = g1.nodes[node1]['y']
            lon1 = g1.nodes[node1]['x']
            
            
#             if(constant*np.linalg.norm(np.array((g1.nodes[node1]['y'],g1.nodes[node1]['x']))-np.array((g2.nodes[node2]['y'],g2.nodes[node2]['x'])))<=maximum_distance):            
            
            if(distance_between_coordinates(lat1,lon1,lat2,lon2)<maximum_distance):
                
                if node1 not in G.nodes:
                    G.add_node(node1)
                    G.nodes[node1]['y']= lat1 #g1.nodes[node1]['y']
                    G.nodes[node1]['x']= lon1 #g1.nodes[node1]['x']
                        
                if node2 not in G.nodes:  
                    G.add_node(node2)
                    G.nodes[node2]['y']= lat2 #g2.nodes[node2]['y']
                    G.nodes[node2]['x']= lon2 #g2.nodes[node2]['x']   
                

                G.add_edge(node1,node2)

    G= nx.MultiDiGraph(G)
    
                
    out=nx.compose(pre_graph,G)
    ox.distance.add_edge_lengths(out)
    out=add_edge_lengths(out)
    return out


def add_risks_to_edges(graph, risk_polygon_gdf):
    """
    Add risks to a graph's edges based on a risk polygon.

    Parameters
    ----------
    graph : networkx.MultiDiGraph
        Unprojected, unsimplified input graph.

    risk_polygon_gdf : GeoDataFrame
        GeoDataFrame representing one or more risk polygons.

    Returns
    -------
    graph : networkx.MultiDiGraph
        Graph with risk attributes added to the edges.
    """
    # Iterate over the edges in the graph
    for u, v, key in graph.edges(keys=True):
        # Get the coordinates of the start and end nodes of the edge
        start_node_coords = (graph.nodes[u]['x'], graph.nodes[u]['y'])
        end_node_coords = (graph.nodes[v]['x'], graph.nodes[v]['y'])
        
        # Create a LineString for the edge
        edge_line = LineString([start_node_coords, end_node_coords])
        
        # Check if the edge intersects with any risk polygon
        intersects_polygon = risk_polygon_gdf.intersects(edge_line).any()
        
        if intersects_polygon:
            # Add the "risk" attribute to the edge
            graph[u][v][key]['risk'] = True
        else:
            # Ensure the risk attribute is explicitly set to False if not already present
            graph[u][v][key].setdefault('risk', False)
    
    return graph

    
    
    # #Make geodataframes from graph data
    # nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)


    # nodes_in_polygon = nodes[nodes.within()]

    # import numpy as np
    # #Create a new column in the nodes geodataframe with number of visits
    # #I have filled it up with random integers
    # nodes['visits'] = np.random.randint(0,1000, size=len(nodes))

    # #Now make the same graph, but this time from the geodataframes
    # #This will help retain the 'visits' columns
    # G = ox.utils_graph.graph_from_gdfs(nodes, edges)

    #Then plot a graph where node size and node color are related to the number of visits
    # nc = ox.plot.get_node_colors_by_attr(G,'visits',num_bins = 5)
    # ox.plot_graph(G,fig_height=8,fig_width=8,node_size=nodes['visits'], node_color=nc)