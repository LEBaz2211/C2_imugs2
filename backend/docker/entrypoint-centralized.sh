#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
source /app/centralized_coordination/install/setup.bash
exec "$@"
