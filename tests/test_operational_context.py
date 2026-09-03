from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from c2_imugs2.operations.service import (
    FullSnapshotReason,
    OperationalContextService,
    OperationalUpdate,
    OperationalUpdateError,
    UpdateMode,
    materialize_operational_update,
)
from c2_imugs2.operations.models import (
    OPERATIONAL_SECTION_NAMES,
    Freshness,
    OperationalItem,
    OperationalPictureValidationError,
    OperationalReadModel,
    OperationalSection,
    SectionMetadata,
    SourceReference,
)
from c2_imugs2.operations.live import (
    LiveOperationalReadModelProvider,
    MongoOperationalSnapshot,
)


NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
SOURCE_ID = "RuntimeDB.MissionFeedback/latest"


class MutableProvider:
    def __init__(self, model: OperationalReadModel) -> None:
        self.model = model
        self.calls = 0

    def read_operational_model(self) -> OperationalReadModel:
        self.calls += 1
        return self.model


def item(
    item_id: str,
    kind: str,
    data: dict,
    *,
    observed_at: datetime = NOW,
    freshness: Freshness = Freshness.FRESH,
) -> OperationalItem:
    return OperationalItem(
        item_id=item_id,
        kind=kind,
        observed_at=observed_at,
        freshness=freshness,
        source_ids=(SOURCE_ID,),
        data=data,
    )


def model(
    *,
    observed_at: datetime = NOW,
    schema_version: str = "1.0",
    agent: OperationalItem | None = None,
    mission: OperationalItem | None = None,
    warning: OperationalItem | None = None,
) -> OperationalReadModel:
    source = SourceReference(
        source_id=SOURCE_ID,
        kind="mongo",
        observed_at=NOW,
        freshness=Freshness.FRESH,
        details={"database": "RuntimeDB", "bounded": True},
    )
    sections = {
        name: OperationalSection.empty(
            NOW,
            freshness=Freshness.FRESH,
            source_ids=(SOURCE_ID,),
        )
        for name in OPERATIONAL_SECTION_NAMES
    }
    sections["world"] = OperationalSection(
        metadata=sections["world"].metadata,
        items={
            "world-a@v1": item(
                "world-a@v1",
                "active_world",
                {
                    "world_id": "world-a",
                    "world_version": "v1",
                    "status": "ready",
                    "map_collection": "world_a_v1",
                },
            )
        },
    )
    if agent is not None:
        sections["agents"] = OperationalSection(
            metadata=sections["agents"].metadata,
            items={agent.item_id: agent},
        )
    if mission is not None:
        sections["missions"] = OperationalSection(
            metadata=sections["missions"].metadata,
            items={mission.item_id: mission},
        )
    if warning is not None:
        sections["warnings"] = OperationalSection(
            metadata=sections["warnings"].metadata,
            items={warning.item_id: warning},
        )
    return OperationalReadModel(
        schema_version=schema_version,
        observed_at=observed_at,
        sections=sections,
        sources={SOURCE_ID: source},
    )


def test_first_update_is_full_and_round_trips_with_source_freshness() -> None:
    provider = MutableProvider(
        model(agent=item("robot-1", "agent", {"connectivity": "connected"}))
    )
    service = OperationalContextService(provider, runtime_id="runtime-a", history_limit=4)

    update = service.get_operational_update()

    assert update.mode is UpdateMode.FULL
    assert update.reason is FullSnapshotReason.INITIAL
    assert update.picture_revision == "runtime-a:1"
    assert update.picture is not None
    assert update.picture.sections["agents"].metadata.freshness is Freshness.FRESH
    assert update.picture.sources[SOURCE_ID].details["database"] == "RuntimeDB"

    transported = OperationalUpdate.from_dict(update.to_dict())
    materialized = materialize_operational_update(None, transported)
    assert materialized.to_dict() == update.picture.to_dict()


