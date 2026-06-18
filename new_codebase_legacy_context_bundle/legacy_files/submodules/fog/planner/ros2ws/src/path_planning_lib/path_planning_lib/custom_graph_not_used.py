# Custom graph code for custom path planning algorithms
# Author: Alexandre La Grappe
# Delaunay algorithm found on https://github.com/abbottjord94/python-delaunay
import sys
sys.path.insert(0, '../')
import os
import math
import random
import sys
import copy
import matplotlib.pyplot as plt
import json
import geojson
import geopandas as gpd
# import contextily as cx
import itertools
import numpy as np
from scipy.spatial import Delaunay
import triangle as tr
from tools.geographic_computation import *






# import pygame

# Basic Vertex class


class Vertex():
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.cost = 0
        self.allowed = True
        self.is_from_feature = False
        # self._neighbors = []
        self.edges_dict = {}
        self.feature_marker = -1
    
    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value
    
    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value


    # Position of the vertex
    def pos(self):
        return [self._x, self._y]

    # Function to find the metric length to another vertex
    def getMetricLengthTo(self, other_vertex):
        length = latlon_to_meters_dist(self.y, self.x, other_vertex.y, other_vertex.x)
        return length

    # Add neighboring vertex
    def connect_to_vertex_with_edge(self, vertex, edge):
        if not self.isConnectedTo(vertex):
            self.edges_dict[vertex] = edge
            # self._neighbors.append(vertex)
            vertex.connect_to_vertex_with_edge(self, edge)

    # Remove neighboring vertex
    def disconnect_from_vertex(self, vertex):
        if self.isConnectedTo(vertex):
            self.edges_dict.pop(vertex)
            # self._neighbors.append(vertex)
            vertex.disconnect_from_vertex(self)

    # Check if a given vertex is already connected to this one
    def isConnectedTo(self, vertex):
        return vertex in self.edges_dict


    # Determines if two vertices are equivalent
    def isEqual(self, other_point):
        if(self.x == other_point.x and self.y == other_point.y):
            return True
        else:
            return False

    # Convert the vertex into a string (for debugging purposes)
    def pointToStr(self):
        return str(self.pos())

    # Make sure it can't be removed from the graph
    def isFromFeature(self, force_valid):
        self.is_from_feature = force_valid
        return True



# Basic Edge class
class Edge():
    def __init__(self, a, b):
        # if a is not b:
        self.a = a
        self.b = b
        self.cost = 0
        self.allowed = True
        self.is_from_feature = False

        self.computeCost()

    def update_vertices(self, a,b):
        if a == b:
            return False
        else:
            a.edges_dict[b] = self
            b.edges_dict[a] = self
            self.a = a
            self.b = b
            # self.a.x = a.x
            # self.a.y = a.y
            # self.b.x = b.x
            # self.b.y = b.y
            self.computeCost()

    
    # Function to find the angular length of an edge
    def getAngularLength(self):
        ang_dist = math.sqrt(math.pow(self.a.pos()[1] - self.b.pos()[1],
                  2) + math.pow(self.a.pos()[0] - self.b.pos()[1], 2))
        return ang_dist
    # Function to find the metric length of an edge
    def getMetricLength(self):
        length = latlon_to_meters_dist(self.a.pos()[1], self.a.pos()[0], self.b.pos()[1], self.b.pos()[0])
        return length

    # Tests if two edges are equivalent to each other
    def isEqual(self, other_edge):
        if (self.a.isEqual(other_edge.a) or self.b.isEqual(other_edge.a)) and (self.a.isEqual(other_edge.b) or self.b.isEqual(other_edge.b)):
            return True
        elif self == other_edge:
            return True
        else:
            return False
    
    def shares_vertex_with(self, other_edge):
        if self.a.isEqual(other_edge.a) or self.a.isEqual(other_edge.b) or self.b.isEqual(other_edge.b) or self.b.isEqual(other_edge.a):
            return True

        else:
            return False

    # Converts an edge to a string (for debugging purposes)
    def edgeToStr(self):
        return str([self.a.pos(), self.b.pos()])

    # Calculate the length of an edge
    def length(self):
        return math.sqrt(math.pow(self.b.pos()[0] - self.a.pos()[0], 2) + math.pow(self.b.pos()[1] - self.a.pos()[1], 2))
    
    # Function to find the intersection point of two edges
    def get_intersection_vertex(self, other_edge):
        if self.shares_vertex_with(other_edge):
            return None
        x1, y1 = self.a.x, self.a.y
        x2, y2 = self.b.x, self.b.y
        x3, y3 = other_edge.a.x, other_edge.a.y
        x4, y4 = other_edge.b.x, other_edge.b.y

        den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if den == 0:
            # Lines are parallel
            return None
        else:
            t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / den
            u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                # Intersection point exists
                x = x1 + t*(x2-x1)
                y = y1 + t*(y2-y1)
                return Vertex(x, y)
            else:
                # Lines do not intersect
                return None

    # Function to find the point at a certain distance from an endpoint
    def create_vertex_at_metric_distance(self, end, start, metric_distance):
        distance = metric_distance/111000 # 1∘ of latitude or longitude is +- 111 kilometers
        x1, y1 = start.x, start.y
        x2, y2 = end.x, end.y
        length = ((x2-x1)**2 + (y2-y1)**2)**0.5
        if length==0.0:
            print("create_vertex_at_metric_distance -> start and end seem to be same point:")
            # print(start, end)
            # print(start.isEqual(end))
            return start
        x = x1 - (distance/length)*(x2-x1)
        y = y1 - (distance/length)*(y2-y1)
        return Vertex(x, y)

    # Determine if two edges intersect
    def edgeIntersection(self, other_edge):

        if self.isEqual(other_edge):
            return False
        else:
            try:
                x1 = self.a.pos()[0]
                x2 = self.b.pos()[0]
                x3 = other_edge.a.pos()[0]
                x4 = other_edge.b.pos()[0]
                y1 = self.a.pos()[1]
                y2 = self.b.pos()[1]
                y3 = other_edge.a.pos()[1]
                y4 = other_edge.b.pos()[1]
                den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
                if den == 0:
                    # Lines are parallel
                    return None

                t = (((x1 - x3)*(y3 - y4)) - ((y1 - y3)*(x3 - x4))) / den
                u = (((x2 - x1)*(y1 - y3)) - ((y2 - y1)*(x1 - x3))) / den

                # If 0 <= t <= 1 or 0 <= u <= 1, then an intersection occurs.
                if (t >= 0 and t <= 1) and (u >= 0 and u <= 1):
                    int_x = int(x1 + t*(x2 - x1))
                    int_y = int(y1 + t*(y2 - y1))
                    int_point = Vertex(int_x, int_y)

                    # If the intersection vertex is one of the edge vertices, then an intersection is not considered to have occurred (i.e., these are edges connected at the same vertex)
                    if self.a.isEqual(int_point) or self.b.isEqual(int_point) or other_edge.a.isEqual(int_point) or other_edge.b.isEqual(int_point):
                        return False

                    # If there is no vertex, these edges intersect
                    else:
                        return True

                else:
                    return False
            except:
                # A divide-by-zero error is interpreted as the edges not intersecting
                return False

    # Make sure it can't be removed from the graph
    def isFromFeature(self, force_valid):
        self.is_from_feature = force_valid
        return True

    def computeCost(self):
        dist = self.getMetricLength()
        self.cost = dist


