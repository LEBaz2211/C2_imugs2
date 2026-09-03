# JSON Schemas

> **Documentation label: GENERATED**
> Static discovery from the editable `backend/`, adapter, frontend, and schemas;
> declarations are not proof of runtime availability. Linked runtime examples are
> separate `legacy_ros` evidence from `docker-compose.legacy-ros.yml` and do not verify the current editable backend.

Schema pages are generated directly from `schemas/*.schema.json`.

| Schema | Title | Required top-level fields |
|---|---|---|
| [agent_profile.schema.json](agent-profile.md) | AgentProfile | agent_id, current_location |
| [map_feature.schema.json](map-feature.md) | MapFeature | feature_id, feature_type, geometry |
| [mission_config.schema.json](mission-config.md) | MissionConfig | mission_id, behavior, vehicles, objective |
| [task_plan.schema.json](task-plan.md) | TaskPlan | mission_id, tasks |
| [vehicle_model.schema.json](vehicle-model.md) | VehicleModel | model_id, label, vehicle_type, constraints, capabilities, revision, created_at, updated_at |
| [world_definition.schema.json](world-definition.md) | WorldDefinition | world_id, name, map, feature_ids, agents, road_imports, revision, created_at, updated_at |
