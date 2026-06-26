# Multi Agent Path Finding Algorithms

"""
AStar search
"""
from cmath import sqrt
from math import dist, fabs
import itertools
import time

import matplotlib.pyplot as plt# for plotting cost map
import networkx as nx
# fromprint tools.bresenham import *
from .graph import *
from .models import *


    
class AStar():
    def __init__(self, graph, agent, ordered_destinations, road_usage=0.5):
        # Associated with a specific graph and a specific agent
        self.graph = graph
        self.agent = agent 
        self.destination = ordered_destinations[0]
        self.road_usage = self._normalized_preference(road_usage)
        self.roads_only = self.road_usage >= 0.999
        self.preferred_road_sources = self._preferred_road_sources() if self.roads_only else None

    @staticmethod
    def _normalized_preference(value):
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return 0.5
        if normalized > 1.0:
            normalized = normalized / 100.0
        return min(max(normalized, 0.0), 1.0)

    # def set_preferred_start_direction(self,initial_state,preferred_start_direction):
    #     if preferred_start_direction:
    #         preferred_direction_line = list(self.bresenham(initial_state.location.x,initial_state.location.y,preferred_start_direction.location.x,preferred_start_direction.location.y))
    #         for position in preferred_direction_line:
    #             self.cost_graph[position[1],position[0]] *=1
                
    
    def edge_data(self, current_node, neighbor_node):
        if self.graph.has_edge(current_node, neighbor_node):
            edges = self.graph.get_edge_data(current_node, neighbor_node)
        elif self.graph.has_edge(neighbor_node, current_node):
            edges = self.graph.get_edge_data(neighbor_node, current_node)
        else:
            return None

        candidates = list(edges.values())
        if self.roads_only:
            road_candidates = [edge for edge in candidates if self.is_allowed_road(edge)]
            if road_candidates:
                candidates = road_candidates
        return min(candidates, key=lambda edge: edge.get('length', float('inf')))

    def edge_is_blocked(self, current_node, neighbor_node):
        edge = self.edge_data(current_node, neighbor_node)
        if edge is None:
            return True
        if bool(edge.get('risk', False)):
            return True
        return self.roads_only and not self.is_allowed_road(edge)

    def step_cost(self, current_node, neighbor_node):
        # Set the cost of a step to a neighbor to its value in the cost graph:
        # step_cost = self.cost_graph[neighbor.location.y,neighbor.location.x]

        edge = self.edge_data(current_node, neighbor_node)
        if edge is None:
            return float('inf')
        cost = edge['length']
        is_road = bool(edge.get('road', False))
        if self.road_usage > 0.5 and not is_road:
            cost *= 1.0 + ((self.road_usage - 0.5) * 198.0)
        elif self.road_usage < 0.5 and is_road:
            cost *= 1.0 + ((0.5 - self.road_usage) * 198.0)
        return cost

    def heuristic_cost(self, current_node, destination_node):
        current_x = self.graph.nodes[current_node]['x']
        current_y = self.graph.nodes[current_node]['y']
        destination_x = self.graph.nodes[destination_node]['x']
        destination_y = self.graph.nodes[destination_node]['y']

        h_cost = fabs(current_x - destination_x) + fabs(current_y - destination_y)
        # For high road_usage, heuristic cost can be lowered:
        # if self.road_usage>0.5 and (current_x, current_y) in self.roads: h_cost = (1.5-self.road_usage)*h_cost
        return h_cost

    def reconstruct_path(self, came_from, current_node):
        reverse_path = [current_node]
        while current_node in came_from.keys():
            current_node = came_from[current_node]
            reverse_path.append(current_node)
        total_path = reverse_path[::-1]
        route = list()
        for i, node in enumerate(total_path):
            if i == 0:
                t=0
            else:
                previous_state = route[i-1]
                t = previous_state.get_time() + self.step_cost(total_path[i-1], node) / self.agent.nominal_speed
            state = State(t,node)
            route.append(state)
        return route
    
    

    def search(self, log_failure=True):
        """Buddy
        low level A* search 
        """
        # start_state= State(0, ox.nearest_nodes(self.graph,self.agent.localization[0],self.agent.localization[1]))
        start_node = self.nearest_routable_node(self.agent.localization)
        
        destination_node= self.nearest_routable_node(self.destination)
        
        closed_set = set()
        open_set = {start_node}

        came_from = {}

        g_score = {} 
        g_score[start_node] = 0

        f_score = {} 

        f_score[start_node] = self.heuristic_cost(start_node, destination_node)
        
        while open_set:
            temp_dict = {open_item:f_score.setdefault(open_item, float("inf")) for open_item in open_set}
            current_node = min(temp_dict, key=temp_dict.get)
            if current_node==destination_node:
                return self.reconstruct_path(came_from, current_node), f_score[current_node]

            open_set -= {current_node}
            closed_set |= {current_node}

            # Get the neighbors of the selected node
            neighbor_nodes = set(self.graph.neighbors(current_node))
            if hasattr(self.graph, 'predecessors'):
                neighbor_nodes |= set(self.graph.predecessors(current_node))
            for neighbor_node in neighbor_nodes:
                # t = current_state.get_time() + self.graph.edges[current_node, node, 0]['length'] / self.agent.nominal_speed
                # time.sleep(1)
                # neighbor_state = State(t,node)
                
                if not neighbor_node or neighbor_node in closed_set:
                    continue
                if self.edge_is_blocked(current_node, neighbor_node):
                    continue

                tentative_g_score = g_score.setdefault(current_node, float("inf")) + self.step_cost(current_node, neighbor_node)

                if neighbor_node not in open_set:
                    open_set |= {neighbor_node}
                elif tentative_g_score >= g_score.setdefault(neighbor_node, float("inf")):
                    continue

                came_from[neighbor_node] = current_node

                g_score[neighbor_node] = tentative_g_score 
                f_score[neighbor_node] =  g_score[neighbor_node] + self.heuristic_cost(neighbor_node, destination_node) 
            

        try:
            undirected_has_path = nx.has_path(self.graph.to_undirected(as_view=True), start_node, destination_node)
        except Exception:
            undirected_has_path = "unknown"
        if log_failure:
            print(
                "A* failed",
                {
                    "agent": self.agent.agent_id,
                    "visited_nodes": len(closed_set),
                    "remaining_open_nodes": len(open_set),
                    "undirected_has_path": undirected_has_path,
                    "risk_edges": sum(1 for _u, _v, _key, data in self.graph.edges(keys=True, data=True) if data.get('risk')),
                    "road_edges": sum(1 for _u, _v, _key, data in self.graph.edges(keys=True, data=True) if data.get('road')),
                    "total_edges": self.graph.number_of_edges(),
                },
                flush=True,
            )
        return False

    def nearest_routable_node(self, point):
        if not self.roads_only:
            return ox.nearest_nodes(self.graph, point[0], point[1])

        road_nodes = self.road_nodes(self.preferred_road_sources)
        if not road_nodes:
            return ox.nearest_nodes(self.graph, point[0], point[1])

        return min(
            road_nodes,
            key=lambda node: self._squared_coordinate_distance(
                point,
                [self.graph.nodes[node]['x'], self.graph.nodes[node]['y']],
            ),
        )

    def road_nodes(self, road_sources=None):
        nodes = set()
        for u, v, _key, data in self.graph.edges(keys=True, data=True):
            if not self.is_allowed_road(data, road_sources):
                continue
            nodes.add(u)
            nodes.add(v)
        return nodes

    def is_allowed_road(self, edge, road_sources=None):
        if not edge.get('road') or edge.get('risk'):
            return False
        sources = self.preferred_road_sources if road_sources is None else road_sources
        if isinstance(sources, str):
            sources = {sources}
        if sources is not None and edge.get('road_source') not in sources:
            return False
        return True

    def _preferred_road_sources(self):
        sources = set()
        if self.road_nodes("osm"):
            sources.add("osm")
        if self.road_nodes("mission_line"):
            sources.update({"mission_line", "mission_connector"})
        return sources or None

    @staticmethod
    def _squared_coordinate_distance(first, second):
        return ((float(first[0]) - float(second[0])) ** 2) + ((float(first[1]) - float(second[1])) ** 2)

