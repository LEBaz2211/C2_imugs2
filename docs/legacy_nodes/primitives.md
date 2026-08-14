# Task Primitives

> **Documentation label: REFERENCE** — frozen `legacy_ros/` contract evidence.

## Short Version

A primitive is the smallest action unit inside a legacy edge task. The planner builds a task from objectives; each objective contains one or more primitive references. The edge supervisor sends the current objective's primitives to autonomy.

In the current runnable stack:

```text
Real produced/executed primitive: waypoint
Legacy example/concept primitives: search_mine, dispose_mine
```

The current planner only emits `waypoint`. The current autonomy simulator only understands `waypoint`. The edge supervisor has a generic primitive engine, so it can carry other primitive types, but they need a real autonomy implementation that reports their status.

## Where Primitives Sit

```text
MissionConfig
  -> Planner
    -> TaskPlan
      -> tasks[agent_id]
        -> primitives[]   reusable primitive definitions
        -> objectives[]   ordered objective instances
          -> primitives[] references to definitions, with parameters
```

Example shape:

```json
{
  "task_id": "6d2f54a2-a6fd-439a-b5af-a771e53c6e11",
  "primitives": [
    {
      "primitive_id": "c8cab10d-a718-42be-b6ac-4eb496f03d6d",
      "primitive_type": "waypoint",
      "continuous": false,
      "primitive_inputs": [],
      "primitive_outputs": [],
      "completion": {
        "ends_objective": true,
        "ends_task": false,
        "followed_by_primitives": [],
        "inherit_other_primitives": false,
        "resume_after": false
      }
    }
  ],
  "objectives": [
    {
      "objective_id": "31f65b58-e010-4838-9b79-cfb31ef8a84f",
      "objective_type": "combined_primitives",
      "parallel_execution": true,
      "primitives": [
        {
          "primitive_id": "c8cab10d-a718-42be-b6ac-4eb496f03d6d",
          "parameters": {
            "coordinates": [4.392430, 50.844050],
            "speed": 1.3,
            "max_speed": 1.3,
            "mobility_profile": 0,
            "wait_time": 0
          }
        }
      ]
    }
  ]
}
```

The first `primitives[]` array defines what a primitive is. The `objectives[].primitives[]` array says which primitive is active for that objective and supplies or overrides parameters.

## Common Fields

| Field | Meaning |
| --- | --- |
| `primitive_id` | Stable id used to reference the primitive and match autonomy status |
| `primitive_type` | Action type, for example `waypoint` |
| `continuous` | If true, the edge does not wait for this primitive to complete before moving on |
| `primitive_inputs` | Named inputs from previous primitives |
| `primitive_outputs` | Named outputs this primitive may produce |
| `parameters` | Type-specific execution parameters |
| `completion.ends_objective` | Declarative marker that the primitive can end an objective |
| `completion.ends_task` | Declarative marker that the primitive can end the task |
| `completion.followed_by_primitives` | Primitive ids to activate after this primitive completes |
| `completion.inherit_other_primitives` | Intended for carrying primitives into child goals |
| `completion.resume_after` | Return to parent goal after child primitive flow |

The current edge code mainly uses `followed_by_primitives`, `resume_after`, `continuous`, and primitive completion status. `ends_objective` and `ends_task` are parsed but are mostly declarative in the current execution path.

## Primitive Types

### `waypoint`

Status: fully active in the current stack.

Meaning: drive the robot to a coordinate.

Typical parameters:

```json
{
  "coordinates": [4.392430, 50.844050],
  "speed": 1.3,
  "max_speed": 1.3,
  "mobility_profile": 0,
  "wait_time": 0
}
```

Notes:

- Planner task coordinates are `[lon, lat]`.
- The edge sends the waypoint to autonomy in `AutonomySetObjective`.
- The edge can mark it complete by distance to target.
- Current config uses `objective_distance_tolerance: 3.0` meters.
- `wait_time` exists in the payload but waiting behavior is limited in the current path.

### `search_mine`

Status: legacy example/concept, not produced by the current planner and not executed by the current autonomy simulator.

Meaning: search an area/path for mines or contacts using sensors.

Example parameters:

```json
{
  "pattern": "zigzag",
  "swath": 5,
  "sensors": ["emi", "gpr", "stereo_cam"]
}
```

Example outputs:

```json
{
  "primitive_outputs": ["contact"]
}
```

How it would work with a real autonomy module:

```text
1. Edge sends search_mine as a JSON primitive inside AutonomyObjective.
2. Autonomy performs the search.
3. Autonomy publishes AutonomyStatus.primitive_statuses with this primitive_id.
4. Edge sees COMPLETED and activates followed_by_primitives, such as dispose_mine.
```

### `dispose_mine`

Status: legacy example/concept, not produced by the current planner and not executed by the current autonomy simulator.

Meaning: dispose of or interact with a detected mine/contact.

Example parameters:

```json
{
  "grippers": ["robot_front_arm_1"]
}
```

Example input dependency:

```json
{
  "primitive_inputs": [
    {
      "4a4ad006-3d8b-4290-9f62-a9fb07987e07": "contact"
    }
  ]
}
```

In the legacy example, `dispose_mine` follows `search_mine` after a contact is found.

## Execution In The Edge Node

The edge supervisor parses the task like this:

```text
1. Store primitive definitions in primitive_map by primitive_id.
2. For each objective, clone referenced primitives into a start GoalNode.
3. Publish the active GoalNode's primitives to autonomy.
4. Watch autonomy status and local distance checks.
5. When primitives complete, move to child primitives or the next objective.
6. When the final objective completes, mark task_state COMPLETED=3.
```

For `waypoint`, the edge has special local completion logic. For other primitive types, completion depends on autonomy sending `AutonomyPrimitiveStatus` for that primitive id.

## Practical Guidance For The LLM Assistant

For now, the assistant should only generate missions that produce `waypoint` primitives.

Allowed assistant output today:

```text
natural language -> MissionConfig -> legacy planner -> waypoint task plan
```

Do not ask the LLM to generate `search_mine` or `dispose_mine` tasks until a real autonomy implementation and validator exist for them.

The verifier should reject or warn on non-`waypoint` primitives unless the operator explicitly enables experimental primitive types.

## Known Legacy Quirks

- Some old examples contain the misspelled key `primitive_intputs`; current task JSON should use `primitive_inputs`.
- The current autonomy simulator only targets the first `waypoint` primitive found in an objective.
- The current planner does not emit mixed primitive objectives; it emits one waypoint primitive reused across waypoint objectives.
- `search_mine` and `dispose_mine` are useful design hints, not currently safe execution contracts.
