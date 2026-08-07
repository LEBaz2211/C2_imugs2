#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE_FILE=docker-compose.backend.yml \
STACK_PREFIX=c2-imugs2-backend \
STACK_LABEL="Editable backend" \
ROS_CONTAINER=c2-imugs2-backend-centralized-coordination \
  ./scripts/check_legacy_ros_stack.sh
