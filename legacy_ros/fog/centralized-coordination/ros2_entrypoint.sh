#!/bin/bash
set -e

. /opt/ros/humble/setup.bash
ls
. /app/centralized_coordination/install/setup.bash

cd /app/centralized_coordination/

exec "$@"