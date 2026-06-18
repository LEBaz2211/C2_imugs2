#!/usr/bin/env python3
# coding: utf-8
import os
import glob
import math
import numpy as np
import networkx as nx
import geopandas as gpd
import pandas as pd
from shapely.prepared import prep
from shapely.geometry import Point
from pymongo import MongoClient
from shapely.geometry import shape , Point, Polygon, MultiPolygon
EARTH_RADIUS_M = 6371009
def great_circle_vec(lat1, lng1, lat2, lng2, earth_radius=EARTH_RADIUS_M):
    """
    Calculate great-circle distances between pairs of points.

    Vectorized function to calculate the great-circle distance between two
    points' coordinates or between arrays of points' coordinates using the
    haversine formula. Expects coordinates in decimal degrees.

    Parameters
    ----------
    lat1 : float or numpy.array of float
        first point's latitude coordinate
    lng1 : float or numpy.array of float
        first point's longitude coordinate
    lat2 : float or numpy.array of float
        second point's latitude coordinate
    lng2 : float or numpy.array of float
        second point's longitude coordinate
    earth_radius : float
        earth's radius in units in which distance will be returned (default is
        meters)

    Returns
    -------
    dist : float or numpy.array of float
        distance from each (lat1, lng1) to each (lat2, lng2) in units of
        earth_radius
    """
    y1 = np.deg2rad(lat1)
    y2 = np.deg2rad(lat2)
    dy = y2 - y1

    x1 = np.deg2rad(lng1)
    x2 = np.deg2rad(lng2)
    dx = x2 - x1

    h = np.sin(dy / 2) ** 2 + np.cos(y1) * np.cos(y2) * np.sin(dx / 2) ** 2
    h = np.minimum(1, h)  # protect against floating point errors
    arc = 2 * np.arcsin(np.sqrt(h))

    # return distance in units of earth_radius
    return arc * earth_radius


def add_edge_lengths(G, precision=3, edges=None):
    """
    Add `length` attribute (in meters) to each edge.

    Vectorized function to calculate great-circle distance between each edge's
    incident nodes. Ensure graph is in unprojected coordinates, and
    unsimplified to get accurate distances.

    Note: this function is run by all the `graph.graph_from_x` functions
    automatically to add `length` attributes to all edges. It calculates edge
    lengths as the great-circle distance from node `u` to node `v`. When
    OSMnx automatically runs this function upon graph creation, it does it
    before simplifying the graph: thus it calculates the straight-line lengths
    of edge segments that are themselves all straight. Only after
    simplification do edges take on a (potentially) curvilinear geometry. If
    you wish to calculate edge lengths later, you are calculating
    straight-line distances which necessarily ignore the curvilinear geometry.
    You only want to run this function on a graph with all straight edges
    (such as is the case with an unsimplified graph).

    Parameters
    ----------
    G : networkx.MultiDiGraph
        unprojected, unsimplified input graph
    precision : int
        decimal precision to round lengths
    edges : tuple
        tuple of (u, v, k) tuples representing subset of edges to add length
        attributes to. if None, add lengths to all edges.

    Returns
    -------
    G : networkx.MultiDiGraph
        graph with edge length attributes
    """
    if edges is None:
        uvk = tuple(G.edges)
    else:
        uvk = edges

    # extract edge IDs and corresponding coordinates from their nodes
    x = G.nodes(data="x")
    y = G.nodes(data="y")
    try:
        # two-dimensional array of coordinates: y0, x0, y1, x1
        c = np.array([(y[u], x[u], y[v], x[v]) for u, v, k in uvk])
        # ensure all coordinates can be converted to float and are non-null
        assert not np.isnan(c.astype(float)).any()
    except (AssertionError, KeyError):  # pragma: no cover
        raise ValueError("some edges missing nodes, possibly due to input data clipping issue")

    # calculate great circle distances, round, and fill nulls with zeros
    dists = great_circle_vec(c[:, 0], c[:, 1], c[:, 2], c[:, 3]).round(precision)
    dists[np.isnan(dists)] = 0
    nx.set_edge_attributes(G, values=dict(zip(uvk, dists)), name="length")

#     utils.log("Added length attributes to graph edges")
    return G



def distance_between_coordinates(lat1, lon1, lat2, lon2):
    # Convert degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Earth's radius in kilometers
    R = 6371

    # Calculate the angular separation
    delta_sigma = math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))

    # Calculate the distance
    distance = R * delta_sigma

    return 1000*distance



def midpoint(lat1, lon1, lat2, lon2):

    """
    Find middle point between world coordinates

    Parameters
    ----------
    lat1 : float
    lon1 : float
    lat2 : float
    lon2 : float

    Returns
    -------
    (mid_lat,mid_lon) : tuple
    """
    # Convert degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Calculate the average latitude and longitude
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2

    # Convert radians back to degrees
    mid_lat = math.degrees(mid_lat)
    mid_lon = math.degrees(mid_lon)
    
    
    # Return the midpoint as a tuple (latitude, longitude)
    return (mid_lat, mid_lon)


def Random_Points_in_Bounds(polygon, resolution):   
    
    """
        Generate points inside polygon based on resolution


        Parameters
        ----------
        polygon :GeoPandas GeoDataFrame
        
        resolution : int

        Returns
        -------
        x,y : tuple(list,list)

    """
