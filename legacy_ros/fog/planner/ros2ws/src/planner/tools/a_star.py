"""

AStar search

author: Ashwin Bose (@atb033)

"""
from cmath import sqrt
import matplotlib.pyplot as plt# for plotting cost map
from tools.bresenham import *


class AStar():
    def __init__(self, env):
        self.agent_dict = env.agent_dict
        self.admissible_heuristic = env.admissible_heuristic
        self.is_at_goal = env.is_at_goal
        self.get_valid_neighbors = env.get_valid_neighbors
        self.valid_directions = env.valid_directions
        self.cost_graph = env.cost_graph

    # def set_preferred_start_direction(self,initial_state,preferred_start_direction):
    #     if preferred_start_direction:
    #         preferred_direction_line = list(self.bresenham(initial_state.location.x,initial_state.location.y,preferred_start_direction.location.x,preferred_start_direction.location.y))
    #         for position in preferred_direction_line:
    #             self.cost_graph[position[1],position[0]] *=1
                

    def step_cost(self, neighbor, direction):
        # Set the cost of a step to a neighbor to its value in the cost graph:
        step_cost = self.cost_graph[neighbor.location.y,neighbor.location.x]

        if 0 not in self.valid_directions[direction]: # for diagonal directions: distance*sqrt(2)
            step_cost = step_cost*sqrt(2)
        return step_cost

    def reconstruct_path(self, came_from, current):
        total_path = [current]
        while current in came_from.keys():
            current = came_from[current]
            total_path.append(current)
        return total_path[::-1]

    def search(self, agent_name):
        """
        low level search 
        """
        initial_state = self.agent_dict[agent_name]["start"]
        
        closed_set = set()
        open_set = {initial_state}

        came_from = {}

        g_score = {} 
        g_score[initial_state] = 0

        f_score = {} 

        f_score[initial_state] = self.admissible_heuristic(initial_state, agent_name)
        
        failure_reason = -1

        while open_set:
            temp_dict = {open_item:f_score.setdefault(open_item, float("inf")) for open_item in open_set}
            current = min(temp_dict, key=temp_dict.get)
            # print(agent_name, current)

            if self.is_at_goal(current, agent_name):
                failure_reason = -1 # success 
                return self.reconstruct_path(came_from, current), failure_reason

            open_set -= {current}
            closed_set |= {current}

            neighbor_list, invalidity_reasons = self.get_valid_neighbors(current)

            for direction, neighbor in enumerate(neighbor_list):
                if not neighbor or neighbor in closed_set:
                    continue
                
                tentative_g_score = g_score.setdefault(current, float("inf")) + self.step_cost(neighbor,direction)

                if neighbor not in open_set:
                    open_set |= {neighbor}
                elif tentative_g_score >= g_score.setdefault(neighbor, float("inf")):
                    continue

                came_from[neighbor] = current

                g_score[neighbor] = tentative_g_score 
                f_score[neighbor] =  g_score[neighbor] + self.admissible_heuristic(neighbor, agent_name) 
            
            if (0 not in invalidity_reasons) and (7 in invalidity_reasons):
                failure_reason=7
            elif 0 in invalidity_reasons:
                failure_reason = 0 # Unknown failure reason

        return False, failure_reason

