# HTTP POST

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Routes extracted from FastAPI decorators.

| Contract | Type/details | Evidence |
|---|---|---|
| [POST /api/assistant/messages](../post-api-assistant-messages.md) | `send_message` | [`src/c2_imugs2/api/routers.py:453`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L453) |
| [POST /api/assistant/operational-picture/preview](../post-api-assistant-operational-picture-preview.md) | `operational_picture_preview` | [`src/c2_imugs2/api/routers.py:430`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L430) |
| [POST /api/map/features](../post-api-map-features.md) | `create_map_feature` | [`src/c2_imugs2/api/app.py:272`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L272) |
| [POST /api/missions/init](../post-api-missions-init.md) | `init_mission` | [`src/c2_imugs2/api/routers.py:220`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L220) |
| [POST /api/missions/{mission_id}/approve](../post-api-missions-mission-id-approve.md) | `approve` | [`src/c2_imugs2/api/routers.py:235`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L235) |
| [POST /api/missions/{mission_id}/start](../post-api-missions-mission-id-start.md) | `start` | [`src/c2_imugs2/api/routers.py:242`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L242) |
| [POST /api/testing/reset-legacy-runtime](../post-api-testing-reset-legacy-runtime.md) | `reset_legacy_runtime` | [`src/c2_imugs2/api/app.py:254`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L254) |
| [POST /api/vehicle-models](../post-api-vehicle-models.md) | `create_model` | [`src/c2_imugs2/api/routers.py:369`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L369) |
| [POST /api/worlds](../post-api-worlds.md) | `create` | [`src/c2_imugs2/api/routers.py:266`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L266) |
| [POST /api/worlds/active/features](../post-api-worlds-active-features.md) | `create_live_feature` | [`src/c2_imugs2/api/routers.py:277`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L277) |
| [POST /api/worlds/{world_id}/launch](../post-api-worlds-world-id-launch.md) | `launch` | [`src/c2_imugs2/api/routers.py:319`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L319) |
| [POST /api/worlds/{world_id}/road-imports/query](../post-api-worlds-world-id-road-imports-query.md) | `query_road_import` | [`src/c2_imugs2/api/routers.py:329`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L329) |
