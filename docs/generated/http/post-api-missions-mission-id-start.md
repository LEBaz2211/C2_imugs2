# POST /api/missions/{mission_id}/start

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

FastAPI handler `start`

| Property | Extracted value |
|---|---|
| Kind | `http_endpoint` |
| Method | `POST` |
| Path | `/api/missions/{mission_id}/start` |
| Handler | `start` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| handled by start | `—` | [`src/c2_imugs2/api/routers.py:215`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L215) |
| startMission | `—` | [`frontend/src/api.ts:633`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L633) |

## Verified one-robot navigation data

These payloads come from the [runtime-verified one-robot Point-navigation example](../examples/single-robot-point-navigation.md) using mission `44444444-5555-4666-8777-888888888888` and `Themis Fr`.

### Start the accepted mission

!!! success "Verified Flow"
    Phase: START.

```json
{
  "path": "/api/missions/44444444-5555-4666-8777-888888888888/start",
  "body": {}
}
```

- Send after status ACCEPTED(4) and Edge confirms that the stopped task is installed.

Example evidence: [`fixtures/verified_runs/single_robot_point_navigation.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/fixtures/verified_runs/single_robot_point_navigation.json#L1), [`docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md:164`](https://github.com/LEBaz2211/C2_imugs2/blob/main/docs/LEGACY_SINGLE_ROBOT_MISSION_CODE_WALKTHROUGH.md#L164)

## Definition evidence

- [`src/c2_imugs2/api/routers.py:215`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L215)
