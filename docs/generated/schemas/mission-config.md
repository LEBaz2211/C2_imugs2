# MissionConfig

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

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
| `$.objective.maximum_coverage_distances` | `array` | no | description: Coverage swath widths in metres: one shared value or one value per mission vehicle.; minItems: 1 |
| `$.objective.maximum_coverage_distances[]` | `number` | yes |  |
| `$.objective.arrival_time` | `$ref` | no | $ref: #/$defs/timeWindow |
| `$.mission_end_time` | `string` | no |  |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Canonical mission submitted to the adapter

!!! success "Verified Flow"
    Phase: INIT.

```json
{
  "mission_id": "44444444-5555-4666-8777-888888888888",
  "behavior": 0,
  "vehicles": [
    "f9992bb3-9871-451f-90a0-9207eb9fe6c5"
  ],
  "objective": {
    "geometries": [
      {
        "geometry": {
          "geometry_type": "Point",
          "coordinates": [
            4.39167,
            50.84417
          ]
        }
      }
    ]
  },
  "transit": {
    "optimization": {
      "road_usage": 1.0
    },
    "desired_vehicle_constraints": {
      "max_speed": 1.3
    }
  }
}
```

- The adapter uses canonical optimization; the legacy REST payload below translates it to optimalization.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:108`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L108), [`src/c2_imugs2/legacy_rest.py:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/legacy_rest.py#L1)

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
          "description": "Coverage swath widths in metres: one shared value or one value per mission vehicle.",
          "items": {
            "type": "number",
            "exclusiveMinimum": 0
          },
          "minItems": 1
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
