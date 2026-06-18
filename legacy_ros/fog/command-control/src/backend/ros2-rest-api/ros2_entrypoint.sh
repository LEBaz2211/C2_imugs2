#!/bin/bash
set -e

. /opt/ros/humble/setup.bash
ls
. ros2_ws/install/setup.bash

cd /app/c2_ros2_rest_api/

exec "$@"