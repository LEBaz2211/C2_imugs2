from tools.bresenham import *
from read_geojson import *


def draw_area(xmin,ymin,xmax,ymax):
    for i in range(xmin,xmax+1):
        # print("    - !!python/tuple ",[i,i+(ymin-xmin)])
        # print("    - !!python/tuple ",[i,i+(ymin-xmin)+1])
        for j in range(ymin,ymax+1):
            print("    - !!python/tuple ",[i,j])

def draw_line(xmin,ymin,xmax,ymax):
    line = bresenham(xmin,ymin,xmax,ymax)
    for point in line:
        print("    - !!python/tuple ",[point[0],point[1]])

def draw_geojson_line_features(geojson_file, map_dimensions):
    js = geojson_to_map_coordinates_json(geojson_file, map_dimensions)#,origin_lat_long, map_dimension))
    for feature in js['features']:
        for i in range(1,len(feature["geometry"]["coordinates"][0])):
            point0 = feature["geometry"]["coordinates"][0][i-1]
            point1 = feature["geometry"]["coordinates"][0][i]
            draw_line(point0[0],point0[1],point1[0],point1[1])

map_dimensions = [128,128]

xmin =127
ymin=113

xmax=124
ymax=128

# draw_line(xmin,ymin,xmax,ymax)

draw_geojson_line_features('map/geojson/line_obstacles_clipped.geojson', map_dimensions)

