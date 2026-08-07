#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
source /app/ros2ws/install/setup.bash
exec "$@"
