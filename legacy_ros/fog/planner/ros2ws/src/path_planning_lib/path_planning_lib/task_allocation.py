import numpy as np
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
import networkx as nx
from ortools.constraint_solver import routing_enums_pb2, pywrapcp


class TaskAllocator:
    def __init__(self, distance_mode="euclidean", graph=None):
        """
        Initialize the task allocator.

        :param distance_mode: "euclidean" or "graph" to determine cost computation method.
        :param graph: NetworkX graph for shortest path computation (required for graph mode).
        """
        self.distance_mode = distance_mode
        self.graph = graph  # Graph used for path-based allocation

    def compute_cost_matrix(self, agents, points):
        """
        Compute the cost matrix based on the selected distance mode.

        :param agents: Dictionary {agent_id: agent_object}.
        :param points: List of point coordinates [(x, y), (x, y), ...].
        :return: Cost matrix (NumPy array), Ordered agent IDs, Ordered task coordinates.
        """
        agent_positions = [(agent.localization[0], agent.localization[1]) for agent in agents]

        if not agent_positions or not points:
            return None, []

        if self.distance_mode == "euclidean":
            cost_matrix = cdist(agent_positions, points, metric="euclidean")
        elif self.distance_mode == "graph":
            if not self.graph:
                raise ValueError("Graph is required for path-based allocation.")

            cost_matrix = np.zeros((len(agent_positions), len(points)))
            for i, agent in enumerate(agent_positions):
                for j, task in enumerate(points):
                    try:
                        cost_matrix[i, j] = nx.shortest_path_length(
                            self.graph, tuple(agent), tuple(task), weight="weight"
                        )
                    except nx.NetworkXNoPath:
                        cost_matrix[i, j] = np.inf  # No valid path
        else:
            raise ValueError("Unsupported distance mode. Choose 'euclidean' or 'graph'.")

        return cost_matrix, points

    def hungarian_allocation(self, agents, points):
        """
        Solve the task allocation problem optimally using the Hungarian algorithm.

        :param agents: Dictionary {agent_id: agent_object}.
        :param points: List of point coordinates [(x, y), (x, y), ...].
        :return: Dictionary {agent_id: [task]}
        """
        cost_matrix, destination_positions = self.compute_cost_matrix(agents, points)

        agent_ids = [agent.agent_id for agent in agents]

        if cost_matrix is None:
            return {}

        agent_indices, dest_indices = linear_sum_assignment(cost_matrix)

        allocation = {agent_id: [] for agent_id in agent_ids}
        for a_idx, t_idx in zip(agent_indices, dest_indices):
            allocation[agent_ids[a_idx]].append(destination_positions[t_idx])

        return allocation

    def solve_mtsp(self, agents, points):
        """
        Solve the Multiple Traveling Salesman Problem (mTSP) optimally.

        :param agents: Dictionary {agent_id: agent_object}.
        :param points: List of point coordinates [(x, y), (x, y), ...].
        :return: Dictionary {agent_id: ordered list of tasks}
        """
        cost_matrix, destination_positions = self.compute_cost_matrix(agents, points)
        agent_ids = [agent.agent_id for agent in agents]

        if cost_matrix is None:
            return {}

        num_agents = len(agent_ids)
        num_tasks = len(destination_positions)

        # Create a combined list of start points and tasks
        points_combined = [(agents[agent_id].localization[0], agents[agent_id].localization[1]) for agent_id in agent_ids] + destination_positions

        # Compute the full distance matrix
        full_cost_matrix = cdist(points_combined, points_combined, metric="euclidean")

        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(len(full_cost_matrix), num_agents, list(range(num_agents)))

        # Create Routing Model
        routing = pywrapcp.RoutingModel(manager)

        # Define the cost of travel
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(full_cost_matrix[from_node][to_node])

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Allow all agents to visit all tasks
        for agent in range(num_agents):
            routing.AddVariableMinimizedByFinalizer(routing.NextVar(agent))

        # Solve the problem
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

        solution = routing.SolveWithParameters(search_parameters)

        # Extract solution
        if solution:
            allocation = {agent_ids[i]: [] for i in range(num_agents)}
            for agent in range(num_agents):
                index = routing.Start(agent)
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    if node_index >= num_agents:  # Ignore the agent's starting location
                        allocation[agent_ids[agent]].append(destination_positions[node_index - num_agents])
                    index = solution.Value(routing.NextVar(index))
            return allocation
        else:
            return self.hungarian_allocation(agents, points)  # Fallback if mTSP fails
