# VehicleModel

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Extracted from `schemas/vehicle_model.schema.json` · [`schemas/vehicle_model.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/vehicle_model.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.model_id` | `string` | yes |  |
| `$.label` | `string` | yes |  |
| `$.vehicle_type` | `string` | yes |  |
| `$.constraints` | `object` | yes |  |
| `$.capabilities` | `array` | yes |  |
| `$.capabilities[]` | `string` | yes |  |
| `$.default_name` | `string` | no |  |
| `$.revision` | `integer` | yes | minimum: 1 |
| `$.created_at` | `string` | yes |  |
| `$.updated_at` | `string` | yes |  |

## Complete extracted schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://c2-imugs2.local/schemas/vehicle_model.schema.json",
  "title": "VehicleModel",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "model_id",
    "label",
    "vehicle_type",
    "constraints",
    "capabilities",
    "revision",
    "created_at",
    "updated_at"
  ],
  "properties": {
    "model_id": {
      "type": "string",
      "minLength": 1
    },
    "label": {
      "type": "string",
      "minLength": 1
    },
    "vehicle_type": {
      "type": "string",
      "minLength": 1
    },
    "constraints": {
      "type": "object"
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "uniqueItems": true
    },
    "default_name": {
      "type": "string"
    },
    "revision": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string"
    },
    "updated_at": {
      "type": "string"
    }
  }
}
```