# Basic Triangle class
class Triangle():

    # Cannot create a triangle if any two vertices are the same
    def __init__(self, a, b, c):
        if a is not b and a is not c:
            self.a = a
        if b is not a and b is not c:
            self.b = b
        if c is not a and c is not b:
            self._c = c

    # Test if any two triangles are equal (defined as sharing all three vertices)
    def isEqual(self, other_tri):
        if (self.a is other_tri.a or self.a is other_tri.b or self.a is other_tri._c) and (self.b is other_tri.a or self.b is other_tri.b or self.b is other_tri._c) and (self._c is other_tri.a or self._c is other_tri.b or self._c is other_tri._c):
            return True
        else:
            return False

    # Prints the triangle in a neat format (for debugging purposes)
    def printTriangle(self):
        print("A: " + self.a.pointToStr() + " B: " +
              self.b.pointToStr() + " C: " + self._c.pointToStr())

# Graph class


class Graph():
    def __init__(self):

        # This will be a list of vertex objects as defined above
        self._vertices = set()

        # This will be a list of triangle objects as defined above
        self._triangles = []

        # This is a list of edges as defined above
        self._edges = set()
        # self._edges_vertices_dict = {}
        # self._vertices_edge_dict = {}

        self._vertices_to_remove = []

        # Planar straight line graph (PSLG) dictionary
        self._pslg_dict = {'vertices':[], 'vertex_markers': [] , 'segments': [], 'segment_markers': []} #,'holes': []}

        self._triangulation = None

        self._cost_map_dict = {}

        # Vertex boundaries for sorting purposes
        self._point_min_x = 0
        self._point_max_x = 0

    def addVertex(self, vertex):

        # Check to see if an equivalent vertex exists
        for v in self._vertices:
            if v.isEqual(vertex):
                # print("equal vertex found")
                return v
        self._vertices.add(vertex)
        return vertex
        # self._pslg_dict['vertices'].append([vertex.pos()[0], vertex.pos()[1]])
        # self._pslg_dict['vertex_markers'].append(feature_index)

        # # If the vertex has an X value lower than any other vertex
        # if self._point_min_x > vertex.pos()[0] or self._point_min_x == 0:
        #     self._vertices.insert(0, vertex)
        #     self._point_min_x = vertex.pos()[0]
        #     return True

        # # If the vertex has an X value higher than any other vertex
        # elif self._point_max_x < vertex.pos()[0]:
        #     self._vertices.append(vertex)
        #     self._point_max_x = vertex.pos()[0]
        #     return True

        # # If the X value is somewhere in the middle
        # else:
        #     same_x = []
        #     for x in self._vertices:
        #         if x.pos()[0] == vertex.pos()[0]:
        #             same_x.append(x)

        #     # If no vertex has the same X value as the new vertex, find the first vertex that has a greater X value and insert the new vertex before it
        #     if len(same_x) == 0:
        #         first_greater = 0
        #         for x in self._vertices:
        #             if x.pos()[0] > vertex.pos()[0]:
        #                 first_greater = self._vertices.index(x)
        #                 break
        #         self._vertices.insert(first_greater, vertex)
        #         return True

        #     # If there's only one vertex in the graph with the same X value, compare the Y values to find which order they go in
        #     elif len(same_x) == 1:
        #         index = self._vertices.index(same_x[0])
        #         if same_x[0].pos()[1] > vertex.pos()[1]:
        #             self._vertices.insert(index - 1, vertex)
        #             return True
        #         else:
        #             self._vertices.insert(index + 1, vertex)
        #             return True

        #     # If multiple vertices have the same X value, find where the new vertex needs to go based on its Y value
        #     else:
        #         first_greater_y = 0
        #         for x in same_x:
        #             if x.pos()[1] > vertex.pos()[1]:
        #                 first_greater_y = self._vertices.index(x)
        #                 break
        #         if(first_greater_y != 0):
        #             self._vertices.insert(first_greater_y, vertex)
        #             return True
        #         else:
        #             self._vertices.insert(self._vertices.index(
        #                 same_x[len(same_x) - 1]), vertex)
        #             return True

    def addEdge(self, edge):

        # Check for an equivalent edge in the graph, add it if one doesn't exist
        if edge.a.isEqual(edge.b):
            print("A = B !!!!!!!!!!")
            return False
        for x in self._edges:
            if x.isEqual(edge):
                # print("edge already existing")
                return False
        self._edges.add(edge)
        edge.a.connect_to_vertex_with_edge(edge.b, edge)

        # self._edges_vertices_dict[edge] = [edge.a, edge.b]
        # point_a_dict = {edge.a: edge}
        # point_b_dict = {edge.b: edge}
        # if edge.a in self._vertices_edge_dict:
        #     self._vertices_edge_dict[edge.a].update(point_b_dict)
        # else:
        #     self._vertices_edge_dict[edge.a]=point_b_dict
        # if edge.b in self._vertices_edge_dict:
        #     self._vertices_edge_dict[edge.b].update(point_a_dict)
        # else:
        #     self._vertices_edge_dict[edge.b]=point_a_dict

        return True

    # Adds a triangle to the list of triangles and returns true if successful, checking if it is equal to any other triangle. Returns false if an equivalent triangle exists
    def addTriangle(self, triangle):

        # First check if an equivalent triangle already exists
        for x in self._triangles:
            if x.isEqual(triangle):
                return False

        # If not, we can add the triangle to the graph
        self._triangles.append(triangle)
        tri = [triangle.a.pos(), triangle.b.pos(), triangle._c.pos()]
        return True

    def generatePSLG(self):
        vertices = list(self._vertices)
        for vertex in vertices:
            graph._pslg_dict['vertices'].append([vertex.x,vertex.y])
            graph._pslg_dict['vertex_markers'].append(vertex.feature_marker)
        for edge in self._edges:
            if edge.is_from_feature:
                if edge.a in self._vertices and edge.b in self._vertices:
                    a_ind = vertices.index(edge.a)
                    b_ind = vertices.index(edge.b)
                # a_ind = next(i for i,v in enumerate(self._vertices) if v.isEqual(edge.a))
                # b_ind = next(i for i,v in enumerate(self._vertices) if v.isEqual(edge.b))

                    graph._pslg_dict['segments'].append((a_ind, b_ind))
                    graph._pslg_dict['segment_markers'].append(graph._pslg_dict['vertex_markers'][a_ind])
                else:
                    print("Vertices of edge not in list!!!")



    # Triangulation
    def triangulate(self):
        # self._triangulation = Delaunay(vertices)
        self._triangulation = tr.triangulate(self._pslg_dict, 'pq5D') # Uses "triangle" library

        # Add all resulting vertices
        for v in self._triangulation['vertices']:
            new_vertex = Vertex(v[0], v[1])
            graph.addVertex(new_vertex)

        # Connect all vertices
        points = self._triangulation['vertices']
        for simplex in self._triangulation['triangles']:
            for pair in itertools.combinations(simplex, 2):
                edge_vertex_a = graph.addVertex(Vertex(points[pair[0]][0], points[pair[0]][1]))
                edge_vertex_b = graph.addVertex(Vertex(points[pair[1]][0], points[pair[1]][1]))

                graph.addEdge(Edge(edge_vertex_a, edge_vertex_b))
            # graph.connect_vertices_by_simplex(simplex)

    # Connect vertices in graph based on indices
    def connect_vertices_by_simplex(self, simplex):
        for pair in itertools.combinations(simplex, 2):
            graph.addEdge(Edge(self._vertices[pair[0]], self._vertices[pair[1]]))
            # self._vertices[pair[0]].connect_to_neighbor(self._vertices[pair[1]])

    # def repair_edge_intersections(self):
    #     pass

    # def connect_and_delete(self, edges, threshold):
    #     # Create a set to store the new edges
    #     new_edges = set()
        
    #     # Iterate through all pairs of edges
    #     for i, edge1 in enumerate(edges):
    #         for edge2 in edges[i+1:]:
    #             # Check if the edges intersect
    #             intersection = get_intersection_vertex(edge1, edge2)
    #             if intersection:
    #                 # Add a new vertex at the intersection point
    #                 new_vertex = intersection
                    
    #                 # Create new edges between the intersection and the endpoints of the original edges
    #                 new_edge1 = (new_vertex, edge1[1])
    #                 new_edge2 = (new_vertex, edge2[1])
                    
    #                 # Add the new edges to the set
    #                 new_edges.add(new_edge1)
    #                 new_edges.add(new_edge2)
                    
    #                 # Check the length of new edges 
    #                 if get_length(new_edge1) < threshold:
    #                     new_edges.discard(new_edge1)
    #                 if get_length(new_edge2) < threshold:
    #                     new_edges.discard(new_edge2)
                        
    #     return new_edges

    # def trim_and_extend(self, edges, threshold):
    #     new_edges = set()
    #     intersections = set()
    #     # Iterate through all pairs of edges
    #     for i, edge1 in enumerate(edges):
    #         for edge2 in edges[i+1:]:
    #             # Check if the edges intersect
    #             intersection = get_intersection_vertex(edge1, edge2)
    #             if intersection:
    #                 intersections.add((edge1, edge2, intersection))
    #     for edge1, edge2, intersection in intersections:
    #         new_edge1 = (edge1[0], intersection)
    #         new_edge2 = (intersection, edge1[1])
    #         new_edge3 = (edge2[0], intersection)
    #         new_edge4 = (intersection, edge2[1])
    #         if get_length(new_edge1) < threshold:
    #             new_edges.add(new_edge2)
    #         else:
    #             new_edges.add(new_edge1)
    #         if get_length(new_edge3) < threshold:
    #             new_edges.add(new_edge4)
    #         else:
    #             new_edges.add(new_edge3)
    #     for edge in edges:
    #         if not any(edge in x for x in intersections):
    #             new_edges.add(edge)
    #     return new_edges

    
    def clear_duplicates(self):
        num_rem_edges = 0
        num_rem_vertices = 0
        vertices = copy.copy(self._vertices) # A set needs to stay the same size while you iterate through it
        edges = copy.copy(self._edges)
        for edge in self._edges:
            # Remove edge if it is defined by a single point
            if edge.a.isEqual(edge.b):
                edges.discard(edge)
                num_rem_edges+=1
                continue
            # # Add vertex if not in vertex list
            # if not edge.a in vertices:
            #     vertices.addVertex(edge.a)
            # if not edge.b in vertices:
            #     vertices.addVertex(edge.b)
            
            for other_edge in self._edges:
                if edge == other_edge:
                    continue
                # Remove edge if it is already existing
                if edge.isEqual(other_edge):
                    edges.discard(edge)
                    num_rem_edges+=1

        for vertex in self._vertices:
            for other_vertex in self._vertices:
                if vertex == other_vertex:
                    continue
                if vertex.isEqual(other_vertex):
                    vertices.discard(other_vertex)
                    for edge in edges:
                        if edge.a.isEqual(other_vertex):
                            edge.a = vertex
                        elif edge.b.isEqual(other_vertex):
                            edge.b = vertex

                    num_rem_vertices+=1
        self._vertices = vertices
        self._edges = edges
        print("number of remaining edges: ", len(self._edges))
        print("removed ", num_rem_edges, " edges and ", num_rem_vertices, " vertices")
            

    def repair_mismatches(self, threshold):
        new_graph = copy.deepcopy(self)
        edges_were_updated = False 
        for edge in new_graph._edges:
            for other_edge in new_graph._edges:
                if edge.a.isEqual(edge.b) or edge.isEqual(other_edge) or edge.shares_vertex_with(other_edge):
                    continue

                # Check if the pair of edges intersects
                intersection = edge.get_intersection_vertex(other_edge)
                if intersection:
                    print("Intersection!")
                    if edge.a.getMetricLengthTo(intersection) < threshold and len(edge.a.edges_dict.keys()) ==1:
                        print("cutting edge A")
                        if other_edge.a.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.a,  other_edge.a)
                        if other_edge.b.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.a,  other_edge.b)
                        else:
                            new_graph.replace_edge_vertex(edge, edge.a,  intersection)
                            new_graph.split_edge( other_edge, intersection)
                            edges_were_updated = True
                    if edge.b.getMetricLengthTo(intersection) < threshold and len(edge.b.edges_dict.keys()) ==1:
                        print("cutting edge B")
                        if other_edge.a.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.b,  other_edge.a)
                        if other_edge.b.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.b,  other_edge.b)
                        else:
                            new_graph.replace_edge_vertex(edge, edge.b,  intersection)
                            new_graph.split_edge( other_edge, intersection)
                            edges_were_updated = True
                    if other_edge.a.getMetricLengthTo(intersection) < threshold and len(other_edge.a.edges_dict.keys()) ==1:
                        print("cutting other edge A")
                        if edge.a.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(other_edge, other_edge.a,  edge.a)
                        if edge.b.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(other_edge, other_edge.a,  edge.b)
                        else:
                            new_graph.replace_edge_vertex(other_edge, other_edge.a,  intersection)
                            new_graph.split_edge( edge, intersection)
                            edges_were_updated = True
                    if other_edge.b.getMetricLengthTo(intersection) < threshold and len(other_edge.b.edges_dict.keys()) ==1:
                        print("cutting  other edge B")
                        if edge.a.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(other_edge, other_edge.b,  edge.a)
                        if edge.b.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(other_edge, other_edge.b,  edge.b)
                        else:
                            new_graph.replace_edge_vertex(other_edge, other_edge.b,  intersection)
                            new_graph.split_edge( edge, intersection)
                            edges_were_updated = True
                    else:
                        print("Splitting both edges")
                        new_graph.split_edge( edge, intersection)
                        new_graph.split_edge( other_edge, intersection)
                        edges_were_updated = True
                    break

                else:
                    # check if the extension of the start endpoint causes an intersection
                    extension_vertex = edge.create_vertex_at_metric_distance(edge.b, edge.a, threshold)
                    extended_edge = Edge(edge.b, extension_vertex)
                    intersection = other_edge.get_intersection_vertex(Edge(edge.b, extension_vertex))
                    if intersection:
                        print("There's a start extension intersection...")
                        if other_edge.a.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.a,  other_edge.a)
                        if other_edge.b.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.a,  other_edge.b)
                        else:
                            new_graph.replace_edge_vertex(edge, edge.a,  intersection)
                            new_graph.split_edge(other_edge, intersection)
                            edges_were_updated = True
                        break
                    # check if the extension of the end endpoint causes an intersection
                    extension_vertex = edge.create_vertex_at_metric_distance(edge.a, edge.b, threshold)
                    extended_edge = Edge(edge.a, extension_vertex)
                    intersection = other_edge.get_intersection_vertex(extended_edge)
                    if intersection:
                        print("There's an end extension intersection...")
                        if other_edge.a.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.b,  other_edge.a)
                        if other_edge.b.getMetricLengthTo(intersection) < threshold:
                            new_graph.replace_edge_vertex(edge, edge.b,  other_edge.b)
                        else:
                            new_graph.replace_edge_vertex(edge, edge.b,  intersection)
                            new_graph.split_edge(other_edge, intersection)
                            edges_were_updated = True
                        break
            if edges_were_updated:
                break
        if edges_were_updated:
            return new_graph.repair_mismatches(threshold)
        else: 
            return new_graph

    def discard_vertices(self,vertex_list):
        for vertex in vertex_list:
            self._vertices.discard(vertex)
            neighbours = list(vertex.edges_dict.keys())
            for neighbour in neighbours:
                vertex.disconnect_from_vertex(neighbour)
    
    def discard_edges(self,edge_list):
        for edge in edge_list:
            self._edges.discard(edge)
            edge.a.disconnect_from_vertex(edge.b)


    def repair(self,threshold):
        cnt = 0
        vertices_to_remove = []
        edges_were_updated = True # to enter the loop
        while edges_were_updated and cnt <500 : # As long as new edges were added to self._edges
            cnt+=1
            print("                          recursion nr: ", cnt)
            edges = self._edges
            edges_were_updated = False 
            for edge in edges:
                if not edge in self._edges or edge.a.isEqual(edge.b):
                    continue
                # if edge.getMetricLength() < threshold:
                #     self.discard_vertices([edge.a, edge.b])
                #     self.discard_edges([edge])

                #     continue
                for other_edge in edges:
                    if not other_edge in self._edges or edge.isEqual(other_edge) or edge.shares_vertex_with(other_edge):
                        continue

                    # Check if the pair of edges intersects
                    intersection = edge.get_intersection_vertex(other_edge)
                    if intersection:
                        print("Intersection!")
                        if edge.a.getMetricLengthTo(intersection) < threshold and len(edge.a.edges_dict.keys()) ==1:
                            print("cutting edge A")
                            if other_edge.a.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.a,  other_edge.a)
                            if other_edge.b.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.a,  other_edge.b)
                            else:
                                edges_were_updated = True
                                if edge.b.getMetricLengthTo(intersection) > threshold:
                                    self.replace_edge_vertex(edge, edge.a,  intersection)
                                    self.split_edge( other_edge, intersection)
                                else: 
                                    self._edges.discard(edge)
                                    continue
                        if edge.b.getMetricLengthTo(intersection) < threshold and len(edge.b.edges_dict.keys()) ==1:
                            print("cutting edge B")
                            if other_edge.a.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.b,  other_edge.a)
                            if other_edge.b.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.b,  other_edge.b)
                            else:
                                edges_were_updated = True
                                if edge.a.getMetricLengthTo(intersection) > threshold:
                                    self.replace_edge_vertex(edge, edge.b,  intersection)
                                    self.split_edge( other_edge, intersection)
                                else: 
                                    self._edges.discard(edge)
                                    continue
                                
                        if other_edge.a.getMetricLengthTo(intersection) < threshold and len(other_edge.a.edges_dict.keys()) ==1:
                            print("cutting other edge A")
                            if edge.a.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(other_edge, other_edge.a,  edge.a)
                            if edge.b.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(other_edge, other_edge.a,  edge.b)
                            else:
                                edges_were_updated = True
                                if other_edge.b.getMetricLengthTo(intersection) > threshold:
                                    self.replace_edge_vertex(other_edge, other_edge.a,  intersection)
                                    self.split_edge( edge, intersection)
                                else: 
                                    self._edges.discard(edge)
                                    continue
                        if other_edge.b.getMetricLengthTo(intersection) < threshold and len(other_edge.b.edges_dict.keys()) ==1:
                            print("cutting  other edge B")
                            if edge.a.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(other_edge, other_edge.b,  edge.a)
                            if edge.b.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(other_edge, other_edge.b,  edge.b)
                            else:
                                edges_were_updated = True
                                if other_edge.a.getMetricLengthTo(intersection) > threshold:
                                    self.replace_edge_vertex(other_edge, other_edge.b,  intersection)
                                    self.split_edge( edge, intersection)
                                else: 
                                    self._edges.discard(edge)
                                    continue
                        else:
                            print("Splitting both edges")
                            self.split_edge( edge, intersection)
                            self.split_edge( other_edge, intersection)
                            edges_were_updated = True
                        break

                    else:
                        # check if the extension of the start endpoint causes an intersection
                        extension_vertex = edge.create_vertex_at_metric_distance(edge.b, edge.a, threshold)
                        extended_edge = Edge(edge.b, extension_vertex)
                        intersection = other_edge.get_intersection_vertex(Edge(edge.b, extension_vertex))
                        if intersection:
                            print("There's a start extension intersection...")
                            if other_edge.a.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.a,  other_edge.a)
                            if other_edge.b.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.a,  other_edge.b)
                            else:
                                self.replace_edge_vertex(edge, edge.a,  intersection)
                                self.split_edge(other_edge, intersection)
                                edges_were_updated = True
                            break
                        # check if the extension of the end endpoint causes an intersection
                        extension_vertex = edge.create_vertex_at_metric_distance(edge.a, edge.b, threshold)
                        extended_edge = Edge(edge.a, extension_vertex)
                        intersection = other_edge.get_intersection_vertex(extended_edge)
                        if intersection:
                            print("There's an end extension intersection...")
                            if other_edge.a.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.b,  other_edge.a)
                            if other_edge.b.getMetricLengthTo(intersection) < threshold:
                                self.replace_edge_vertex(edge, edge.b,  other_edge.b)
                            else:
                                self.replace_edge_vertex(edge, edge.b,  intersection)
                                self.split_edge(other_edge, intersection)
                                edges_were_updated = True
                            break
                if edges_were_updated:
                    break
        # for vertex in graph._vertices:
        #     if len(vertex.edges_dict.keys()) == 0:
        #         graph._vertices_to_remove.append(vertex)
        print("Vertices to be removed: ", graph._vertices_to_remove)
        # graph.discard_vertices(graph._vertices_to_remove)

        return True

    # Function to split the edge in two edges given a vertex on the original edge
    def split_edge(self,  edge, split_vertex):
        if split_vertex.isEqual(edge.a) or split_vertex.isEqual(edge.b):
            # print("split point is actually an endpoint ------------")
            return False
        else:
            edge_b_vertex_copy = copy.deepcopy(edge.b)
            # edge_b_vertex_pos = edge.b.pos() # = self.addVertex(split_vertex)
            self.replace_edge_vertex(edge, edge.b, split_vertex) # Edge_b is replaced by th split vertex

            edge_b_vertex = self.addVertex(edge_b_vertex_copy) #Vertex(edge_b_vertex_pos[0], edge_b_vertex_pos[1])
            other_edge = Edge(split_vertex , edge_b_vertex)
            other_edge.isFromFeature(edge.is_from_feature)
            self.addEdge(other_edge)
            
        return True
    
    # Function to replace a vertex on an edge
    def replace_edge_vertex(self, edge, vertex_to_replace, new_vertex):
        # Only remove the vertex to replace if it is not connected to other vertices !
        if len(vertex_to_replace.edges_dict.keys()) <=1:
            self._vertices_to_remove.append(vertex_to_replace)
        #  Update point A
        if vertex_to_replace.isEqual(edge.a):
            edge.a = self.addVertex(new_vertex)
            print("Start point UPDATED ------")
        # Update point B
        elif vertex_to_replace.isEqual(edge.b):
            edge.b = self.addVertex(new_vertex)
            print("End point UPDATED ------")
        else:
            return False      
        return True


    
    
    # Tests if a given triangle is Delaunay (i.e., no other vertices lie within the circumcircle of the triangle)
    def triangleIsDelaunay(self, triangle):
        tri = [triangle.a.pos(), triangle.b.pos(), triangle._c.pos()]
        cc = circumcircle(tri)
        for x in self._vertices:
            # print(x.pos())
            # If we get the divide-by-zero error, we assume the triangle is non-Delaunay
            if not (x.isEqual(triangle.a) and x.isEqual(triangle.b) and x.isEqual(triangle._c)):
                try:
                    if pointInCircle(x.pos(), cc):
                        return False
                except:
                    return False
        # self._circles.append(cc)
        return True

    # Generates the complete Delaunay mesh by testing every possible triangle for the Delaunay condition, then marking any edges that intersect, and removing the longer of the intersecting edges
    def generateDelaunayMesh(self):

        # Create every possible triangle and test it for the Delaunay condition
        for p1 in self._vertices:
            for p2 in self._vertices:
                for p3 in self._vertices:
                    if not p1.isEqual(p2) and not p2.isEqual(p3) and not p3.isEqual(p1):
                        test_tri = Triangle(p1, p2, p3)
                        if self.triangleIsDelaunay(test_tri):
                            self.addTriangle(test_tri)

        # One more check for the Delaunay condition (probably redundant) and then adding the edges of the triangle to the graph
        for t in self._triangles:
            if not self.triangleIsDelaunay(t):
                self._triangles.remove(t)
            else:
                self.addEdge(Edge(t.a, t.b))
                self.addEdge(Edge(t.b, t._c))
                self.addEdge(Edge(t._c, t.a))

        # Checking for intersecting edges
        bad_edges = []
        for e1 in self._edges:
            for e2 in self._edges:
                if not e1.isEqual(e2):
                    if e1.edgeIntersection(e2):
                        len_e1 = e1.length()
                        len_e2 = e2.length()
                        if len_e1 >= len_e2:
                            bad_edges.append(e1)

                        else:
                            bad_edges.append(e2)
                        # if (not e1.is_from_feature and not e2.is_from_feature):
                        #     len_e1 = e1.length()
                        #     len_e2 = e2.length()
                        #     if len_e1 >= len_e2:
                        #         bad_edges.append(e1)

                        #     else:
                        #         bad_edges.append(e2)
                        # else:
                        #     if (e1.is_from_feature and not e2.is_from_feature):
                        #         bad_edges.append(e2)
                        #     elif (e2.is_from_feature and not e1.is_from_feature):
                        #         bad_edges.append(e1)

        # Removing any bad (intersecting) edges from the graph
        for x in bad_edges:
            for y in self._edges:
                if x.isEqual(y):
                    self._edges.discard(y)
                    continue
        for simplex in self._triangulation.simplices:
            graph.connect_vertices_by_simplex(simplex)

