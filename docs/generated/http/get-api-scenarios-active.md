# GET /api/scenarios/active

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

FastAPI handler `active_scenario_runtime`

| Property | Extracted value |
|---|---|
| Kind | `http_endpoint` |
| Method | `GET` |
| Path | `/api/scenarios/active` |
| Handler | `active_scenario_runtime` |

## Source usages

| Relationship | Contract | Evidence |
|---|---|---|
| getActiveScenario | `—` | [`frontend/src/api.ts:448`](https://github.com/LEBaz2211/C2_imugs2/blob/main/frontend/src/api.ts#L448) |
| handled by active_scenario_runtime | `—` | [`src/c2_imugs2/api.py:244`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api.py#L244) |

## Definition evidence

- [`src/c2_imugs2/api.py:244`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api.py#L244)
