# MapFeature

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Extracted from `schemas/map_feature.schema.json` · [`schemas/map_feature.schema.json:1`](https://github.com/LEBaz2211/C2_imugs2/blob/main/schemas/map_feature.schema.json#L1)

| JSON path | Type | Required | Constraints / description |
|---|---|---|---|
| `$` | `object` | yes |  |
| `$.feature_id` | `string` | yes |  |
| `$.name` | `string` | no |  |
| `$.feature_type` | `string` | yes |  |
| `$.geometry` | `object` | yes |  |
| `$.properties` | `object` | no |  |

## Complete extracted schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MapFeature",
  "type": "object",
  "required": [
    "feature_id",
    "feature_type",
    "geometry"
  ],
  "properties": {
    "feature_id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "feature_type": {
      "type": "string"
    },
    "geometry": {
      "type": "object"
    },
    "properties": {
      "type": "object"
    }
  }
}
```