class CBS_Node(object):
    def __init__(self):
        self.solution = {}
        self.constraint_dict = {}
        self.cost = 0

class VertexConstraint(object):
    def __init__(self, state):
        self.state = state

    def __eq__(self, other):
        return self.state.time == other.state.time and self.state.node == self.state.node
    def __hash__(self):
        return hash(str(self.state.time)+str(self.state.node))
    def __str__(self):
        return '(' + str(self.state.time) + ', '+ str(self.state.node) + ')'

class EdgeConstraint(object):
    def __init__(self, time, state_1, state_2):
        self.state_1 = state_1
        self.state_2 = state_2
    def __eq__(self, other):
        return (self.state_1 == other.state_1 and self.state_2 == other.state_2) or (self.state_1 == other.state_2 and self.state_2 == other.state_1)

class Constraints(object):
    def __init__(self):
        self.node_constraints = set()
        self.edge_constraints = set()

    def add_constraint(self, other):
        self.node_constraints |= other.node_constraints
        self.edge_constraints |= other.edge_constraints

class Conflict(object):
    # types:
    VERTEX = 1
    EDGE = 2
    def __init__(self, type=None):
        self.type = type
        self.agents = tuple()

        if type == self.VERTEX:
            self.state = State()
        elif type == self.EDGE:
            self.state_1 = State()
            self.state_2 = State()




