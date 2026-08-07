#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.legacy-ros.yml}"
STACK_PREFIX="${STACK_PREFIX:-c2-imugs2}"
STACK_LABEL="${STACK_LABEL:-Legacy}"
ROS_CONTAINER="${ROS_CONTAINER:-${STACK_PREFIX}-centralized-coordination}"
CHECK_MAPDB_SEED="${CHECK_MAPDB_SEED:-1}"
MONGO_CONTAINER="${MONGO_CONTAINER:-${STACK_PREFIX}-mongodb}"
MAPDB_SEED_CONTAINER="${MAPDB_SEED_CONTAINER:-${STACK_PREFIX}-mapdb-seed}"

required_containers=(
  "${STACK_PREFIX}-mongodb"
  "${STACK_PREFIX}-centralized-coordination"
  "${STACK_PREFIX}-planner"
  "${STACK_PREFIX}-c2-ros-rest"
  "${STACK_PREFIX}-rosbridge"
  "${STACK_PREFIX}-edge-agent-sim-1"
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

container_completed_successfully() {
  local container="$1"
  [ "$(docker inspect -f '{{.State.Status}}:{{.State.ExitCode}}' "$container" 2>/dev/null || true)" = "exited:0" ]
}

mapdb_seed_is_valid() {
  docker exec "$MONGO_CONTAINER" mongosh --quiet --eval '
const expected = [
  "60bae762-6c7a-4b11-8803-556fdfee4425",
  "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e",
  "5711e91f-f8e5-4ae2-b4a0-8ceb7e73d098",
];
const features = db.getSiblingDB("MapDB").getCollection("rma");
quit(expected.every((id) => features.countDocuments({"properties.feature_id": id}) === 1) ? 0 : 1);
' >/dev/null
}

has_line() {
  local haystack="$1"
  local needle="$2"
  grep -Fxq "$needle" <<< "$haystack"
}

echo "$STACK_LABEL compose status:"
docker compose -f "$COMPOSE_FILE" ps
echo

for container in "${required_containers[@]}"; do
  check "container running: $container" container_running "$container"
done

if [ "$CHECK_MAPDB_SEED" = "1" ]; then
  check "map seed completed: $MAPDB_SEED_CONTAINER" container_completed_successfully "$MAPDB_SEED_CONTAINER"
  check "MapDB.rma contains the three baseline features" mapdb_seed_is_valid
fi

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
  echo "$STACK_LABEL ROS stack smoke test passed."
else
  echo "$STACK_LABEL ROS stack smoke test failed with $failures issue(s)."
  exit 1
fi