def test_unchanged_read_model_reuses_revision_and_emits_empty_delta() -> None:
    provider = MutableProvider(model())
    service = OperationalContextService(provider, runtime_id="runtime-a")
    first = service.get_operational_update()

    provider.model = model(observed_at=NOW + timedelta(seconds=30))

    second = service.get_operational_update(
        first.picture_revision,
        since_checksum=first.picture_checksum,
    )

    assert provider.calls == 2
    assert second.mode is UpdateMode.DELTA
    assert second.base_revision == first.picture_revision
    assert second.picture_revision == first.picture_revision
    assert second.observed_at == first.observed_at
    assert second.picture_checksum == first.picture_checksum
    assert second.changed == {}
    assert second.removed == ()
    assert service.retained_revisions == (first.picture_revision,)
    base = materialize_operational_update(None, first)
    assert materialize_operational_update(base, second).to_dict() == base.to_dict()


def test_delta_replaces_stable_keyed_items_and_materializes_target() -> None:
    old_agent = item("robot/1", "agent", {"connectivity": "connected", "tags": ["ugv"]})
    old_mission = item("mission-1", "mission", {"status": "PLANNED"})
    provider = MutableProvider(model(agent=old_agent, mission=old_mission))
    service = OperationalContextService(provider, runtime_id="runtime-a", history_limit=4)
    first = service.get_operational_update()
    base = materialize_operational_update(None, first)

    later = NOW + timedelta(seconds=5)
    new_agent = item(
        "robot/1",
        "agent",
        {"connectivity": "disconnected", "tags": ["ugv", "missing"]},
        observed_at=later,
        freshness=Freshness.STALE,
    )
    warning = item(
        "planner~waiting",
        "warning",
        {"severity": "warning", "message": "Planner is waiting for a robot"},
        observed_at=later,
    )
    target_sections = dict(base.sections)
    target_sections["agents"] = OperationalSection(
        metadata=SectionMetadata(
            observed_at=later,
            freshness=Freshness.STALE,
            source_ids=(SOURCE_ID,),
        ),
        items={new_agent.item_id: new_agent},
    )
    target_sections["missions"] = OperationalSection(
        metadata=base.sections["missions"].metadata,
        items={},
    )
    target_sections["warnings"] = OperationalSection(
        metadata=base.sections["warnings"].metadata,
        items={warning.item_id: warning},
    )
    provider.model = OperationalReadModel(
        schema_version="1.0",
        observed_at=later,
        sections=target_sections,
        sources=base.sources,
    )

    delta = service.get_operational_update(
        base.picture_revision,
        since_checksum=base.checksum,
    )
    delta = OperationalUpdate.from_dict(delta.to_dict())

    assert delta.mode is UpdateMode.DELTA
    assert list(delta.changed) == sorted(delta.changed)
    assert "agents/robot~11" in delta.changed
    assert "section_metadata/agents" in delta.changed
    assert "warnings/planner~0waiting" in delta.changed
    assert delta.removed == ("missions/mission-1",)
    assert delta.changed["agents/robot~11"]["data"] == {
        "connectivity": "disconnected",
        "tags": ["ugv", "missing"],
    }
    assert [source.source_id for source in delta.sources] == [SOURCE_ID]

    materialized = materialize_operational_update(base, delta)
    expected = provider.model.to_dict()
    assert materialized.to_read_model().to_dict() == expected
    assert materialized.picture_revision == "runtime-a:2"


def test_compacted_or_foreign_revision_falls_back_to_full_picture() -> None:
    provider = MutableProvider(model())
    service = OperationalContextService(provider, runtime_id="runtime-a", history_limit=2)
    first = service.get_operational_update()

    provider.model = model(
        observed_at=NOW + timedelta(seconds=1),
        mission=item(
            "mission-1",
            "mission",
            {"status": "PLANNED"},
            observed_at=NOW + timedelta(seconds=1),
        ),
    )
    second = service.get_operational_update(first.picture_revision)
    assert second.mode is UpdateMode.DELTA

    provider.model = model(
        observed_at=NOW + timedelta(seconds=2),
        mission=item(
            "mission-1",
            "mission",
            {"status": "STARTED"},
            observed_at=NOW + timedelta(seconds=2),
        ),
    )
    compacted = service.get_operational_update(first.picture_revision)
    assert compacted.mode is UpdateMode.FULL
    assert compacted.reason is FullSnapshotReason.BASE_REVISION_UNAVAILABLE
    assert service.retained_revisions == ("runtime-a:2", "runtime-a:3")

    foreign = service.get_operational_update("another-runtime:9")
    assert foreign.mode is UpdateMode.FULL
    assert foreign.reason is FullSnapshotReason.RUNTIME_MISMATCH


