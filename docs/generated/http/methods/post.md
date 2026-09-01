# HTTP POST

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Routes extracted from FastAPI decorators.

| Contract | Type/details | Evidence |
|---|---|---|
| [POST /api/assistant/messages](../post-api-assistant-messages.md) | `send_message` | [`src/c2_imugs2/api/routers.py:330`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L330) |
| [POST /api/assistant/operational-picture/preview](../post-api-assistant-operational-picture-preview.md) | `operational_picture_preview` | [`src/c2_imugs2/api/routers.py:307`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L307) |
| [POST /api/map/features](../post-api-map-features.md) | `create_map_feature` | [`src/c2_imugs2/api/app.py:274`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L274) |
| [POST /api/map/osm-roads/query](../post-api-map-osm-roads-query.md) | `query_osm_roads` | [`src/c2_imugs2/api/app.py:320`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L320) |
| [POST /api/missions/init](../post-api-missions-init.md) | `init_mission` | [`src/c2_imugs2/api/routers.py:209`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L209) |
| [POST /api/missions/{mission_id}/approve](../post-api-missions-mission-id-approve.md) | `approve` | [`src/c2_imugs2/api/routers.py:224`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L224) |
| [POST /api/missions/{mission_id}/start](../post-api-missions-mission-id-start.md) | `start` | [`src/c2_imugs2/api/routers.py:231`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L231) |
| [POST /api/scenarios/activate](../post-api-scenarios-activate.md) | `activate` | [`src/c2_imugs2/api/routers.py:260`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L260) |
| [POST /api/scenarios/launch](../post-api-scenarios-launch.md) | `activate` | [`src/c2_imugs2/api/routers.py:260`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L260) |
| [POST /api/testing/reset-legacy-runtime](../post-api-testing-reset-legacy-runtime.md) | `reset_legacy_runtime` | [`src/c2_imugs2/api/app.py:256`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L256) |
