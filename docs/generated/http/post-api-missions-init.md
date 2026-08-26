# POST /api/missions/init

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

FastAPI handler `init_mission`

| Property | Extracted value |
|---|---|
| Kind | `http_endpoint` |
| Method | `POST` |
| Path | `/api/missions/init` |
| Handler | `init_mission` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| handled by init_mission | `—` | [`src/c2_imugs2/api_routers.py:166`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api_routers.py#L166) |
| initMission | `—` | [`frontend/src/api.ts:597`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L597) |

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

## Definition evidence

- [`src/c2_imugs2/api_routers.py:166`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api_routers.py#L166)