#    minx, miny, maxx, maxy = polygon['geometry'][0].bounds
    latmin, lonmin, latmax, lonmax = polygon['geometry'][0].bounds

    # prep_polygon = prep(polygon)
    
    points = []
    x=[]
    y=[]
    for lat in np.arange(latmin, latmax, resolution/100000):
        for lon in np.arange(lonmin, lonmax, resolution/100000):
            x.append(lat)
            y.append(lon)
            points.append(Point((lat, lon)))


    for i,j in zip(polygon.convex_hull[0].exterior.coords.xy[0],polygon.convex_hull[0].exterior.coords.xy[1]):
    # print(i,j)
        if(i  in x and j in y):
            continue
            
        x.append(i)
        y.append(j)
    

    # for i in polygon.convex_hull[0].exterior.coords.xy[0]:
    #     x.append(i)
        
    # for i in polygon.convex_hull[0].exterior.coords.xy[1]:
    #     y.append(i)
        

# validate if each point falls inside shape using
# the prepared polygon
    
#     valid_points.extend(filter(prep_polygon.contains, points))
#     x=np.arange(minx,maxx,1/number)
#     y=np.arange(miny,maxy,1/number)
#     x = np.random.uniform( minx, maxx, number )
#     y = np.random.uniform( miny, maxy, number )
    return x, y



def read_features_from_db(
    feature_collection, 
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
        feature_type (str or list, optional): Specific feature type(s) to filter.
        crs (str): Coordinate reference system for returned geometries (default: 'epsg:4326').

    Returns:
        List[gpd.GeoDataFrame]: List of GeoDataFrames containing matching features.
    """
    # print(f"Searching for features with criteria: feature_id={feature_id}, geometry_type={geometry_type}, feature_type={feature_type}")


    # Build the query dynamically based on provided arguments
    query = {}
    if feature_id:
        query["properties.feature_id"] = feature_id
    if geometry_type:
        query["geometry.type"] = geometry_type
    if feature_type:
        if isinstance(feature_type, list):
            query["properties.feature_type"] = {"$in": feature_type}  # Support multiple feature types
        else:
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



def read_free_linestrings_from_disk(filepath,crs="epsg:32633"):
    
    free_linestrings=[]
    base_path = filepath if os.path.isabs(filepath) else os.path.join(os.getcwd(), filepath)

    print("Looking for geojson files at : "+base_path)
    for file in glob.iglob(os.path.join(base_path, 'free_linestrings', '*.geojson')):
        gdf_free_linestring=gpd.read_file(file,crs=crs)
        gdf_line=gpd.GeoDataFrame(index=["myline"], geometry=[gdf_free_linestring['geometry'][0]])
#         gdf_line.set_crs(crs)
        free_linestrings.append(gdf_line)
    
    return free_linestrings


def read_free_polygons_from_disk(filepath,crs="epsg:32633"):

    free_polygons=[]
    base_path = filepath if os.path.isabs(filepath) else os.path.join(os.getcwd(), filepath)

    for file in glob.iglob(os.path.join(base_path, 'free_polygons', '*.geojson')):
        gdf_free_polygon=gpd.read_file(file)
    
        gdf_poly=gpd.GeoDataFrame(index=["myPoly"], geometry=[gdf_free_polygon['geometry'][0]],crs=crs)
        free_polygons.append(gdf_poly)
    
    return free_polygons

def read_risk_polygons_from_disk(filepath,crs="epsg:32633"):

    risk_polygons=[]
    base_path = filepath if os.path.isabs(filepath) else os.path.join(os.getcwd(), filepath)
    for file in glob.iglob(os.path.join(base_path, 'risk_polygons', '*.geojson')):
        gdf_risk_polygon=gpd.read_file(file)    
        gdf_poly=gpd.GeoDataFrame(index=["myPoly"], geometry=[gdf_risk_polygon['geometry'][0]],crs=crs)
        risk_polygons.append(gdf_poly)
    
    return risk_polygons

def read_virtual_geofence_from_disk(filepath,crs="epsg:32633"):
    
    virtual_geofences=[]
    base_path = filepath if os.path.isabs(filepath) else os.path.join(os.getcwd(), filepath)

    # print(current_dir+filepath+'/virtual_geofences/*.geojson')
    for file in glob.iglob(os.path.join(base_path, 'virtual_geofences', '*.geojson')):
        virtual_geofence=gpd.read_file(file,crs=crs)
        gdf_virtual_geofence =gpd.GeoDataFrame(index=["myPoly"], geometry=[virtual_geofence['geometry'][0]])
#         gdf_line.set_crs(crs)
        virtual_geofences.append(gdf_virtual_geofence)
    
    return virtual_geofences

def generate_points_in_polygon(polygon_gdf, point_distance, crs):

    # Generate random points within bounds
    minx, miny, maxx, maxy = polygon_gdf.bounds
    x_vals, y_vals = Random_Points_in_Bounds(polygon_gdf, point_distance)

    # Convert to GeoDataFrame of points
    df = pd.DataFrame({'points': list(zip(x_vals, y_vals))})
    df['points'] = df['points'].apply(Point)
    gdf_points = gpd.GeoDataFrame(df, geometry='points', crs=crs)

    # Prepare the polygon GeoDataFrame for spatial join
    polygon_gdf = polygon_gdf.set_geometry('geometry', inplace=False)

    # Perform spatial join to filter points inside the polygon
    sjoin = gpd.sjoin(gdf_points, polygon_gdf, predicate="within", how="left")

    # Return only points that intersect the polygon
    points_in_poly = gdf_points[sjoin.index_right.notna()]

    return points_in_poly
