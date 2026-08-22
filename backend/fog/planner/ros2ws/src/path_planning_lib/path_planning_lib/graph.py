#!/usr/bin/env python3
# coding: utf-8
import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from libpysal import weights
from pyproj import Transformer
# from shapely.prepared import prep
from shapely.geometry import Point, Polygon,LineString
from scipy.spatial import Delaunay, cKDTree
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


class EdgeSnapIndex:
    """Metric lookup from mission endpoints to active-scenario graph edges.

    The projected graph is a read-only derivative of the exact active scenario
    graph.  It retains the base graph's ``(u, v, key)`` identifiers so a snap
    can be applied to a temporary query graph without changing the scenario.
    """

    def __init__(self, graph, projected_graph=None):
        if graph.number_of_edges() == 0:
            raise ValueError("Cannot build an endpoint index for an empty routing graph")
        if not graph.graph.get("crs"):
            raise ValueError("Routing graph is missing CRS metadata")

        self.graph = graph
        self.projected_graph = projected_graph or ox.project_graph(graph)
        self.to_projected = Transformer.from_crs(
            graph.graph["crs"],
            self.projected_graph.graph["crs"],
            always_xy=True,
        )
        self.to_graph = Transformer.from_crs(
            self.projected_graph.graph["crs"],
            graph.graph["crs"],
            always_xy=True,
        )
        self.edge_ids = []
        projected_lines = []
        for u, v, key, data in graph.edges(keys=True, data=True):
            if u == v or data.get("risk", False):
                continue
            projected_data = self.projected_graph.get_edge_data(u, v, key)
            if projected_data is None:
                continue
            line = projected_data.get("geometry")
            if not isinstance(line, LineString):
                line = LineString(
                    [
                        (
                            float(self.projected_graph.nodes[u]["x"]),
                            float(self.projected_graph.nodes[u]["y"]),
                        ),
                        (
                            float(self.projected_graph.nodes[v]["x"]),
                            float(self.projected_graph.nodes[v]["y"]),
                        ),
                    ]
                )
            if line.is_empty or line.length <= 0:
                continue

            # OSMnx edge geometry normally follows u -> v, but imported graph
            # attributes are not required to do so. Normalize it before using
            # the interpolation fraction to split a directed edge.
            u_point = Point(
                float(self.projected_graph.nodes[u]["x"]),
                float(self.projected_graph.nodes[u]["y"]),
            )
            if Point(line.coords[-1]).distance(u_point) < Point(line.coords[0]).distance(u_point):
                line = LineString(list(line.coords)[::-1])
            self.edge_ids.append((u, v, key))
            projected_lines.append(line)

        if not projected_lines:
            raise ValueError("Routing graph contains no non-risk edges for endpoint snapping")
        self.projected_lines = gpd.GeoSeries(
            projected_lines,
            crs=self.projected_graph.graph["crs"],
        )

    def snap(self, location, risk_polygons=None, endpoint_tolerance_m=0.25):
        """Return the nearest risk-safe point along a routable directed edge."""
        lon, lat = float(location[0]), float(location[1])
        x_coord, y_coord = self.to_projected.transform(lon, lat)
        point = Point(x_coord, y_coord)
        distances = self.projected_lines.distance(point).to_numpy()
        for index in np.argsort(distances):
            line = self.projected_lines.iloc[int(index)]
            distance_along = float(line.project(point))
            projected_snap = line.interpolate(distance_along)
            snap_lon, snap_lat = self.to_graph.transform(projected_snap.x, projected_snap.y)
            coordinate = [float(snap_lon), float(snap_lat)]
            if not _endpoint_connector_is_risk_free(location, coordinate, risk_polygons or []):
                continue

            u, v, key = self.edge_ids[int(index)]
            if distance_along <= endpoint_tolerance_m:
                node = u
                coordinate = [float(self.graph.nodes[u]["x"]), float(self.graph.nodes[u]["y"])]
                fraction = 0.0
            elif line.length - distance_along <= endpoint_tolerance_m:
                node = v
                coordinate = [float(self.graph.nodes[v]["x"]), float(self.graph.nodes[v]["y"])]
                fraction = 1.0
            else:
                node = None
                fraction = distance_along / line.length
            return {
                "edge": (u, v, key),
                "fraction": float(fraction),
                "coordinate": coordinate,
                "node": node,
                "snap_distance_m": float(distances[int(index)]),
            }
        raise RuntimeError(f"No risk-safe routing edge is available near endpoint {location}")


