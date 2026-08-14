# GET /api/missions/{mission_id}

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

FastAPI handler `mission_runtime_state`

| Property | Extracted value |
|---|---|
| Kind | `http_endpoint` |
| Method | `GET` |
| Path | `/api/missions/{mission_id}` |
| Handler | `mission_runtime_state` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| getMissionState | `—` | [`frontend/src/api.ts:497`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L497) |
| handled by mission_runtime_state | `—` | [`src/c2_imugs2/api.py:358`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api.py#L358) |

## Definition evidence

- [`src/c2_imugs2/api.py:358`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api.py#L358)
