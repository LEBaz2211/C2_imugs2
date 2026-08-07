#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
source /app/backend/ros2-rest-api/ros2_ws/install/setup.bash
exec "$@"