def test_checksum_or_schema_mismatch_falls_back_to_full_picture() -> None:
    provider = MutableProvider(model())
    service = OperationalContextService(provider, runtime_id="runtime-a")
    first = service.get_operational_update()

    checksum_recovery = service.get_operational_update(
        first.picture_revision,
        since_checksum="0" * 64,
    )
    assert checksum_recovery.mode is UpdateMode.FULL
    assert checksum_recovery.reason is FullSnapshotReason.CHECKSUM_MISMATCH

    provider.model = model(
        observed_at=NOW + timedelta(seconds=1),
        schema_version="2.0",
    )
    schema_recovery = service.get_operational_update(first.picture_revision)
    assert schema_recovery.mode is UpdateMode.FULL
    assert schema_recovery.reason is FullSnapshotReason.SCHEMA_VERSION_MISMATCH


def test_materializer_rejects_base_and_result_checksum_mismatches() -> None:
    provider = MutableProvider(model())
    service = OperationalContextService(provider, runtime_id="runtime-a")
    first = service.get_operational_update()
    base = materialize_operational_update(None, first)
    provider.model = model(observed_at=NOW + timedelta(seconds=1))
    delta = service.get_operational_update(base.picture_revision)

    with pytest.raises(OperationalUpdateError, match="without a materialized base"):
        materialize_operational_update(None, delta)

    bad_checksum = OperationalUpdate(
        schema_version=delta.schema_version,
        mode=delta.mode,
        base_revision=delta.base_revision,
        picture_revision=delta.picture_revision,
        observed_at=delta.observed_at,
        picture_checksum="f" * 64,
        changed=delta.changed,
        removed=delta.removed,
        sources=delta.sources,
    )
    with pytest.raises(OperationalUpdateError, match="checksum"):
        materialize_operational_update(base, bad_checksum)


def test_read_model_rejects_unknown_sources_and_non_json_payloads() -> None:
    sections = {
        name: OperationalSection.empty(NOW, freshness=Freshness.FRESH)
        for name in OPERATIONAL_SECTION_NAMES
    }
    sections["agents"] = OperationalSection(
        metadata=sections["agents"].metadata,
        items={
            "robot-1": OperationalItem(
                item_id="robot-1",
                kind="agent",
                observed_at=NOW,
                freshness=Freshness.FRESH,
                source_ids=("missing-source",),
                data={},
            )
        },
    )
    with pytest.raises(OperationalPictureValidationError, match="unknown sources"):
        OperationalReadModel(
            schema_version="1.0",
            observed_at=NOW,
            sections=sections,
            sources={},
        )

    with pytest.raises(OperationalPictureValidationError, match="non-JSON"):
        OperationalItem(
            item_id="robot-1",
            kind="agent",
            observed_at=NOW,
            freshness=Freshness.FRESH,
            data={"bad": object()},
        )


def test_live_world_item_key_includes_immutable_version() -> None:
    active = {
        "world_id": "world-a",
        "world_version": "7f2c",
        "status": "ready",
        "ready": True,
        "agents": [],
    }

    provider = object.__new__(LiveOperationalReadModelProvider)
    provider.map_feature_limit = 64
    provider.map_coordinate_limit = 128
    provider.map_total_coordinate_limit = 512
    section = provider._world_section(NOW, active, MongoOperationalSnapshot())

    assert list(section.items) == ["world-a@7f2c"]
    world = section.items["world-a@7f2c"]
    assert world.data["world_id"] == "world-a"
    assert world.data["world_version"] == "7f2c"
    assert world.data["map_feature_observation"]["freshness"] == "missing"
    assert world.freshness is Freshness.STALE
