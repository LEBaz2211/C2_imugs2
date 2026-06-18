from xml.etree.ElementTree import tostring
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from tools.bresenham import *
import yaml
import io

import json
from shapely.geometry import shape, Point


def project_on_xy(lat,long, UTM_BB, map_dimensions):
  origin = UTM_BB[0]
  UTM_dimensions = [UTM_BB[1][0] - UTM_BB[0][0], UTM_BB[1][1] - UTM_BB[0][1]]
  
  x = round((lat - origin[0])*map_dimensions[0]/UTM_dimensions[0])  
  y = round((long - origin[1])*map_dimensions[1]/UTM_dimensions[1])
  return x,y


def geojson_to_map_coordinates_json(geojson_file, map_dimensions): #, origin_lat_long, map_dimensions):
  Linestring_list = []
  UTM_BB = [[669994.9+150-30, 5569514.8-100-18],[670392.7+200-18, 5569912.6+20-18]]
  # load GeoJSON file containing sectors
  with open(geojson_file) as f:
      js = json.load(f)

  # check each polygon to see if it contains the point
  for feature in js['features']:
      Linestring = []
      coordinates_list = feature["geometry"]["coordinates"]
      while len(coordinates_list)==1 :
          coordinates_list= coordinates_list[0]
          feature["geometry"]["coordinates"] = feature["geometry"]["coordinates"][0]
      for i, coordinate in enumerate(coordinates_list):
        x,y = project_on_xy(coordinate[0],coordinate[1],UTM_BB,map_dimensions)
        # print(x,y)
        feature["geometry"]["coordinates"][i] = [x,y]
  return js


def draw_area(xmin,ymin,xmax,ymax,f):
    for i in range(xmin,xmax+1):
        for j in range(ymin,ymax+1):
            f.write("    - !!python/tuple " + "[" + str(i) + "," + str(j) + "]")

def draw_line(xmin,ymin,xmax,ymax, f):
    line = bresenham(xmin,ymin,xmax,ymax)
    for point in line:
        if (point[0]>=0 and point[0]<map_dimensions[0])  and (point[1]>=0 and point[1]<map_dimensions[1]):
            f.write("    - !!python/tuple " + "[" + str(point[0]) + "," + str(point[1]) + "]")
            f.write('\n')

def draw_geojson_line_features(geojson_file, map_dimensions, f):
    js = geojson_to_map_coordinates_json(geojson_file, map_dimensions)#,origin_lat_long, map_dimension))
    for feature in js['features']:
        for i in range(1,len(feature["geometry"]["coordinates"])):
            point0 = feature["geometry"]["coordinates"][i-1]
            point1 = feature["geometry"]["coordinates"][i]
            draw_line(point0[0],point0[1],point1[0],point1[1], f)



map_dimensions = [128,128]

with open('map_features.yaml', 'w') as f:
    # f.write('readme')
    # f.write("map:\n")
    f.write("    obstacles:\n")
    # print("================== working area")
    draw_geojson_line_features('map/geojson/working_area.geojson', map_dimensions,f)
    # print("================== line obstacles")
    draw_geojson_line_features('map/geojson/line_obstacles_clipped.geojson', map_dimensions,f)
    # print("================== buildings")
    draw_geojson_line_features('map/geojson/buildings_clipped.geojson', map_dimensions,f)
    # print("================== forbidden area")
    draw_geojson_line_features('map/geojson/forbidden_area_clipped.geojson', map_dimensions,f)
    # print("================== forest")
    # draw_geojson_line_features('map/geojson/forest_clipped.geojson', map_dimensions,f)

    f.write("\n    roads:\n")
    draw_geojson_line_features('map/geojson/dirt_roads_clipped.geojson', map_dimensions,f)
    draw_geojson_line_features('map/geojson/road_clipped.geojson', map_dimensions,f)

    f.write("\n    enemies:")