# Function for determining the circumcircle of any three vertices


def circumcircle(tri):
    try:
        D = ((tri[0][0] - tri[2][0]) * (tri[1][1] - tri[2][1]) -
             (tri[1][0] - tri[2][0]) * (tri[0][1] - tri[2][1]))

        center_x = (((tri[0][0] - tri[2][0]) * (tri[0][0] + tri[2][0]) + (tri[0][1] - tri[2][1]) * (tri[0][1] + tri[2][1])) / 2 * (tri[1][1] - tri[2][1]) -
                    ((tri[1][0] - tri[2][0]) * (tri[1][0] + tri[2][0]) + (tri[1][1] - tri[2][1]) * (tri[1][1] + tri[2][1])) / 2 * (tri[0][1] - tri[2][1])) / D

        center_y = (((tri[1][0] - tri[2][0]) * (tri[1][0] + tri[2][0]) + (tri[1][1] - tri[2][1]) * (tri[1][1] + tri[2][1])) / 2 * (tri[0][0] - tri[2][0]) -
                    ((tri[0][0] - tri[2][0]) * (tri[0][0] + tri[2][0]) + (tri[0][1] - tri[2][1]) * (tri[0][1] + tri[2][1])) / 2 * (tri[1][0] - tri[2][0])) / D

        radius = math.sqrt((tri[2][0] - center_x) **
                           2 + (tri[2][1] - center_y)**2)

        return [[center_x, center_y], radius]
    except:
        print("Divide By Zero error")
        print(tri)


