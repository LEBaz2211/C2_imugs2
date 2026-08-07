from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    # swarm_manager_node = Node(
    #     package="swarm_manager",
    #     executable="swarm_manager_executable"
    # )

    swarm_planner_node = Node(
        package="swarm_manager",
        executable="test_swarm_planner_sim"
    )
    c2_node = Node(
        package="swarm_manager",
        executable="test_c2_sim"
    )

    # ld.add_action(swarm_manager_node)
    ld.add_action(swarm_planner_node)
    ld.add_action(c2_node)

    return ld