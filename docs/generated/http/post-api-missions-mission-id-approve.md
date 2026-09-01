# POST /api/missions/{mission_id}/approve

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

FastAPI handler `approve`

| Property | Extracted value |
|---|---|
| Kind | `http_endpoint` |
| Method | `POST` |
| Path | `/api/missions/{mission_id}/approve` |
| Handler | `approve` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| approveMission | `—` | [`frontend/src/api.ts:629`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L629) |
| handled by approve | `—` | [`src/c2_imugs2/api/routers.py:208`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L208) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Approve the planned mission

!!! success "Verified Flow"
    Phase: APPROVE.

```json
{
  "path": "/api/missions/44444444-5555-4666-8777-888888888888/approve",
  "body": {}
}
```

- Send only after mission feedback contains a non-empty path and status PLANNED(1).

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:154`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L154)

## Definition evidence

- [`src/c2_imugs2/api/routers.py:208`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L208)