def add_virtual_endpoint_nodes(graph, snaps):
    """Split snapped edges on a query-local graph and resolve endpoint nodes.

    All mutations apply to the returned graph copy. Parallel and reverse edges
    between the selected endpoints are split together so directionality and
    edge attributes remain valid, including when both query points lie on the
    same base edge.
    """
    query_graph = graph.copy()
    resolved = [dict(snap) for snap in snaps]
    grouped = {}
    for index, snap in enumerate(resolved):
        if snap.get("node") is not None:
            continue
        u, v, _key = snap["edge"]
        grouped.setdefault(frozenset((u, v)), []).append((index, snap))

    for group_number, items in enumerate(grouped.values()):
        canonical_u, canonical_v, _key = items[0][1]["edge"]
        positions = []
        for index, snap in items:
            edge_u, edge_v, _edge_key = snap["edge"]
            fraction = snap["fraction"] if (edge_u, edge_v) == (canonical_u, canonical_v) else 1.0 - snap["fraction"]
            positions.append((float(fraction), index, snap["coordinate"]))
        positions.sort(key=lambda item: item[0])

        virtuals = []
        for position, index, coordinate in positions:
            if virtuals and abs(position - virtuals[-1][0]) <= 1e-12:
                node = virtuals[-1][1]
            else:
                node = ("query_endpoint", group_number, len(virtuals))
                query_graph.add_node(node, x=float(coordinate[0]), y=float(coordinate[1]), virtual=True)
                virtuals.append((position, node))
            resolved[index]["node"] = node

        directed_edges = []
        for edge_u, edge_v in ((canonical_u, canonical_v), (canonical_v, canonical_u)):
            for edge_key, data in list((query_graph.get_edge_data(edge_u, edge_v) or {}).items()):
                directed_edges.append((edge_u, edge_v, edge_key, dict(data)))
                query_graph.remove_edge(edge_u, edge_v, edge_key)

        if not directed_edges:
            raise RuntimeError(f"Cannot split missing routing edge {canonical_u!r} <-> {canonical_v!r}")

        for edge_u, edge_v, edge_key, data in directed_edges:
            if (edge_u, edge_v) == (canonical_u, canonical_v):
                ordered_virtuals = virtuals
            else:
                ordered_virtuals = [(1.0 - position, node) for position, node in reversed(virtuals)]
            chain = [(0.0, edge_u), *ordered_virtuals, (1.0, edge_v)]
            original_length = float(data.get("length", 0.0))
            for (start_fraction, start_node), (end_fraction, end_node) in zip(chain, chain[1:]):
                segment_data = dict(data)
                segment_data["length"] = original_length * max(0.0, end_fraction - start_fraction)
                segment_data["geometry"] = LineString(
                    [
                        (float(query_graph.nodes[start_node]["x"]), float(query_graph.nodes[start_node]["y"])),
                        (float(query_graph.nodes[end_node]["x"]), float(query_graph.nodes[end_node]["y"])),
                    ]
                )
                query_graph.add_edge(start_node, end_node, key=edge_key, **segment_data)
    return query_graph, resolved