# Article about CBS basics: https://doi.org/10.1609/aaai.v26i1.8140
class CBS(object):
    def __init__(self, graph):
        self.graph = graph
        self.open_set = set()
        self.closed_set = set()
        self.solution = {}
        self.constraints = Constraints()
        self.constraint_dict = {}

    # def pause_other_agents(self, wait_time = 0):
    #     # print(self.LOS_lost_state)
    #     for other_agent in self.solution.keys():
    #         adapted_solution = self.solution[other_agent]
    #         if wait_time <= len(adapted_solution):
    #             wait_waypoint = State(adapted_solution[wait_time].time, adapted_solution[wait_time].location)
    #             # print(wait_waypoint.location)
    #             for waypoint in adapted_solution[wait_time:]:
    #                 waypoint.time += 1
    #             adapted_solution.insert(wait_time, wait_waypoint)
    #             self.solution.update({other_agent: adapted_solution})
    #             self.env.agents_paused_dict[other_agent].append(wait_time)

    def compute_solution(self, agents, allocations):
        self.solution = {}

        for agent_id, destination in allocations.items():
            print("CBS - computing solution for agent ", agent.agent_id)

            # Retrieve the agent object using the agent_id
            agent = agents[agent_id]        

            a_star = AStar(self.graph, agent, destination)
            path, f_score = a_star.search()
            
            # If promblem due to Line Of Sight not satisfied:
            # if not path and self.env.line_of_sight==1 and failure_reason == 7 and not self.env.line_of_sight_target:
            #     counter = 0
            #     while not path and failure_reason == 7 and counter <100:
            #         counter += 1
            #         wait_time = self.env.LOS_lost_state.time # Time when LOS was lost
                    
            #         self.pause_other_agents(wait_time)
            #         path, failure_reason = self.a_star.search(agent)
            #     print("Added ",counter, " seconds of pause to other agents")
            #     if path: 
            #         print(self.env.agents_paused_dict)

            if not path:
                # if failure_reason == 7: print("------LOS PLANNING FAILURE FOR AGENT", agent)
                # elif failure_reason == 0: print("------UNKNOWN PLANNING FAILURE FOR AGENT", agent)
                return False
            else: 
                self.solution.update({agent.agent_id: {'path': path, 'f_score': f_score}})

                # self.solution.update({agent.agent_id:path})
        
        return self.solution

    def compute_solution_cost(self, solution):
        total_f_score = sum(entry['f_score'] for entry in solution.values())
        return total_f_score

    def get_first_conflict(self, solution):
        for (agent1, solution_dict1), (agent2, solution_dict2) in itertools.combinations(self.solution.items(), 2):
            path1 = solution_dict1['path']
            path2 = solution_dict2['path']

            node_conflict_state = next((state1 for state1 in path1 for state2 in path2 if state1==state2), None)
            node_conflict_state = False
            if node_conflict_state:
                print("Node Conflict Found!")
                if node_conflict_state == path1[-1] or node_conflict_state == path2[-1]: 
                        print("One of the agents was at its goal and was hit by another agent")
                else:
                    result = Conflict(Conflict.VERTEX)
                    result.state = node_conflict_state
                    result.agents = (agent1, agent2)

        # max_t = max(len(solution_dict['path']) for solution_dict in self.solution.values())
        # for t in range(max_t):
        #     for agent_1, agent_2 in combinations(solution.keys(), 2):
        #         state_1 = self.get_state(agent_1, solution, t)
        #         state_2 = self.get_state(agent_2, solution, t)

        #         if state_1.same_location_as(state_2):
        #             result.time = t
        #             result.type = Conflict.VERTEX
        #             result.state_1 = state_1.location
        #             if self.is_at_goal(state_1,agent_1): 
        #                 print(agent_1, "was at goal and was hit by ", agent_2)
        #                 result.agent_1 = agent_2 # Don't put a constraint on agent tha was at goal
        #                 result.agent_2 = agent_2
        #             elif self.is_at_goal(state_2,agent_2): 
        #                 print(agent_2, "was at goal and was hit by ", agent_1)
        #                 result.agent_1 = agent_1
        #                 result.agent_2 = agent_1
        #             else:
        #                 result.agent_1 = agent_1
        #                 result.agent_2 = agent_2
        #             return result

        #     for agent_1, agent_2 in combinations(solution.keys(), 2):
        #         state_1a = self.get_state(agent_1, solution, t)
        #         state_1b = self.get_state(agent_1, solution, t+1)

        #         state_2a = self.get_state(agent_2, solution, t)
        #         state_2b = self.get_state(agent_2, solution, t+1)

        #         if state_1a.same_location_as(state_2b) and state_1b.same_location_as(state_2a):
        #             result.time = t
        #             result.type = Conflict.EDGE
        #             result.agent_1 = agent_1
        #             result.agent_2 = agent_2
        #             result.state_1 = state_1a.location
        #             result.state_2 = state_1b.location
        #             return result
        return False

    def create_constraints_from_conflict(self, conflict):
        constraint_dict = {}
        if conflict.type == Conflict.VERTEX:
            # t = conflict.state.time
            # t_1 = t
            # t_2 = t
            
            # if self.agents_paused_dict: # If the agents were paused
            #     t_1 = t - sum(wait_time < t for wait_time in self.agents_paused_dict[conflict.agents[0]])
            #     t_2 = t - sum(wait_time < t for wait_time in self.agents_paused_dict[conflict.agents[1]])
            #     [self.agents_paused_dict.update({agent:[]}) for agent in self.agents_paused_dict.keys()]
            
            constraint_1 = Constraints()
            constraint_1.vertex_constraints |= {VertexConstraint(t_1, conflict.state)}
            
            # constraint_2 = Constraints()
            # constraint_2.vertex_constraints |= {VertexConstraint(t_2, conflict.state)}

            constraint_dict[conflict.agents[0]] = constraint_1
            # constraint_dict[conflict.agent_2] = constraint_2
            

        # elif conflict.type == Conflict.EDGE:
        #     constraint1 = Constraints()
        #     constraint2 = Constraints()

        #     e_constraint1 = EdgeConstraint(conflict.time, conflict.state_1, conflict.state_2)
        #     e_constraint2 = EdgeConstraint(conflict.time, conflict.state_2, conflict.state_1)

        #     constraint1.edge_constraints |= {e_constraint1}
        #     constraint2.edge_constraints |= {e_constraint2}

        #     constraint_dict[conflict.agents[0]] = constraint1
        #     constraint_dict[conflict.agents[1]] = constraint2

        return constraint_dict


    def search(self, agents, allocations):
        start_cbs_node = CBS_Node()
        start_cbs_node.constraint_dict = {}
        for agent in agents:
            start_cbs_node.constraint_dict[agent.agent_id] = Constraints()
        start_cbs_node.solution = self.compute_solution(agents, allocations)
        if not start_cbs_node.solution:
            print("No initial plan was found")
            return {}
        start_cbs_node.cost = self.compute_solution_cost(start_cbs_node.solution)

        self.open_set |= {start_cbs_node}

        while self.open_set: # open set contains a solution that needs to be checked for conflicts
            P = min(self.open_set)
            self.open_set -= {P}
            self.closed_set |= {P}

            self.constraint_dict = P.constraint_dict
            conflict_dict = self.get_first_conflict(P.solution)
            print(conflict_dict)
            if not conflict_dict:
                print("solution found")
                return self.generate_plan(P.solution)

            constraint_dict = self.create_constraints_from_conflict(conflict_dict)

            print("----> Conflict for ", list(constraint_dict.keys()), "- computing solution again ")
            for agent in constraint_dict.keys():
                new_cbs_node = deepcopy(P)
                new_cbs_node.constraint_dict[agent].add_constraint(constraint_dict[agent])

                self.constraint_dict = new_cbs_node.constraint_dict
                
                new_cbs_node.solution = self.compute_solution()
                if not new_cbs_node.solution:
                    continue
                new_cbs_node.cost = self.compute_solution_cost(new_cbs_node.solution)
                
                if new_cbs_node in self.closed_set:
                    print("same solution as the one with conflicts...")

                if new_cbs_node not in self.closed_set:
                    self.open_set |= {new_cbs_node}

                # TODO: ending condition
        if not self.open_set: print("CBS open set is now empty")
        return {} #self.generate_plan(P.solution)

    def generate_plan(self, solution):
        plan = {}
        for agent, solution_dict in solution.items():
            path = solution_dict['path']
            # path_dict_list = [{'t':state.time, 'x':state.location.x, 'y':state.location.y} for state in path]
            plan[agent] = solution_dict['path']
        return plan
