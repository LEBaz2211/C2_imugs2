# sources :
# https://github.com/cyang-kth/maximum-coverage-location/blob/master/README.md
# https://stackoverflow.com/questions/49211126/efficiently-sample-from-arbitrary-multivariate-function


from math import sqrt
import numpy as np
from scipy.spatial import distance_matrix
from gurobipy import *
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, Point
from numpy import random

from matplotlib import pyplot as plt

from functools import partial
import pylab
import matplotlib.pyplot as plt

import pandas as pd


# Generate a density function from the cost graph
def generate_pdf_from_cost_graph(cost_graph):
    map_size = np.size(cost_graph,0)
    # probability density function
    cost_pdf = cost_graph/np.sum(cost_graph)  
    # give higher probability to lower cost
    weighted_graph = np.ones(map_size)/(map_size**2) - cost_pdf
    PDF = weighted_graph/np.sum(weighted_graph)
    return PDF


def get_density(z, PDF):
    z = np.around(z)
    return 10*PDF[int(z[0, 0]), int(z[0, 1])]


def metropolis_hastings(PDF):
    map_size = np.size(PDF,0)
    size=map_size**2
    burnin_size = map_size
    size += burnin_size
    x0 = np.array([[0, 0]])
    xt = x0
    samples = []
    for i in range(size):
        # xt_candidate = np.array([np.random.multivariate_normal(xt[0], np.eye(2))])
        xy_min = [0, 0]
        xy_max = [31, 31]
        xt_candidate = np.random.uniform(low=xy_min, high=xy_max, size=(1, 2))
        accept_prob = (get_density(xt_candidate, PDF))/(get_density(xt, PDF))
        if np.random.uniform(0, 1) < accept_prob:
            xt = xt_candidate
        samples.append(xt)

    samples = np.array(samples[burnin_size:])
    samples = np.reshape(samples, [samples.shape[0], 2])
    return samples



def generate_candidate_sites(points, obstacles, M=100 ):
    '''
    Generate M candidate sites with the convex hull of a point set
    Input:
        points: a Numpy array with shape of (N,2)
        M: the number of candidate sites to generate
    Return:
        sites: a Numpy array with shape of (M,2)
    '''
    hull = ConvexHull(points)
    polygon_points = points[hull.vertices]
    poly = Polygon(polygon_points)
    min_x, min_y, max_x, max_y = poly.bounds
    sites = []
    while len(sites) < M:
        random_point = Point([random.uniform(min_x, max_x),
                             random.uniform(min_y, max_y)])
        # point = np.around(random_point)
        point = np.around(np.array((random_point.xy[0][0], random_point.xy[1][0])))

        if (random_point.within(poly) and (point[1],point[0]) not in obstacles):
            # print(point)
            sites.append(random_point)
    candidate_sites = np.array([(p.x, p.y) for p in sites])
    return np.around(candidate_sites)


def mclp(points, K, radius, obstacles):
    """
    Solve maximum covering location problem
    Input:
        points: input points, Numpy array in shape of [N,2]
        K: the number of sites to select
        radius: the radius of circle
        M: the number of candidate sites, which will randomly generated inside
        the ConvexHull wrapped by the polygon
    Return:
        opt_locations: locations K optimal sites, Numpy array in shape of [K,2]
        f: the optimal value of the objective function
    """
    # Candidate site size (random sites generated)
    M = 10*K

    
    sites = generate_candidate_sites(points, obstacles, M)
    J = sites.shape[0]
    I = points.shape[0]
    D = distance_matrix(points, sites)
    mask1 = D <= radius
    D[mask1] = 1
    D[~mask1] = 0
    # Build model
    m = Model()
    # Add variables
    x = {}
    y = {}
    for i in range(I):
        y[i] = m.addVar(vtype=GRB.BINARY, name="y%d" % i)
    for j in range(J):
        x[j] = m.addVar(vtype=GRB.BINARY, name="x%d" % j)

    m.update()
    # Add constraints
    m.addConstr(quicksum(x[j] for j in range(J)) == K)

    for i in range(I):
        m.addConstr(quicksum(x[j] for j in np.where(D[i] == 1)[0]) >= y[i])
    


    m.setObjective(quicksum(y[i]for i in range(I)), GRB.MAXIMIZE)
    m.setParam('OutputFlag', 0)
    m.optimize()


    solution = []
    if m.status == GRB.Status.OPTIMAL:
        for v in m.getVars():
            if v.x == 1 and v.varName[0] == "x":
                solution.append(int(v.varName[1:]))
    opt_locations = sites[solution]
    return opt_locations, m.objVal



def get_max_coverage_locations(cost_graph, K, obstacles):
    map_size = np.size(cost_graph, 0)
    PDF = generate_pdf_from_cost_graph(cost_graph)
    # Service radius of each agent
    radius = map_size/(2*sqrt(K))

    # Generate samples according to weighted graph
    points = metropolis_hastings(PDF)

    # Run mclp
    # opt_locations is the location of optimal sites
    # f is the number of points covered
    opt_locations, f = mclp(points, K, radius, obstacles)
    # Plot results 
    fig, axis = plt.subplots(figsize=(6, 5))
    heatmap = axis.pcolor(cost_graph, cmap=plt.cm.Reds)
    plt.colorbar(heatmap)
    plt.title("Maximum Coverage Location")
    #plt.scatter(points[:, 1], points[:, 0], c='C0')
    plt.plot(opt_locations[:, 1], opt_locations[:, 0], 'x', color = 'green')
    for site in opt_locations:
            circle = plt.Circle(np.flip(site,0), radius, color='C1', fill=False, lw=2)
            axis.add_artist(circle)
    plt.savefig('results/images/max_coverage_locations.png')
    return np.around(opt_locations)

###########################################################

# cost_graph = np.load('cost_weighted_graph.npy')
# K = 10 # Number of agents


# opt_locations = get_max_coverage_locations(cost_graph, K)


# # Plot results 
# fig, axis = plt.subplots(figsize=(6, 5))
# heatmap = axis.pcolor(cost_graph, cmap=plt.cm.Reds)
# plt.colorbar(heatmap)
# plt.title("Maximum Coverage Location")
# #plt.scatter(points[:, 1], points[:, 0], c='C0')
# plt.plot(opt_locations[:, 1], opt_locations[:, 0], 'x', color = 'green')
# # for site in opt_locations:
# #         circle = plt.Circle(np.flip(site,0), radius, color='C1', fill=False, lw=2)
# #         axis.add_artist(circle)
# plt.show()
