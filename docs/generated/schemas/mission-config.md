# MissionConfig

Extracted from `schemas/mission_config.schema.json` · [`schemas/mission_config.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/mission_config.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.schema_version` | `string` | no |  |
| `$.mission_id` | `string` | yes |  |
| `$.phase` | `integer` | no | minimum: 0 |
| `$.name` | `string` | no |  |
| `$.behavior` | `integer` | yes | enum: 0, 1, 2 |
| `$.vehicles` | `array` | yes | minItems: 1 |
| `$.vehicles[]` | `string` | yes |  |
| `$.start` | `object` | no |  |
| `$.transit` | `object` | no |  |
| `$.objective` | `object` | yes |  |
| `$.objective.geometries` | `array` | yes | minItems: 1 |
| `$.objective.geometries[]` | `$ref` | yes | $ref: #/$defs/geometryRef |
| `$.objective.minimum_distance` | `number` | no |  |
| `$.objective.maximum_distance` | `number` | no |  |
| `$.objective.vehicle_formation` | `integer` | no | enum: 0, 1, 2, 3, 4, 5, 6 |
| `$.objective.vehicle_formation_distance` | `number` | no |  |
| `$.objective.vehicle_orientation` | `array` | no |  |
| `$.objective.vehicle_orientation[]` | `number` | yes |  |
| `$.objective.vehicle_orientation_origin` | `$ref` | no | $ref: #/$defs/geometryRef |
| `$.objective.vehicle_order` | `boolean` | no |  |
| `$.objective.line_of_sight` | `$ref` | no | $ref: #/$defs/geometryRef |
| `$.objective.line_of_sight_propagation` | `boolean` | no |  |
| `$.objective.maximize_coverage` | `boolean` | no |  |
| `$.objective.maximum_coverage_distances` | `array` | no |  |
| `$.objective.maximum_coverage_distances[]` | `number` | yes |  |
| `$.objective.arrival_time` | `$ref` | no | $ref: #/$defs/timeWindow |
| `$.mission_end_time` | `string` | no |  |

## Complete extracted schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MissionConfig",
  "type": "object",
  "required": [
    "mission_id",
    "behavior",
    "vehicles",
    "objective"
  ],
  "properties": {
    "schema_version": {
      "type": "string"
    },
    "mission_id": {
      "type": "string"
    },
    "phase": {
      "type": "integer",
      "minimum": 0
    },
    "name": {
      "type": "string"
    },
    "behavior": {
      "type": "integer",
      "enum": [
        0,
        1,
        2
      ]
    },
    "vehicles": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    },
    "start": {
      "type": "object"
    },
    "transit": {
      "type": "object"
    },
    "objective": {
      "type": "object",
      "required": [
        "geometries"
      ],
      "properties": {
        "geometries": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/geometryRef"
          },
          "minItems": 1
        },
        "minimum_distance": {
          "type": "number"
        },
        "maximum_distance": {
          "type": "number"
        },
        "vehicle_formation": {
          "type": "integer",
          "enum": [
            0,
            1,
            2,
            3,
            4,
            5,
            6
          ]
        },
        "vehicle_formation_distance": {
          "type": "number"
        },
        "vehicle_orientation": {
          "type": "array",
          "items": {
            "type": "number"
          }
        },
        "vehicle_orientation_origin": {
          "$ref": "#/$defs/geometryRef"
        },
        "vehicle_order": {
          "type": "boolean"
        },
        "line_of_sight": {
          "$ref": "#/$defs/geometryRef"
        },
        "line_of_sight_propagation": {
          "type": "boolean"
        },
        "maximize_coverage": {
          "type": "boolean"
        },
        "maximum_coverage_distances": {
          "type": "array",
          "items": {
            "type": "number"
          }
        },
        "arrival_time": {
          "$ref": "#/$defs/timeWindow"
        }
      }
    },
    "mission_end_time": {
      "type": "string"
    }
  },
  "$defs": {
    "geometryRef": {
      "type": "object",
      "oneOf": [
        {
          "required": [
            "feature_id"
          ]
        },
        {
          "required": [
            "geometry"
          ]
        }
      ],
      "properties": {
        "feature_id": {
          "type": "string"
        },
        "geometry": {
          "type": "object",
          "required": [
            "geometry_type",
            "coordinates"
          ],
          "properties": {
            "geometry_type": {
              "type": "string"
            },
            "coordinates": {}
          }
        }
      }
    },
    "timeWindow": {
      "type": "object",
      "required": [
        "earliest",
        "target",
        "latest"
      ],
      "properties": {
        "earliest": {
          "type": "string"
        },
        "target": {
          "type": "string"
        },
        "latest": {
          "type": "string"
        }
      }
    }
  }
}
```
