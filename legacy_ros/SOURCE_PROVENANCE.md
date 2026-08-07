# `legacy_ros` Source Provenance

This directory vendors the ROS components from
`/home/basil/repos/robotics/multi-agent-framework` at framework revision
`327c387899fb3b77af658e9811cfebd80ba9592a`.

| Local path | Framework path | Component revision |
| --- | --- | --- |
| `fog/centralized-coordination` | `submodules/fog/centralized-coordination` | `4c0cdb023621796f8c6d9cd5fb2715eca457f91f` |
| `fog/command-control/src/backend/ros2-rest-api` | `submodules/fog/command-control/src/backend/ros2-rest-api` | `a95115a8cec5073a146a9edf206e06d1927a0d2e` |
| `fog/planner` | `submodules/fog/planner` | `b154575f5a5f8fa8884e35424224a1364f19cf9d` |
| `edge/agent-tasks-supervisor` | `submodules/edge/agent-tasks-supervisor` | `fdff69bedea140f3df41fb66e01776a0082aea36` |

Retained ROS runtime source was imported and content-compared on 2026-08-07.
The revisions above are provenance for that baseline; they are not a claim that
the current planner remains byte-identical. Centralized coordination, the edge
supervisor, and the REST bridge remain baseline-equivalent. The planner has
these repository-local compatibility patches:

- an idempotent three-feature `MapDB.rma` seed
  ([`seed-mapdb.js`, L71-L144](docker/seed-mapdb.js#L71-L144));
- a nonfatal `CreatePlanner` map-readiness guard returning state `4`
  ([`planner_node.py`, L290-L322](fog/planner/ros2ws/src/planner/planner/planner_node.py#L290-L322)
  and [L694-L722](fog/planner/ros2ws/src/planner/planner/planner_node.py#L694-L722));
- a planning exception boundary and stable AStar no-route contract
  ([`planner_node.py`, L221-L287](fog/planner/ros2ws/src/planner/planner/planner_node.py#L221-L287),
  [`mapf.py`, L71-L127](fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/mapf.py#L71-L127),
  and [`multi_robot_path_planning.py`, L182-L197](fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py#L182-L197));
- bidirectional local free-road edges
  ([`graph.py`, L184-L227](fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/graph.py#L184-L227));
- `25 m` runtime graph-connector thresholds, replacing upstream's `15 m` for
  the measured `21.45 m` local-to-OSM gap
  ([`config_planner.yaml`, L7-L11](config/config_planner.yaml#L7-L11)).

Generated build/install/log trees, caches, development-container metadata, and
historical binary plots remain excluded. Dockerfiles, compose wiring, launch
aggregation, seed orchestration, and runtime mounts are local adapters. The
command-control dependency installer adds
`ros-$ROS_DISTRO-rosbridge-server` for the separate rosbridge service.

Live ROS validation produced planner state `2` and `10` waypoints for the exact
Themis mission. An unreachable route produced state `4` while `/planner_node`
remained alive.

For the file-level comparison, intentional integration differences, and the
planner baseline and local compatibility differences, see
[`docs/LEGACY_ROS_UPSTREAM_COMPARISON.md`](../docs/LEGACY_ROS_UPSTREAM_COMPARISON.md).
