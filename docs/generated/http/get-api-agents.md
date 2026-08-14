# GET /api/agents

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

FastAPI handler `agents`

| Property | Extracted value |
|---|---|
| Kind | `http_endpoint` |
| Method | `GET` |
| Path | `/api/agents` |
| Handler | `agents` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| handled by agents | `—` | [`src/c2_imugs2/api.py:267`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api.py#L267) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Themis agent returned to the UI adapter

!!! success "Runtime Observed"
    Phase: robot discovery.

```json
{
  "agents": [
    {
      "agent_id": "f9992bb3-9871-451f-90a0-9207eb9fe6c5",
      "name": "Themis Fr",
      "vehicle_type": "UGV",
      "current_location": [
        4.392588,
        50.844317
      ],
      "constraints": {
        "max_speed": 4.5,
        "max_acceleration": 8.0,
        "max_weight": 16.0,
        "max_tilt_angle": 1.8
      },
      "status": "1"
    }
  ]
}
```

- Coordinates are [longitude, latitude].

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`legacy_ros/config/config_autonomy.yaml:6`](https://github.com/LEBaz2211/C2_imugs2/blob/main/legacy_ros/config/config_autonomy.yaml#L6)

## Definition evidence

- [`src/c2_imugs2/api.py:267`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api.py#L267)
