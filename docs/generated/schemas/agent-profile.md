# AgentProfile

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

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

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Canonical profile for the participating robot

!!! success "Runtime Observed"
    Phase: robot discovery.

```json
{
  "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
  "name": "Themis Fr",
  "vehicle_type": "UGV",
  "status": "1",
  "current_location": [
    4.392588,
    50.844317
  ],
  "constraints": {
    "max_speed": 4.5,
    "max_acceleration": 8.0,
    "max_weight": 16.0,
    "max_tilt_angle": 1.8
  }
}
```

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

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
