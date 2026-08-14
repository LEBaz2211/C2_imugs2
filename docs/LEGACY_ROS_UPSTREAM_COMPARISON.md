# Legacy ROS Compared With `multi-agent-framework`

> **Documentation label: REFERENCE**
> Dated provenance and comparison evidence for the frozen source tree.

Comparison date: 2026-08-07.

## Result

The retained ROS runtime was first synchronized to the checked-out
`multi-agent-framework` component revisions. Centralized coordination, the edge
supervisor, and the REST bridge still match that baseline. The planner now has a
small, explicit set of repository-local compatibility patches on top of its
upstream revision so the real Dockerized stack starts and fails safely.

| Legacy component | Authoritative framework source | Revision | Result |
| --- | --- | --- | --- |
| `fog/centralized-coordination` | `submodules/fog/centralized-coordination` | `4c0cdb023621` | Already identical |
| `edge/agent-tasks-supervisor` | `submodules/edge/agent-tasks-supervisor` | `fdff69bedea1` | Already identical |
| REST bridge subtree | `submodules/fog/command-control/src/backend/ros2-rest-api` | command-control `a95115a8cec5` | Already identical |
| `fog/planner` | `submodules/fog/planner` | `b154575f5a5f` | Baseline synchronized; local patches listed below |

The containing framework revision is `327c387899fb3b77af658e9811cfebd80ba9592a`.
Its checked-out files have many executable-bit-only working-tree changes. At
the synchronization point, the imported baseline content equaled the component
commits above.

The component hashes identify the imported baseline, not the current planner's
complete content identity. Some unchanged files also retain older executable
mode bits; that metadata difference does not alter runtime behavior.

## Planner Files Synchronized

These four files contain all planner runtime-code differences that existed
before synchronization:

- `planner/planner_node.py`
- `path_planning_lib/mapf.py`
- `path_planning_lib/multi_robot_path_planning.py`
- `path_planning_lib/utils.py`

The framework versions remove the later C2-specific local-map, road-only,
inline-feature, endpoint-append, path-simplification, and route-fallback
adaptations. Two planner-owned build scripts were also copied verbatim:

- `.config/install_dependencies.sh`
- `path_planning_lib/build_lib.sh`

The framework's `Single-Robotnik-Full-Stack/config_planner.yaml` supplied the
database-map configuration and `60 m` OSM radius. Its `15 m` connector distance
was the initial baseline; the deployed local value is now `25 m`, as explained
below.

The other active Single-Robotnik configuration and input files already matched:

- edge-supervisor, autonomy, and centralized-coordination YAML;
- the separate edge and autonomy launch scripts;
- `.env.ros`;
- the complete `data/map` tree.

## Intentionally Repository-Local Files

The following are integration wrappers, not forks of ROS component behavior,
and remain local to this repository:

- `docker-compose.legacy-ros.yml`
- `legacy_ros/docker/*`
- `legacy_ros/config/launch_edge_with_autonomy_sim.sh`
- the rosbridge package addition used by the C2 REST image
- `legacy_ros/docker/seed-mapdb.js` and the compose seed service

Specifically, `legacy_ros/fog/command-control/install_ros_dependencies.sh` adds
only `ros-$ROS_DISTRO-rosbridge-server` beyond the framework version. This
supports the local rosbridge service and does not alter REST or mission logic.

The authoritative `build_lib.sh` assumes a `Fields2Cover/` checkout that is not
present in either trimmed vendor tree. `legacy_ros/docker/Dockerfile.planner`
therefore builds the baseline Python package directly, then performs the same
ROS workspace build.

Generated workspaces, caches, `.devcontainer` files, historical plot/test PNGs,
and the unused `planner/assets/ugv.png` were not imported. They are not deployed
runtime source.

Component-pinned ROS message packages were compared with the message packages
nested in each authoritative component and already match. They were not
replaced with the framework's newer root-level `submodules/custom-msgs/*`, whose
contracts differ from the legacy component pins.

## Repository-Local Planner Compatibility Patches

These changes deliberately diverge from planner revision `b154575f5a5f` while
preserving its ROS messages, services, topics, mission JSON, and task-plan JSON:

- The one-shot compose service at
  [`docker-compose.legacy-ros.yml`, L17-L37](../docker-compose.legacy-ros.yml#L17-L37)
  runs the idempotent
  [`seed-mapdb.js`, L71-L144](../legacy_ros/docker/seed-mapdb.js#L71-L144).
  It flattens and upserts the three valid RMA baseline features before the
  planner starts, preserves unrelated rows, and skips the malformed,
  geographically unrelated virtual-geofence file.
- `CreatePlanner` calls a lazy map-readiness guard and converts initialization
  errors into planner/service state `4` instead of terminating ROS spin; see
  [`planner_node.py`, L290-L322](../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L290-L322)
  and
  [`planner_node.py`, L694-L722](../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L694-L722).
- The planning timer catches solver errors, releases its path lock, clears any
  stale path cache, publishes state `4`, and leaves the node alive
  ([`planner_node.py`, L221-L287](../legacy_ros/fog/planner/ros2ws/src/planner/planner/planner_node.py#L221-L287)).
  AStar now has a stable no-route return shape
  ([`mapf.py`, L71-L127](../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/mapf.py#L71-L127)),
  which the mission solver turns into an explicit planning error
  ([`multi_robot_path_planning.py`, L182-L197](../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/multi_robot_path_planning.py#L182-L197)).
- Local free-road LineStrings are traversable in both directions
  ([`graph.py`, L184-L227](../legacy_ros/fog/planner/ros2ws/src/path_planning_lib/path_planning_lib/graph.py#L184-L227)).
- The runtime line/polygon connector thresholds are `25 m`
  ([`config_planner.yaml`, L7-L11](../legacy_ros/config/config_planner.yaml#L7-L11)).
  The measured nearest gap between the seeded local road component and the
  current OSM component is `21.45 m`; the upstream `15 m` value left the graph
  disconnected.

The original startup defect, the local compatibility boundary, and the now
runnable mission path are traced with exact source links in the
[true legacy single-robot walkthrough](LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md).

## Live Validation

The rebuilt real stack was exercised through the ROS services, not a mock. The
exact Themis mission for
`f9992bb3-9871-451f-90a0-9207eb9fe6c5` reached planner state `2` and returned
one task containing `10` waypoint objectives. A deliberately unreachable route
reached planner state `4`; `/planner_node` remained running and continued to
serve ROS requests.
