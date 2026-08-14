# TaskPlan

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Extracted from `schemas/task_plan.schema.json` · [`schemas/task_plan.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/task_plan.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.mission_id` | `string` | yes |  |
| `$.tasks` | `object` | yes |  |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Observed 10-waypoint plan (recorded coordinate excerpt)

!!! warning "Observed Excerpt"
    Phase: plan retrieval.

```json
{
  "mission_id": "44444444-5555-4666-8777-888888888888",
  "tasks": {
    "f9992bb3-9871-451f-90a0-9207eb9fe6c5": {
      "task_id": "<generated-task-uuid>",
      "primitives": [
        {
          "primitive_id": "<generated-primitive-uuid>",
          "primitive_type": "waypoint",
          "completion": {
            "ends_objective": true,
            "ends_task": false
          }
        }
      ],
      "objectives": [
        {
          "objective_id": "<first-generated-objective-uuid>",
          "parallel_execution": true,
          "primitives": [
            {
              "primitive_id": "<generated-primitive-uuid>",
              "parameters": {
                "coordinates": [
                  4.3925979,
                  50.8443434
                ],
                "speed": 1.3,
                "max_speed": 1.3
              }
            }
          ]
        },
        {
          "objective_id": "<second-generated-objective-uuid>",
          "parallel_execution": true,
          "primitives": [
            {
              "primitive_id": "<generated-primitive-uuid>",
              "parameters": {
                "coordinates": [
                  4.3923021488298595,
                  50.8442681286928
                ],
                "speed": 1.3,
                "max_speed": 1.3
              }
            }
          ]
        },
        {
          "objective_id": "<final-generated-objective-uuid>",
          "parallel_execution": true,
          "primitives": [
            {
              "primitive_id": "<generated-primitive-uuid>",
              "parameters": {
                "coordinates": [
                  4.391670213379427,
                  50.84417059346137
                ],
                "speed": 1.3,
                "max_speed": 1.3
              }
            }
          ]
        }
      ]
    }
  }
}
```

- This is deliberately an excerpt: the verified route contained 10 objectives, while the runtime record preserved in the walkthrough names the first two and final coordinates.
- Generated task, primitive, and objective UUIDs change on every GetPlan serialization.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:599`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L599)

## Complete extracted schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TaskPlan",
  "type": "object",
  "required": [
    "mission_id",
    "tasks"
  ],
  "properties": {
    "mission_id": {
      "type": "string"
    },
    "tasks": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": [
          "task_id",
          "primitives",
          "objectives"
        ],
        "properties": {
          "task_id": {
            "type": "string"
          },
          "primitives": {
            "type": "array"
          },
          "objectives": {
            "type": "array"
          }
        }
      }
    }
  }
}
```
