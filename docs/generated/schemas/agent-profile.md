# AgentProfile

Extracted from `schemas/agent_profile.schema.json` · [`schemas/agent_profile.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/agent_profile.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.agent_id` | `string` | yes |  |
| `$.name` | `string` | no |  |
| `$.vehicle_type` | `string` | no |  |
| `$.status` | `string` | no |  |
| `$.current_location` | `array` | yes | minItems: 2; maxItems: 2 |
| `$.current_location[]` | `number` | yes |  |
| `$.constraints` | `object` | no |  |
| `$.capabilities` | `array` | no |  |
| `$.capabilities[]` | `string` | yes |  |

## Complete extracted schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentProfile",
  "type": "object",
  "required": [
    "agent_id",
    "current_location"
  ],
  "properties": {
    "agent_id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "vehicle_type": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "current_location": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "minItems": 2,
      "maxItems": 2
    },
    "constraints": {
      "type": "object"
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
```
