#!/bin/bash
set -e
# setup ros1 environment
echo "Sourcing ROS2 (humble)"
source "/opt/ros/humble/setup.bash"
echo "Sourcing local ROS2 workspace"
source "ros2ws/install/setup.bash"
ros2 run agent_tasks_supervisor swarm_edge_executable a_2
exec "$@"