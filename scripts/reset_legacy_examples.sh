#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose -f docker-compose.legacy-ros.yml up -d mongodb

docker exec c2-imugs2-mongodb mongosh --quiet --eval '
const runtime = db.getSiblingDB("RuntimeDB");
["MissionFeedback", "Planning", "MissionConfig", "Logs"].forEach((name) => {
  const result = runtime.getCollection(name).deleteMany({});
  print(`${name}: ${result.deletedCount}`);
});
'

docker compose -f docker-compose.legacy-ros.yml up -d --force-recreate mapdb-seed
seed_exit_code="$(docker wait c2-imugs2-mapdb-seed)"
if [ "$seed_exit_code" != "0" ]; then
  docker logs c2-imugs2-mapdb-seed
  echo "Legacy MapDB seed failed with exit code $seed_exit_code." >&2
  exit "$seed_exit_code"
fi

docker compose -f docker-compose.legacy-ros.yml restart \
  centralized-coordination \
  planner \
  c2-ros-rest \
  rosbridge \
  edge-agent-sim-1

echo "Legacy example runtime reset complete."
