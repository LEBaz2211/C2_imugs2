# WorldDefinition

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Extracted from `schemas/world_definition.schema.json` · [`schemas/world_definition.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/world_definition.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.world_id` | `string` | yes |  |
| `$.name` | `string` | yes |  |
| `$.map` | `string` | yes |  |
| `$.notes` | `string` | no |  |
| `$.feature_ids` | `array` | yes |  |
| `$.feature_ids[]` | `string` | yes |  |
| `$.agents` | `array` | yes |  |
| `$.agents[]` | `object` | yes |  |
| `$.agents[].agent_id` | `string` | yes |  |
| `$.agents[].name` | `string` | yes |  |
| `$.agents[].vehicle_type` | `string` | yes |  |
| `$.agents[].current_location` | `array` | no | minItems: 2; maxItems: 2 |
| `$.agents[].current_location[]` | `number` | yes |  |
| `$.agents[].constraints` | `object` | no |  |
| `$.agents[].capabilities` | `array` | no |  |
| `$.agents[].capabilities[]` | `string` | yes |  |
| `$.road_imports` | `array` | yes |  |
| `$.road_imports[]` | `object` | yes |  |
| `$.road_imports[].import_id` | `string` | yes |  |
| `$.road_imports[].name` | `string` | yes |  |
| `$.road_imports[].feature_count` | `integer` | yes | minimum: 0 |
| `$.road_imports[].bbox` | `array` | no | minItems: 4; maxItems: 4 |
| `$.road_imports[].bbox[]` | `number` | yes |  |
| `$.road_imports[].created_at` | `string` | yes |  |
| `$.road_imports[].geojson` | `object` | no |  |
| `$.map_view` | `['object', 'null']` | no |  |
| `$.map_view.center` | `array` | yes | minItems: 2; maxItems: 2 |
| `$.map_view.center[]` | `number` | yes |  |
| `$.map_view.zoom` | `number` | yes |  |
| `$.revision` | `integer` | yes | minimum: 1 |
| `$.created_at` | `string` | yes |  |
| `$.updated_at` | `string` | yes |  |

## Complete extracted schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://c2-imugs2.local/schemas/world_definition.schema.json",
  "title": "WorldDefinition",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "world_id",
    "name",
    "map",
    "feature_ids",
    "agents",
    "road_imports",
    "revision",
    "created_at",
    "updated_at"
  ],
  "properties": {
    "world_id": {
      "type": "string",
      "minLength": 1
    },
    "name": {
      "type": "string",
      "minLength": 1
    },
    "map": {
      "type": "string",
      "minLength": 1
    },
    "notes": {
      "type": "string"
    },
    "feature_ids": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "agents": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "agent_id",
          "name",
          "vehicle_type"
        ],
        "properties": {
          "agent_id": {
            "type": "string",
            "minLength": 1
          },
          "name": {
            "type": "string",
            "minLength": 1
          },
          "vehicle_type": {
            "type": "string",
            "minLength": 1
          },
          "current_location": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {
              "type": "number"
            }
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
        },
        "additionalProperties": true
      }
    },
    "road_imports": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "import_id",
          "name",
          "feature_count",
          "created_at"
        ],
        "properties": {
          "import_id": {
            "type": "string",
            "minLength": 1
          },
          "name": {
            "type": "string",
            "minLength": 1
          },
          "feature_count": {
            "type": "integer",
            "minimum": 0
          },
          "bbox": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
              "type": "number"
            }
          },
          "created_at": {
            "type": "string"
          },
          "geojson": {
            "type": "object"
          }
        },
        "additionalProperties": false
      }
    },
    "map_view": {
      "type": [
        "object",
        "null"
      ],
      "required": [
        "center",
        "zoom"
      ],
      "properties": {
        "center": {
          "type": "array",
          "minItems": 2,
          "maxItems": 2,
          "items": {
            "type": "number"
          }
        },
        "zoom": {
          "type": "number"
        }
      },
      "additionalProperties": false
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
