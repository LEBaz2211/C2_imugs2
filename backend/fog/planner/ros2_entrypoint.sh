#!/bin/bash
set -e

. /opt/ros/humble/setup.bash
. /app/ros2ws/install/setup.bash

exec "$@"