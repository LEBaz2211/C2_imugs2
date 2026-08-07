# Editable ROS Backend Fork

This directory is the working copy of the legacy ROS backend. It exists so the
backend can evolve without changing the runnable comparison baseline in
`legacy_ros/`.

## Baseline

`backend/` contains all 627 version-controlled files from `legacy_ros/`,
copied byte-for-byte from repository commit
`9db7b44d70ce89c8dbf58e85320cf43f69e948bf` on 2026-08-04. Ignored build
outputs, caches, generated ROS workspaces, and editor files were deliberately
not copied.

```text
Source commit: 9db7b44d70ce89c8dbf58e85320cf43f69e948bf
Source tree:   194be54b33c3c3d90418e3b31bbbbdb9c098498b
Tracked files: 627
```

The initial copy includes the complete runtime source needed by the current
stack:

```text
backend/
  fog/centralized-coordination/  lifecycle, mission manager, fleet manager
  fog/planner/                   planner node and path-planning library
  fog/command-control/           C2 HTTP-to-ROS bridge
  edge/agent-tasks-supervisor/   edge supervisor and autonomy simulator
  config/                        ROS parameters, launch scripts, and maps
  docker/                        reproducible ROS 2 Humble images
```

This is intentionally a placeholder fork, not a redesigned architecture. Its
ROS message/service definitions, topic/service names, numeric enums, and JSON
contracts are unchanged. Future refactors should be made here and compared
against `legacy_ros/` one boundary at a time.

## Run The Fork

The editable fork exposes the same host ports and ROS domain as the baseline,
so only one of the two stacks may run at a time.

```bash
docker compose -f docker-compose.legacy-ros.yml down
docker compose -f docker-compose.backend.yml up --build
./scripts/check_backend_ros_stack.sh
```

The existing FastAPI/UI stack can then be started normally; it talks to the
same REST and rosbridge endpoints:

```bash
docker compose up -d --build c2-imugs2-api c2-imugs2-ui
```

The fork uses its own Mongo and planner-result directories:

```text
data/backend-mongo/
data/backend-planresults/
```

These are runtime data and should not be treated as source.

The FastAPI map reader and experimental Scenario Lab launcher still default to
paths and an edge image named for `legacy_ros/`. The initial trees are
identical, so this does not affect parity testing. Those dependencies must
become configurable before later backend changes to maps, launch scripts, or
the edge image are selected as the default UI runtime.

## Verify The Initial Copy

The following checks every version-controlled baseline file. No output from
`cmp` and a final count of `627` means the initial fork is intact:

```bash
count=0
while IFS= read -r source; do
  relative="${source#legacy_ros/}"
  cmp --silent "$source" "backend/$relative"
  count=$((count + 1))
done < <(git ls-files legacy_ros)
printf 'verified files: %s\n' "$count"
```

Once intentional refactoring starts, differences are expected and should be
covered by contract tests and recorded in the relevant design document.
