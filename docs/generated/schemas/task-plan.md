# TaskPlan

Extracted from `schemas/task_plan.schema.json` · [`schemas/task_plan.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/task_plan.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.mission_id` | `string` | yes |  |
| `$.tasks` | `object` | yes |  |

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
