#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.legacy-ros.yml}"
ROS_CONTAINER="${ROS_CONTAINER:-c2-imugs2-centralized-coordination}"

required_containers=(
  c2-imugs2-mongodb
  c2-imugs2-centralized-coordination
  c2-imugs2-planner
  c2-imugs2-c2-ros-rest
  c2-imugs2-rosbridge
  c2-imugs2-edge-agent-sim-1
)

required_nodes=(
  /c2_node
  /c2_interface_node
  /orchestrator_node
  /fleet_manager_node
  /planner_node
  /rosbridge_websocket
  /agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5
  /autonomy_test_node_Themis_Fr
)

required_topics=(
  /multi_robot/mission_init_request
  /multi_robot/mission_feedback
  /multi_robot/edge/feedback
  /multi_robot/planner/state
)

failures=0

check() {
  local label="$1"
  shift
  if "$@"; then
    printf '[ok] %s\n' "$label"
  else
    printf '[error] %s\n' "$label"
    failures=$((failures + 1))
  fi
}

container_running() {
  local container="$1"
  [ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null || true)" = "true" ]
}

has_line() {
  local haystack="$1"
  local needle="$2"
  grep -Fxq "$needle" <<< "$haystack"
}

echo "Legacy compose status:"
docker compose -f "$COMPOSE_FILE" ps
echo

for container in "${required_containers[@]}"; do
  check "container running: $container" container_running "$container"
done

nodes="$(docker exec "$ROS_CONTAINER" bash -lc 'source /opt/ros/humble/setup.bash && source /app/centralized_coordination/install/setup.bash && ros2 node list' 2>/dev/null || true)"
topics="$(docker exec "$ROS_CONTAINER" bash -lc 'source /opt/ros/humble/setup.bash && source /app/centralized_coordination/install/setup.bash && ros2 topic list' 2>/dev/null || true)"

for node in "${required_nodes[@]}"; do
  check "ROS node visible: $node" has_line "$nodes" "$node"
done

for topic in "${required_topics[@]}"; do
  check "ROS topic visible: $topic" has_line "$topics" "$topic"
done

check "legacy REST reachable: http://localhost:5001/mission_control" python3 - <<'PY'
from urllib import request
req = request.Request("http://localhost:5001/mission_control", method="OPTIONS")
with request.urlopen(req, timeout=3) as response:
    raise SystemExit(0 if response.status < 500 else 1)
PY

check "rosbridge websocket reachable: ws://localhost:9090" python3 - <<'PY'
import base64
import os
import socket

key = base64.b64encode(os.urandom(16)).decode()
request = (
    "GET / HTTP/1.1\r\n"
    "Host: localhost:9090\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    f"Sec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Version: 13\r\n\r\n"
)
with socket.create_connection(("127.0.0.1", 9090), timeout=3) as sock:
    sock.sendall(request.encode())
    response = sock.recv(256).decode(errors="replace")
    raise SystemExit(0 if "101" in response and "websocket" in response.lower() else 1)
PY

echo
if [ "$failures" -eq 0 ]; then
  echo "Legacy ROS stack smoke test passed."
else
  echo "Legacy ROS stack smoke test failed with $failures issue(s)."
  exit 1
fi
