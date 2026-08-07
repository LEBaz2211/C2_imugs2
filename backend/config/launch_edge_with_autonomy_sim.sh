#!/usr/bin/env bash
set -euo pipefail

bash /app/launch_agent_tasks_supervisor.sh &
agent_pid=$!

bash /app/launch_autonomy_sim.sh &
autonomy_pid=$!

trap 'kill "$agent_pid" "$autonomy_pid" 2>/dev/null || true' INT TERM EXIT

wait -n "$agent_pid" "$autonomy_pid"