# Determine if any given vertex lies inside a circle
def pointInCircle(vertex, circle):
    # This is pretty simple; just find the distance between the vertex and the center. If it's less than or equal to the radius, the vertex is inside the circle

    d = math.sqrt(math.pow(vertex[0] - circle[0][0],
                  2) + math.pow(vertex[1] - circle[0][1], 2))
    if d < circle[1]:
        return True
    else:
        return False



def dijkstra(graph, start, goal, visited=[], cost_dict={}, predecessors={}):
    """Find the shortest path between start and goal nodes in a graph"""
    # we've found our goal node, now find the path to it, and return
    # print("start vertex:")
    # print(start)
    if start == goal:
        path = []
        while goal != None:
            path.append(goal)
            goal = predecessors.get(goal, None)
        return cost_dict[start], path[::-1]
    # detect if it's the first time through, set current distance to zero
    if not visited:
        cost_dict[start] = 0
    # process neighbors as per algorithm, keep track of predecessors
    for neighbor in start.edges_dict.keys(): # _vertices_edge_dict[start].keys():
        if neighbor not in visited:
            neighbor_cost = cost_dict.get(neighbor, sys.maxsize)
            # print(start.edges_dict)
            # print(neighbor)

            edge = start.edges_dict[neighbor]
            # heuristic_cost = latlon_to_meters_dist(neighbor.x,goal.x,neighbor.y ,goal.y)
            tentative_cost = cost_dict[start] + edge.cost# + heuristic_cost

            if tentative_cost < neighbor_cost:
                cost_dict[neighbor] = tentative_cost
                predecessors[neighbor] = start
    
    # neighbors processed, now mark the current node as visited
    visited.append(start)
    # finds the closest unvisited node to the start
    unvisiteds = dict((v, cost_dict.get(v, sys.maxsize))
                      for v in graph._vertices if v not in visited)
    closestnode = min(unvisiteds, key=unvisiteds.get)
    # now we can take the closest node and recurse, making it current
    return dijkstra(graph, closestnode, goal, visited, cost_dict, predecessors)


