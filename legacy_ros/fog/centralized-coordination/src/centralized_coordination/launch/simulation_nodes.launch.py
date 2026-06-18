from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    # swarm_manager_node = Node(
    #     package="centralized_coordination",
    #     executable="centralized_coordination_executable"
    # )

    swarm_planner_node = Node(
        package="centralized_coordination",
        executable="test_planner_sim"
    )
    c2_node = Node(
        package="centralized_coordination",
        executable="test_c2_sim"
    )

    # ld.add_action(swarm_manager_node)
    ld.add_action(swarm_planner_node)
    ld.add_action(c2_node)

    return ld