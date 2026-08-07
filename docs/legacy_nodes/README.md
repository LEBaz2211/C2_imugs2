# Legacy ROS Node Contracts

This folder documents the runnable legacy ROS stack one node at a time. Each page answers four questions:

- What enters the node?
- What leaves the node?
- What the node actually does inside?
- What three concrete workflow slices look like with real field names and example data?

The examples use the current Docker stack and the current simulated UGV where possible:

```text
Mission id: 11111111-2222-4333-8444-555555555555
Agent id:   f9992bb3-9871-451f-90a0-9207eb9fe6c5
Edge node:  /agent_f9992bb3_9871_451f_90a0_9207eb9fe6c5
Autonomy:   /autonomy_test_node_Themis_Fr
Map area:   RMA, around [lon, lat] [4.392588, 50.844317]
```

## Runtime Nodes

| Node | Document | Main role |
| --- | --- | --- |
| `/c2_node` | [c2_node.md](c2_node.md) | HTTP REST bridge into old C2 ROS topics |
| `/c2_interface_node` | [c2_interface_node.md](c2_interface_node.md) | Converts C2 topic requests into orchestrator actions |
| `/orchestrator_node` | [orchestrator_node.md](orchestrator_node.md) | Owns mission lifecycle, DB registration, dynamic mission nodes |
| `/mission_<mission_id>` | [mission_manager_node.md](mission_manager_node.md) | Per-mission state machine, planner/fleet coordination, feedback |
| `/fleet_manager_node` | [fleet_manager_node.md](fleet_manager_node.md) | Agent registry, task dispatch, edge feedback bridge to planner |
| `/planner_node` | [planner_node.md](planner_node.md) | Legacy map/path planner and task-plan JSON producer |
| `/agent_<agent_id>` | [edge_agent_node.md](edge_agent_node.md) | Edge task supervisor for one robot |
| `/autonomy_test_node_Themis_Fr` | [autonomy_sim_node.md](autonomy_sim_node.md) | Simple autonomy simulator, odometry/profile/status source |
| `/rosbridge_websocket` | [rosbridge_websocket.md](rosbridge_websocket.md) | WebSocket gateway for diagnostics/live reads |
| Task primitives | [primitives.md](primitives.md) | Action units inside planner/edge task JSON |

The `centralized_coordination_executable` process creates three regular nodes in one executor: `/orchestrator_node`, `/c2_interface_node`, and `/fleet_manager_node`. The orchestrator then creates one dynamic mission manager node per initialized mission.

## Common Mission Payload

This is a compact mission config shape accepted by the legacy flow after adapter normalization. Coordinates are GeoJSON style `[lon, lat]`.

```json
{
  "mission_id": "11111111-2222-4333-8444-555555555555",
  "behavior": 0,
  "vehicles": ["f9992bb3-9871-451f-90a0-9207eb9fe6c5"],
  "objective": {
    "geometries": [
      {
        "geometry": {
          "geometry_type": "Point",
          "coordinates": [4.392430, 50.844050]
        }
      }
    ]
  },
  "transit": {
    "optimalization": {
      "road_usage": 1.0
    },
    "desired_vehicle_constraints": {
      "max_speed": 1.3
    }
  }
}
```

## Important Enums

Mission status request:

```text
INIT=0, APPROVE=1, START=2, PAUSE=3, STOP=4, DELETE=5
```

Mission status:

```text
NONE=0, PLANNED=1, PLANNED_ALTERNATIVE=2, PLANNED_FAILED=3,
ACCEPTED=4, STARTED=5, PAUSED=6, FAILED=7, STOPPED=8,
DELETED=9, COMPLETED=10
```

Task request state used between mission manager, fleet manager, and edge:

```text
STOP=0, EXECUTE=1, PAUSE=2, DELETE=3
```

Task state used by the edge:

```text
STOPPED=0, STARTED=1, PAUSED=2, COMPLETED=3, ABORTED=4, DELETED=5
```

## Read Order

For the whole mission path, read:

```text
c2_node -> c2_interface_node -> orchestrator_node -> mission_manager_node
-> planner_node -> fleet_manager_node -> edge_agent_node -> autonomy_sim_node
```

For planner understanding, start with [planner_node.md](planner_node.md), then read the parts of [mission_manager_node.md](mission_manager_node.md) and [fleet_manager_node.md](fleet_manager_node.md) that explain how planner inputs are collected.

The legacy compose stack now runs an idempotent `mapdb-seed` job before starting
the planner. It loads the three valid RMA baseline features into `MapDB.rma`.
`CreatePlanner` also has a readiness guard: it initializes the database-backed
graph synchronously when needed and returns planner error state `4` without
terminating the node if map initialization fails. The complete verified robot
mission is traced in the
[legacy single-robot walkthrough](../LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md).

For task JSON vocabulary, especially `primitive`, `objective`, and `waypoint`, read [primitives.md](primitives.md).