# Disable
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore
def enablePrint():
    sys.stdout = sys.__stdout__


if __name__ == "__main__":

    sys.setrecursionlimit(10000)
    blockPrint()

    
    # To compute the running time
    import time
    start_total = time.time()

    graph = Graph()

    print("Reading Geojson files...")
    # gdf = gpd.read_file("/home/alexandre/rma/imugs/local_projects/mapf/centralized/cbs/map/geojson/road_clipped.geojson", driver='GeoJSON')
    # print("Plotting...")
    # ax = gdf.plot(figsize=(10, 10), alpha=0.5, edgecolor='k')
    # ax.set_axis_off()
    # cx.add_basemap(ax, source=cx.providers.OpenStreetMap.HOT)
    # plt.show()
    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    rel_path = "map/geojson/roads.geojson"
    abs_file_path = os.path.join(script_dir, rel_path)

    with open(abs_file_path) as jsonfile:
        data = json.load(jsonfile)
    features = data['features'] 

    for f_index, feature in enumerate(features):
        if (feature['geometry']['type'] == 'LineString' ):
            for i, coordinate in enumerate(feature['geometry']['coordinates']):
                new_vertex = Vertex(coordinate[0], coordinate[1])
                new_vertex.feature_marker = f_index
                current_vertex = graph.addVertex(new_vertex)
                if i!=0:
                    feature_edge = Edge(previous_vertex , current_vertex)
                    feature_edge.isFromFeature(True) # Makes this edge a constraint for triangulation 
                    graph.addEdge(feature_edge)
                previous_vertex = current_vertex
        elif (feature['geometry']['type'] == 'Polygon'):
            for i, coordinate in enumerate(feature['geometry']['coordinates'][0]):
                new_vertex = Vertex(coordinate[0], coordinate[1])
                new_vertex.feature_marker = f_index
                current_vertex = graph.addVertex(new_vertex)
                if i!=0:
                    feature_edge = Edge(previous_vertex , current_vertex)
                    feature_edge.isFromFeature(True) # Makes this edge a constraint for triangulation 
                    graph.addEdge(feature_edge)
                previous_vertex = current_vertex
        # elif (feature['geometry']['type'] == 'MultiLineString'):
        #     for coordinate_list in feature['geometry']['coordinates']:
        #         for coordinate in coordinate_list:
        #             graph.addVertex(Vertex(coordinate[0], coordinate[1]))
    
    # graph.generatePSLG()
    # graph2 = copy.deepcopy(graph)


    # start_repair = time.time()
    # # graph.clear_duplicates()
    graph.repair(2)

    enablePrint()

    # end_repair = time.time()
    # print('Repair time : %s seconds' % float(end_repair-start_repair))

    
    graph.generatePSLG()
    # print(graph._pslg_dict)
    # print(len(graph._pslg_dict['vertices']), len(graph._pslg_dict['segments']))

    tr.plot(plt.axes(), **graph._pslg_dict)
    plt.show()


    
    # B = tr.triangulate(graph._pslg_dict, 'p10')
    # tr.compare(plt, graph._pslg_dict, B)
    # plt.show()
  

    # # # Add uniform distribution random vertices
    # # # random.seed(1)
    # # # for x in range(0, 1000):
    # # #     while graph.addVertex(Vertex(random.uniform(12.800964, 12.808976), random.uniform(52.21507, 52.22061))) is False:
    # # #         print("Couldn't add vertex")
    

    print("Generating Delaunay Mesh...")
    # graph.generateDelaunayMesh()
    start_triangulation = time.time()

    # # # A = dict(vertices=np.array(((0, 0), (1, 0), (1, 1), (0, 1))))
    # # # B = tr.triangulate(A, 'qa0.1')
    # # # print(A)
    # # # tr.compare(plt, A, B)
    # # # plt.show()
    
    # # # face = tr.get_data('face')
    # # # print(face)
    # # # t = tr.triangulate(graph._ver, 'pq0D')
    # # # tr.plot(plt.axes(), **t)

    # # # plt.show()

    
    graph.triangulate()

    # end_triangulation = time.time()
    # print('Triangulation time : %s seconds' % float(end_triangulation-start_triangulation))



    start_dijkstra = time.time()

    vertices = list(graph._vertices)
    start_vertex = random.choice(vertices)
    end_vertex = random.choice(vertices)

    start_ind = random.randint(1, len(graph._vertices))
    end_ind = random.randint(1, len(graph._vertices))
    print(start_ind, end_ind)

    dijkstra_result = dijkstra(graph, start_vertex, end_vertex)
    path = dijkstra_result[1]
    print('Path length : %s degrees' % float(dijkstra_result[0]))

    end_dijkstra = time.time()
    print('Dijkstra time : %s seconds' % float(end_dijkstra-start_dijkstra))


    end_total = time.time()
    print('Total running time : %s seconds' % float(end_total-start_total))

    # print("Plotting resulting mesh...")
    # # plt.triplot(vertices[:,0], vertices[:,1], tri.simplices)
    # plt.plot(vertices[:,0], vertices[:,1], 'o')
    # plt.show()

    # Plot Edges
    for e in graph._edges:
        if not e.is_from_feature:
            # Generated edges
            plt.plot([e.a.pos()[0], e.b.pos()[0]], [
                    e.a.pos()[1], e.b.pos()[1]], '-', c='0.75')
    for e in graph._edges:
        if e.is_from_feature:
            # Environment features
            plt.plot([e.a.pos()[0], e.b.pos()[0]], [
                    e.a.pos()[1], e.b.pos()[1]], '-', c='0.1', linewidth=3)

    # # Show connections between vertices (all neighbors)
    # for v in graph._vertices:
    #     for n in v.edges_dict.keys():
    #         plt.plot([v.pos()[0], n.pos()[0]], [
    #                 v.pos()[1], n.pos()[1]], 'r:')

    # Show Dijkstra result
    for v in graph._vertices:
        plt.plot(v.pos()[0], v.pos()[1], '.', c='0.5')
    plt.plot(start_vertex.pos()[0], start_vertex.pos()[1], 'ro')
    plt.plot(end_vertex.pos()[0], end_vertex.pos()[1], 'ro')
    for i, v in enumerate(path):
        if i > 0:
            plt.plot([previous_vertex.pos()[0], v.pos()[0]], [
                    previous_vertex.pos()[1], v.pos()[1]], 'r:', linewidth=2)
        previous_vertex = v

    # plt.legend()
    plt.show()
