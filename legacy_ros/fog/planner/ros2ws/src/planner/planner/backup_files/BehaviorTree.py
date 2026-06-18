import py_trees
from shapely.geometry import Point, Polygon, LineString

class BehaviorTreeBuilder:
    def __init__(self):
        self.tree = None
    
    def create_behavior_tree(self):
        root = py_trees.composites.Selector(name="Mission", memory=False)
        
        navigate = py_trees.composites.Sequence(name="Navigate to Geometries", memory=False)
        navigate.add_child(CheckBehavior(0))  # The behavior check for navigation
        
        # Generic branches for coverage logic, which will be filled during tick
        navigate.add_child(ComputeCoverageGoals())  # Placeholder for dynamic goal computation
        navigate.add_child(AssignGoals())  # Placeholder for dynamic assignment logic
        navigate.add_child(PlanPaths())  # Placeholder for path planning
        
        explore = py_trees.composites.Sequence(name="Explore Geometries", memory=False)
        explore.add_child(CheckBehavior(1))  # The behavior check for exploration
        explore.add_child(ComputeCoverageGoals())  # Placeholder for dynamic exploration
        
        root.add_children([navigate, explore])
        
        self.tree = root

        # Visualize in ASCII
        print(py_trees.display.ascii_tree(self.tree))
    
    def tick_tree(self, mission_config):
        if self.tree:
            # Pass mission configuration to the tree on each tick
            self.update_dynamic_nodes(mission_config)
            self.tree.tick()

    def update_dynamic_nodes(self, mission_config):
        # Update dynamic nodes based on mission configuration
        for node in self.tree.children:
            if isinstance(node, ComputeCoverageGoals):
                node.update_coverage(mission_config)  # Pass coverage info
            if isinstance(node, AssignGoals):
                node.assign_goals(mission_config)  # Assign goals based on config
            if isinstance(node, PlanPaths):
                node.plan_paths(mission_config)  # Plan paths for the assigned goals



class CheckBehavior(py_trees.behaviour.Behaviour):
    def __init__(self, behavior, target_behavior):
        super(CheckBehavior, self).__init__("Check Behavior")
        self.behavior = behavior
        self.target_behavior = target_behavior

    def update(self):
        if self.behavior == self.target_behavior:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE

class CheckMaximizeCoverage(py_trees.behaviour.Behaviour):
    def __init__(self, maximize_coverage):
        super(CheckMaximizeCoverage, self).__init__("Check Maximize Coverage")
        self.maximize_coverage = maximize_coverage

    def update(self):
        return py_trees.common.Status.SUCCESS if self.maximize_coverage else py_trees.common.Status.FAILURE

class ComputeCoverageGoals(py_trees.behaviour.Behaviour):
    def __init__(self, geometries, vehicles):
        super(ComputeCoverageGoals, self).__init__("Compute Coverage Goals")
        self.geometries = geometries
        self.vehicles = vehicles

    def update(self):
        # Compute points for coverage optimization
        print(f"Computing coverage goals for {len(self.geometries)} geometries with {len(self.vehicles)} vehicles.")
        return py_trees.common.Status.SUCCESS
    
class AssignGoals(py_trees.behaviour.Behaviour):
    def __init__(self, geometries, vehicles):
        super().__init__(name="Assign Goals")
        self.geometries = geometries
        self.vehicles = vehicles

    def update(self):
        # Simplified goal assignment logic
        if len(self.geometries) <= len(self.vehicles):
            # Assign one geometry to each vehicle
            self.assigned_goals = {v: g for v, g in zip(self.vehicles, self.geometries)}
        else:
            # Randomly select geometries if there are fewer vehicles than geometries
            self.assigned_goals = {v: self.geometries[i % len(self.geometries)] for i, v in enumerate(self.vehicles)}
        
        # Log assigned goals for debugging
        print(f"Assigned goals: {self.assigned_goals}")
        return py_trees.common.Status.SUCCESS

class PlanPaths(py_trees.behaviour.Behaviour):
    def __init__(self, goals):
        super(PlanPaths, self).__init__("Plan Paths")
        self.goals = goals

    def update(self):
        print(f"Planning paths to goals: {self.goals}")
        return py_trees.common.Status.SUCCESS

# Create Behavior Tree
def create_behavior_tree(behavior, maximize_coverage, geometries, vehicles):
    root = py_trees.composites.Selector(name="Mission", memory=False)

    # Navigate to Geometries (Behavior 0)
    navigate = py_trees.composites.Sequence(name="Navigate to Geometries", memory=False)
    navigate.add_child(CheckBehavior(behavior, 0))
    navigate.add_child(CheckMaximizeCoverage(maximize_coverage))

    # Branches for maximize_coverage True/False
    if maximize_coverage:
        navigate.add_child(ComputeCoverageGoals(geometries, vehicles))
    else:
        navigate.add_child(AssignGoals(geometries, vehicles))  # Simplified logic for False case

    navigate.add_child(PlanPaths(geometries))

    # Explore Geometries (Behavior 1)
    explore = py_trees.composites.Sequence(name="Explore Geometries", memory=False)
    explore.add_child(CheckBehavior(behavior, 1))
    explore.add_child(ComputeCoverageGoals(geometries, vehicles))
    explore.add_child(PlanPaths(geometries))

    root.add_children([navigate, explore])
    return root


# Example Usage
behavior = 0
maximize_coverage = False
geometries = [Point(1, 1), Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]
vehicles = ["vehicle_1", "vehicle_2"]

tree = create_behavior_tree(behavior, maximize_coverage, geometries, vehicles)


# Instantiate the behavior tree builder
behavior_tree_builder = BehaviorTreeBuilder()

# Pre-define the behavior tree
behavior_tree_builder.create_behavior_tree()

# Update mission config (this could come from an API or another module)
mission_config = {
    "geometries": [Point(1, 1), Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
    "vehicles": ["vehicle_1", "vehicle_2"],
    "maximize_coverage": False,
    "behavior": 0,
}

# Tick the tree with the current mission configuration
behavior_tree_builder.tick_tree(mission_config)




tree.tick_once()
