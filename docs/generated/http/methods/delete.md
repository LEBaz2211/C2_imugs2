# HTTP DELETE

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Routes extracted from FastAPI decorators.

| Contract | Type/details | Evidence |
|---|---|---|
| [DELETE /api/assistant/conversations/{conversation_id}](../delete-api-assistant-conversations-conversation-id.md) | `reset_conversation` | [`src/c2_imugs2/api/routers.py:492`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L492) |
| [DELETE /api/map/features/{feature_id}](../delete-api-map-features-feature-id.md) | `delete_map_feature` | [`src/c2_imugs2/api/app.py:290`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/app.py#L290) |
| [DELETE /api/missions/{mission_id}](../delete-api-missions-mission-id.md) | `forget` | [`src/c2_imugs2/api/routers.py:249`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L249) |
| [DELETE /api/vehicle-models/{model_id}](../delete-api-vehicle-models-model-id.md) | `delete_model` | [`src/c2_imugs2/api/routers.py:383`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L383) |
| [DELETE /api/worlds/active/features/{feature_id}](../delete-api-worlds-active-features-feature-id.md) | `delete_live_feature` | [`src/c2_imugs2/api/routers.py:291`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L291) |
| [DELETE /api/worlds/{world_id}](../delete-api-worlds-world-id.md) | `delete` | [`src/c2_imugs2/api/routers.py:312`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L312) |
| [DELETE /api/worlds/{world_id}/road-imports/{import_id}](../delete-api-worlds-world-id-road-imports-import-id.md) | `delete_road_import` | [`src/c2_imugs2/api/routers.py:343`](https://github.com/LEBaz2211/C2_imugs2/blob/main/src/c2_imugs2/api/routers.py#L343) |
