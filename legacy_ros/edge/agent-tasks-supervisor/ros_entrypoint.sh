#!/bin/bash
set -e

# unsetting ROS_DISTRO to silence ROS_DISTRO override warning
# unset ROS_DISTRO
# # setup ros1 environment
# source /opt/ros/noetic/setup.bash
# source /app/ros1ws/devel/setup.bash
# # unsetting ROS_DISTRO to silence ROS_DISTRO override warning
# unset ROS_DISTRO
# # setup ros2 environment
source /opt/ros/humble/setup.bash
source /app/ros2ws/install/setup.bash
exec "$@"