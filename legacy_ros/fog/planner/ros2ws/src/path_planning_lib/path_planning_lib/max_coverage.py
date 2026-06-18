from shapely.geometry import Polygon, LineString, Point
from scipy.spatial import distance_matrix
from gurobipy import Model, GRB, quicksum

class MaximizeCoverage:
    def __init__(self, graph):
        """
        Initialize the MaximizeCoverage class with a graph.
        
        :param graph: A networkx graph containing nodes with x, y coordinates.
        """
        self.graph = graph

    def get_nodes_inside_geometry(self, geometry_type, coordinates):
        """
        Extracts graph nodes that fall inside a given Polygon or LineString.

        :param geometry_type: "Polygon" or "LineString"
        :param coordinates: The list of coordinate points defining the geometry.
        :return: List of node IDs that fall inside the geometry.
        """
        if geometry_type == "Polygon":
            # Flatten coordinates list if nested
            if isinstance(coordinates[0], list):
                coordinates = coordinates[0]  # Extract actual points

            polygon = Polygon(coordinates)

        elif geometry_type == "LineString":
            line = LineString(coordinates)

        else:
            raise ValueError(f"Unsupported geometry type: {geometry_type}")

        # Check which graph nodes fall inside the geometry
        inside_nodes = []
        for node_id in self.graph.nodes:
            node_x, node_y = self.graph.nodes[node_id]["x"], self.graph.nodes[node_id]["y"]
            node_point = Point(node_x, node_y)

            if geometry_type == "Polygon" and polygon.contains(node_point):
                inside_nodes.append(node_id)
            elif geometry_type == "LineString" and line.distance(node_point) < 1e-6:  # Threshold for inclusion
                inside_nodes.append(node_id)

        return inside_nodes

    def solve_mclp(self, candidate_nodes, K):
        """
        Solve the Maximum Covering Location Problem (MCLP) to determine optimal node placements.

        :param candidate_nodes: List of node IDs that can be used as potential coverage sites.
        :param K: Number of agents (coverage locations to select).
        :return: List of selected coordinates [(x1, y1), (x2, y2), ...].
        """
        if len(candidate_nodes) <= K:
            return [(self.graph.nodes[node]["x"], self.graph.nodes[node]["y"]) for node in candidate_nodes]

        # Extract node coordinates
        node_coords = [(self.graph.nodes[node]["x"], self.graph.nodes[node]["y"]) for node in candidate_nodes]
        num_nodes = len(node_coords)

        # Compute pairwise distances
        D = distance_matrix(node_coords, node_coords)

        # Set coverage radius (heuristic: average node distance)
        radius = D.mean()

        # Convert distance matrix into a binary coverage matrix (1 if within radius, 0 otherwise)
        coverage_matrix = (D <= radius).astype(int)

        # Create Gurobi Model
        m = Model()
        x = {j: m.addVar(vtype=GRB.BINARY, name=f"x{j}") for j in range(num_nodes)}
        y = {i: m.addVar(vtype=GRB.BINARY, name=f"y{i}") for i in range(num_nodes)}

        # Constraint: Select exactly K sites
        m.addConstr(quicksum(x[j] for j in range(num_nodes)) == K)

        # Constraint: Each node should be covered by at least one selected site
        for i in range(num_nodes):
            m.addConstr(quicksum(x[j] for j in range(num_nodes) if coverage_matrix[i, j]) >= y[i])

        # Objective: Maximize total coverage
        m.setObjective(quicksum(y[i] for i in range(num_nodes)), GRB.MAXIMIZE)
        m.setParam("OutputFlag", 0)
        m.optimize()

        # Extract solution
        selected_coords = [node_coords[j] for j in range(num_nodes) if x[j].x > 0.5]
        return selected_coords  # Now returns coordinates instead of node IDs


    # def coverage_algorithm(self, geometry_type, coordinates, K):
    #     """
    #     Compute K optimal coverage points inside the given geometry.

    #     :param geometry_type: "Polygon" or "LineString".
    #     :param coordinates: Coordinates defining the geometry.
    #     :param K: Number of coverage points to find.
    #     :return: List of selected node IDs.
    #     """
    #     candidate_nodes = self.get_nodes_inside_geometry(geometry_type, coordinates)
    #     if not candidate_nodes:
    #         return []  # No valid nodes found in the geometry

    #     return self.solve_mclp(candidate_nodes, K)