def _endpoint_connector_is_risk_free(start, destination, risk_polygons):
    connector = LineString([start, destination])
    return not any(
        risk_polygon.intersection(connector).length > 1e-12
        for risk_polygon in risk_polygons
    )



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
            # A free road LineString describes traversable geometry, not a
            # one-way traffic rule.  Keep both directions so a robot snapped
            # near the final coordinate can still route back along the road.
            graph.add_edge(NODE_IDs,NODE_IDs+1)
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
    
    
    out = nx.compose(g1, g2)
    nodes1 = list(g1.nodes)
    nodes2 = list(g2.nodes)
    if not nodes1 or not nodes2:
        return out

    if projected_graph:
        points1 = np.array([(float(g1.nodes[node]['x']), float(g1.nodes[node]['y'])) for node in nodes1])
        points2 = np.array([(float(g2.nodes[node]['x']), float(g2.nodes[node]['y'])) for node in nodes2])
        query_radius = maximum_distance
    else:
        # Index latitude/longitude nodes on a 3-D Earth sphere. This preserves
        # the legacy metric threshold while avoiding a full nested scan.
        earth_radius_m = 6_371_000.0

        def earth_centered_points(graph, nodes):
            latitudes = np.radians([float(graph.nodes[node]['y']) for node in nodes])
            longitudes = np.radians([float(graph.nodes[node]['x']) for node in nodes])
            cos_latitudes = np.cos(latitudes)
            return earth_radius_m * np.column_stack(
                (
                    cos_latitudes * np.cos(longitudes),
                    cos_latitudes * np.sin(longitudes),
                    np.sin(latitudes),
                )
            )

        points1 = earth_centered_points(g1, nodes1)
        points2 = earth_centered_points(g2, nodes2)
        query_radius = 2.0 * earth_radius_m * np.sin(maximum_distance / (2.0 * earth_radius_m))

    tree = cKDTree(points1)
    new_edges = []
    for node2, point2 in zip(nodes2, points2):
        lat2 = float(g2.nodes[node2]['y'])
        lon2 = float(g2.nodes[node2]['x'])
        for index1 in tree.query_ball_point(point2, query_radius):
            node1 = nodes1[index1]
            lat1 = float(g1.nodes[node1]['y'])
            lon1 = float(g1.nodes[node1]['x'])
            within_threshold = (
                np.hypot(lon1 - lon2, lat1 - lat2) < maximum_distance
                if projected_graph
                else distance_between_coordinates(lat1, lon1, lat2, lon2) < maximum_distance
            )
            if not within_threshold:
                continue
            forward_key = out.add_edge(node1, node2)
            reverse_key = out.add_edge(node2, node1)
            new_edges.extend(((node1, node2, forward_key), (node2, node1, reverse_key)))

    # Existing edges already have lengths. Recomputing every accumulated edge
    # for every imported LineString was the dominant scenario activation cost.
    if new_edges:
        out = add_edge_lengths(out, edges=tuple(new_edges))
    return out


def connect_graph_collection(base_graph, graphs, maximum_distance, projected_graph=False):
    """Compose and connect a collection with the same cross-graph rule as connect_graphs.

    The legacy caller appended hundreds of OSM LineStrings one at a time. That
    repeatedly copied the whole accumulated graph. A single spatial query is
    equivalent: add connector edges only between nodes belonging to different
    source graphs, while preserving every source graph's own edges.
    """
    source_graphs = [base_graph, *graphs]
    nonempty_graphs = [graph for graph in source_graphs if graph.number_of_nodes()]
    if not nonempty_graphs:
        return nx.MultiDiGraph()
    out = nx.compose_all(nonempty_graphs)

    nodes = []
    groups = []
    coordinates = []
    for group_index, graph in enumerate(source_graphs):
        for node in graph.nodes:
            nodes.append(node)
            groups.append(group_index)
            coordinates.append((float(graph.nodes[node]['x']), float(graph.nodes[node]['y'])))
    if len(nodes) < 2:
        return out

    coordinate_array = np.asarray(coordinates)
    if projected_graph:
        points = coordinate_array
        query_radius = maximum_distance
    else:
        earth_radius_m = 6_371_000.0
        longitudes = np.radians(coordinate_array[:, 0])
        latitudes = np.radians(coordinate_array[:, 1])
        cos_latitudes = np.cos(latitudes)
        points = earth_radius_m * np.column_stack(
            (
                cos_latitudes * np.cos(longitudes),
                cos_latitudes * np.sin(longitudes),
                np.sin(latitudes),
            )
        )
        query_radius = 2.0 * earth_radius_m * np.sin(maximum_distance / (2.0 * earth_radius_m))

    new_edges = []
    tree = cKDTree(points)
    for index1, index2 in tree.query_pairs(query_radius):
        if groups[index1] == groups[index2]:
            continue
        node1 = nodes[index1]
        node2 = nodes[index2]
        lon1, lat1 = coordinates[index1]
        lon2, lat2 = coordinates[index2]
        within_threshold = (
            np.hypot(lon1 - lon2, lat1 - lat2) < maximum_distance
            if projected_graph
            else distance_between_coordinates(lat1, lon1, lat2, lon2) < maximum_distance
        )
        if not within_threshold:
            continue
        forward_key = out.add_edge(node1, node2)
        reverse_key = out.add_edge(node2, node1)
        new_edges.extend(((node1, node2, forward_key), (node2, node1, reverse_key)))

    if new_edges:
        out = add_edge_lengths(out, edges=tuple(new_edges))
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
