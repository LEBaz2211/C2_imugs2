from __future__ import annotations

import json
import re
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Protocol

from .operational_picture import (
    OPERATIONAL_SECTION_NAMES,
    OperationalItem,
    OperationalPicture,
    OperationalPictureValidationError,
    OperationalReadModel,
    OperationalSection,
    SectionMetadata,
    SourceReference,
    _json_value,
    _timestamp,
    _utc_datetime,
)


_RUNTIME_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_CHECKSUM_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class OperationalUpdateError(ValueError):
    """Raised when a full picture or delta cannot be safely materialized."""


class UpdateMode(str, Enum):
    FULL = "full"
    DELTA = "delta"


class FullSnapshotReason(str, Enum):
    INITIAL = "initial"
    BASE_REVISION_UNAVAILABLE = "base_revision_unavailable"
    RUNTIME_MISMATCH = "runtime_mismatch"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    SCHEMA_VERSION_MISMATCH = "schema_version_mismatch"


class OperationalReadModelProvider(Protocol):
    """Infrastructure adapter that returns one normalized, bounded read model."""

    def read_operational_model(self) -> OperationalReadModel: ...


def _escape_path_segment(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _unescape_path_segment(value: str) -> str:
    index = 0
    while index < len(value):
        if value[index] == "~":
            if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
                raise OperationalUpdateError(f"invalid escaped update path segment: {value!r}")
            index += 2
        else:
            index += 1
    return value.replace("~1", "/").replace("~0", "~")


def _parse_path(path: str) -> tuple[str, str]:
    if not isinstance(path, str) or not path:
        raise OperationalUpdateError("update paths must be non-empty strings")
    parts = path.split("/")
    if len(parts) != 2:
        raise OperationalUpdateError(
            f"update path {path!r} must replace one documented object boundary"
        )
    collection = _unescape_path_segment(parts[0])
    key = _unescape_path_segment(parts[1])
    if not key:
        raise OperationalUpdateError(f"update path {path!r} has an empty key")
    if collection == "section_metadata":
        if key not in OPERATIONAL_SECTION_NAMES:
            raise OperationalUpdateError(f"unknown section metadata path: {path!r}")
    elif collection not in {*OPERATIONAL_SECTION_NAMES, "sources"}:
        raise OperationalUpdateError(f"unknown operational update collection: {collection!r}")
    return collection, key


def _normalized_changed(value: object) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise OperationalUpdateError("changed must be an object keyed by update path")
    if any(not isinstance(path, str) for path in value):
        raise OperationalUpdateError("changed must use string update paths")
    changed: dict[str, dict[str, Any]] = {}
    for path in sorted(value):
        _parse_path(path)
        try:
            normalized = _json_value(value[path], f"changed.{path}")
        except OperationalPictureValidationError as exc:
            raise OperationalUpdateError(str(exc)) from exc
        if not isinstance(normalized, dict):
            raise OperationalUpdateError(f"changed value for {path!r} must be an object")
        changed[path] = normalized
    return changed


def _normalized_removed(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise OperationalUpdateError("removed must be a list or tuple of update paths")
    removed = []
    for path in value:
        if not isinstance(path, str):
            raise OperationalUpdateError("removed must contain string update paths")
        collection, _ = _parse_path(path)
        if collection == "section_metadata":
            raise OperationalUpdateError("required section metadata cannot be removed")
        removed.append(path)
    if len(set(removed)) != len(removed):
        raise OperationalUpdateError("removed must not contain duplicate paths")
    return tuple(sorted(removed))


@dataclass(frozen=True)
class OperationalUpdate:
    schema_version: str
    mode: UpdateMode
    picture_revision: str
    observed_at: datetime
    picture_checksum: str
    base_revision: str | None = None
    changed: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    removed: tuple[str, ...] = ()
    sources: tuple[SourceReference, ...] = ()
    picture: OperationalPicture | None = None
    reason: FullSnapshotReason | None = None

    def __post_init__(self) -> None:
        try:
            mode = self.mode if isinstance(self.mode, UpdateMode) else UpdateMode(self.mode)
        except (TypeError, ValueError) as exc:
            raise OperationalUpdateError("mode must be 'full' or 'delta'") from exc
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise OperationalUpdateError("schema_version must be a non-empty string")
        if not isinstance(self.picture_revision, str) or not self.picture_revision:
            raise OperationalUpdateError("picture_revision must be a non-empty string")
        try:
            observed_at = _utc_datetime(self.observed_at)
        except OperationalPictureValidationError as exc:
            raise OperationalUpdateError(str(exc)) from exc
        if not isinstance(self.picture_checksum, str) or not _CHECKSUM_PATTERN.fullmatch(
            self.picture_checksum
        ):
            raise OperationalUpdateError("picture_checksum must be a lowercase SHA-256 digest")
        changed = _normalized_changed(self.changed)
        removed = _normalized_removed(self.removed)
        overlap = sorted(set(changed) & set(removed))
        if overlap:
            raise OperationalUpdateError(
                f"paths cannot be both changed and removed: {', '.join(overlap)}"
            )
        if not isinstance(self.sources, (list, tuple)):
            raise OperationalUpdateError("sources must be a list or tuple")
        sources_by_id: dict[str, SourceReference] = {}
        for source in self.sources:
            if not isinstance(source, SourceReference):
                raise OperationalUpdateError("sources must contain SourceReference values")
            if source.source_id in sources_by_id:
                raise OperationalUpdateError("sources must not contain duplicate source ids")
            sources_by_id[source.source_id] = source
        sources = tuple(sources_by_id[source_id] for source_id in sorted(sources_by_id))

        reason = self.reason
        if reason is not None and not isinstance(reason, FullSnapshotReason):
            try:
                reason = FullSnapshotReason(reason)
            except (TypeError, ValueError) as exc:
                raise OperationalUpdateError("unknown full snapshot reason") from exc

        if mode is UpdateMode.FULL:
            if self.base_revision is not None:
                raise OperationalUpdateError("a full update must not have base_revision")
            if changed or removed:
                raise OperationalUpdateError("a full update must not contain changed or removed paths")
            if not isinstance(self.picture, OperationalPicture):
                raise OperationalUpdateError("a full update must contain an OperationalPicture")
            if self.picture.picture_revision != self.picture_revision:
                raise OperationalUpdateError("full update revision does not match its picture")
            if self.picture.schema_version != self.schema_version:
                raise OperationalUpdateError("full update schema version does not match its picture")
            if self.picture.observed_at != observed_at:
                raise OperationalUpdateError("full update timestamp does not match its picture")
            if self.picture.checksum != self.picture_checksum:
                raise OperationalUpdateError("full update checksum does not match its picture")
            expected_sources = tuple(
                self.picture.sources[source_id]
                for source_id in sorted(self.picture.sources)
            )
            if sources != expected_sources:
                raise OperationalUpdateError(
                    "full update source references do not match its picture"
                )
            if reason is None:
                raise OperationalUpdateError("a full update must explain why recovery was required")
        else:
            if not isinstance(self.base_revision, str) or not self.base_revision:
                raise OperationalUpdateError("a delta update must have base_revision")
            if self.picture is not None:
                raise OperationalUpdateError("a delta update must not contain a full picture")
            if reason is not None:
                raise OperationalUpdateError("a delta update must not have a full snapshot reason")

        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "changed", changed)
        object.__setattr__(self, "removed", removed)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "reason", reason)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "mode": self.mode.value,
            "base_revision": self.base_revision,
            "picture_revision": self.picture_revision,
            "observed_at": _timestamp(self.observed_at),
            "picture_checksum": self.picture_checksum,
            "changed": dict(self.changed),
            "removed": list(self.removed),
            "sources": [source.to_dict() for source in self.sources],
        }
        if self.picture is not None:
            result["picture"] = self.picture.to_dict()
        if self.reason is not None:
            result["reason"] = self.reason.value
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperationalUpdate":
        if not isinstance(data, Mapping):
            raise OperationalUpdateError("OperationalUpdate must be an object")
        if any(not isinstance(key, str) for key in data):
            raise OperationalUpdateError("OperationalUpdate must use string field names")
        allowed = {
            "schema_version",
            "mode",
            "base_revision",
            "picture_revision",
            "observed_at",
            "picture_checksum",
            "changed",
            "removed",
            "sources",
            "picture",
            "reason",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise OperationalUpdateError(f"OperationalUpdate has unknown fields: {', '.join(unknown)}")
        required = {
            "schema_version",
            "mode",
            "picture_revision",
            "observed_at",
            "picture_checksum",
        }
        missing = sorted(required - set(data))
        if missing:
            raise OperationalUpdateError(f"OperationalUpdate is missing fields: {', '.join(missing)}")
        raw_sources = data.get("sources", ())
        if not isinstance(raw_sources, (list, tuple)):
            raise OperationalUpdateError("sources must be an array")
        raw_picture = data.get("picture")
        try:
            return cls(
                schema_version=data["schema_version"],
                mode=data["mode"],
                base_revision=data.get("base_revision"),
                picture_revision=data["picture_revision"],
                observed_at=data["observed_at"],
                picture_checksum=data["picture_checksum"],
                changed=data.get("changed", {}),
                removed=data.get("removed", ()),
                sources=tuple(SourceReference.from_dict(source) for source in raw_sources),
                picture=(
                    OperationalPicture.from_dict(raw_picture)
                    if raw_picture is not None
                    else None
                ),
                reason=data.get("reason"),
            )
        except OperationalPictureValidationError as exc:
            raise OperationalUpdateError(str(exc)) from exc


def _flatten_picture(picture: OperationalPicture) -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    for section_name in OPERATIONAL_SECTION_NAMES:
        section = picture.sections[section_name]
        metadata_path = f"section_metadata/{_escape_path_segment(section_name)}"
        flattened[metadata_path] = section.metadata.to_dict()
        for item_id, item in section.items.items():
            item_path = f"{_escape_path_segment(section_name)}/{_escape_path_segment(item_id)}"
            flattened[item_path] = item.to_dict()
    for source_id, source in picture.sources.items():
        source_path = f"sources/{_escape_path_segment(source_id)}"
        flattened[source_path] = source.to_dict()
    return {path: flattened[path] for path in sorted(flattened)}


def _diff_pictures(
    base: OperationalPicture, target: OperationalPicture
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    base_values = _flatten_picture(base)
    target_values = _flatten_picture(target)
    changed = {
        path: target_values[path]
        for path in sorted(target_values)
        if path not in base_values or target_values[path] != base_values[path]
    }
    removed = tuple(sorted(path for path in base_values if path not in target_values))
    return changed, removed


def _sources_for_changed_values(
    target: OperationalPicture, changed: Mapping[str, Mapping[str, Any]]
) -> tuple[SourceReference, ...]:
    source_ids: set[str] = set()
    for path, value in changed.items():
        collection, key = _parse_path(path)
        if collection == "sources":
            source_ids.add(key)
        raw_ids = value.get("source_ids", ())
        if isinstance(raw_ids, list):
            source_ids.update(source_id for source_id in raw_ids if isinstance(source_id, str))
    return tuple(target.sources[source_id] for source_id in sorted(source_ids) if source_id in target.sources)


def materialize_operational_update(
    current: OperationalPicture | None, update: OperationalUpdate
) -> OperationalPicture:
    """Apply an update and validate the resulting full operational picture.

    Callers should request a full update when this function raises
    ``OperationalUpdateError``. Deltas only replace complete section metadata,
    keyed items, or source references; nested payload patching is deliberately
    unsupported.
    """

    if not isinstance(update, OperationalUpdate):
        raise OperationalUpdateError("update must be OperationalUpdate")
    if update.mode is UpdateMode.FULL:
        assert update.picture is not None
        return update.picture
    if current is None:
        raise OperationalUpdateError("cannot apply a delta without a materialized base picture")
    if current.picture_revision != update.base_revision:
        raise OperationalUpdateError(
            f"delta base {update.base_revision!r} does not match current revision "
            f"{current.picture_revision!r}"
        )
    if current.schema_version != update.schema_version:
        raise OperationalUpdateError("delta schema version does not match current picture")

    read_dict = current.to_read_model().to_dict()
    read_dict["schema_version"] = update.schema_version
    read_dict["observed_at"] = _timestamp(update.observed_at)

    try:
        for path in update.removed:
            collection, key = _parse_path(path)
            if collection == "sources":
                read_dict["sources"].pop(key, None)
            else:
                read_dict["sections"][collection]["items"].pop(key, None)

        for path, value in update.changed.items():
            collection, key = _parse_path(path)
            if collection == "section_metadata":
                SectionMetadata.from_dict(value)
                read_dict["sections"][key]["metadata"] = dict(value)
            elif collection == "sources":
                source = SourceReference.from_dict(value)
                if source.source_id != key:
                    raise OperationalUpdateError(
                        f"source update path {key!r} does not match value id "
                        f"{source.source_id!r}"
                    )
                read_dict["sources"][key] = dict(value)
            else:
                item = OperationalItem.from_dict(value)
                if item.item_id != key:
                    raise OperationalUpdateError(
                        f"item update path {key!r} does not match value id {item.item_id!r}"
                    )
                read_dict["sections"][collection]["items"][key] = dict(value)

        materialized = OperationalPicture.from_read_model(
            OperationalReadModel.from_dict(read_dict), update.picture_revision
        )
    except OperationalPictureValidationError as exc:
        raise OperationalUpdateError(f"delta produced an invalid operational picture: {exc}") from exc
    if materialized.checksum != update.picture_checksum:
        raise OperationalUpdateError("delta result checksum does not match the advertised picture")
    return materialized


class OperationalContextService:
    """Publishes bounded, revisioned operational pictures from a read provider."""

    def __init__(
        self,
        provider: OperationalReadModelProvider,
        *,
        runtime_id: str | None = None,
        history_limit: int = 32,
    ) -> None:
        if not hasattr(provider, "read_operational_model"):
            raise TypeError("provider must implement read_operational_model()")
        if runtime_id is None:
            runtime_id = uuid.uuid4().hex
        if not isinstance(runtime_id, str) or not _RUNTIME_ID_PATTERN.fullmatch(runtime_id):
            raise ValueError("runtime_id may contain only letters, numbers, '.', '_' and '-'")
        if isinstance(history_limit, bool) or not isinstance(history_limit, int) or history_limit < 2:
            raise ValueError("history_limit must be an integer of at least 2")
        self._provider = provider
        self._runtime_id = runtime_id
        self._history_limit = history_limit
        self._revision_counter = 0
        self._history: OrderedDict[str, OperationalPicture] = OrderedDict()
        self._latest_fingerprint: str | None = None
        self._lock = threading.RLock()

    @property
    def runtime_id(self) -> str:
        return self._runtime_id

    @property
    def current_picture(self) -> OperationalPicture | None:
        with self._lock:
            if not self._history:
                return None
            return next(reversed(self._history.values()))

    @property
    def retained_revisions(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._history)

    def refresh(self) -> OperationalPicture:
        with self._lock:
            read_model = self._provider.read_operational_model()
            if not isinstance(read_model, OperationalReadModel):
                raise OperationalPictureValidationError(
                    "read_operational_model() must return OperationalReadModel"
                )
            fingerprint_payload = read_model.to_dict()
            # The top-level value is the time of this read, not a diffable fact.
            # Boundary timestamps still participate in the fingerprint, so a
            # freshness, provenance, metadata, or item observation change
            # creates a revision. Reusing the complete previous picture keeps
            # revision, observed_at, and checksum immutable as one unit.
            fingerprint_payload.pop("observed_at")
            fingerprint = json.dumps(
                fingerprint_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            if self._history and fingerprint == self._latest_fingerprint:
                return next(reversed(self._history.values()))
            self._revision_counter += 1
            revision = f"{self._runtime_id}:{self._revision_counter}"
            picture = OperationalPicture.from_read_model(read_model, revision)
            self._history[revision] = picture
            self._latest_fingerprint = fingerprint
            while len(self._history) > self._history_limit:
                self._history.popitem(last=False)
            return picture

    def get_operational_update(
        self,
        since_revision: str | None = None,
        *,
        since_checksum: str | None = None,
    ) -> OperationalUpdate:
        """Return a delta when the base is retained, otherwise a recovery full picture."""

        with self._lock:
            target = self.refresh()
            if since_revision is None:
                return self._full_update(target, FullSnapshotReason.INITIAL)
            if not isinstance(since_revision, str) or not since_revision:
                return self._full_update(target, FullSnapshotReason.RUNTIME_MISMATCH)
            base = self._history.get(since_revision)
            if base is None:
                reason = (
                    FullSnapshotReason.BASE_REVISION_UNAVAILABLE
                    if since_revision.startswith(f"{self._runtime_id}:")
                    else FullSnapshotReason.RUNTIME_MISMATCH
                )
                return self._full_update(target, reason)
            if since_checksum is not None and since_checksum != base.checksum:
                return self._full_update(target, FullSnapshotReason.CHECKSUM_MISMATCH)
            if base.schema_version != target.schema_version:
                return self._full_update(target, FullSnapshotReason.SCHEMA_VERSION_MISMATCH)
            changed, removed = _diff_pictures(base, target)
            return OperationalUpdate(
                schema_version=target.schema_version,
                mode=UpdateMode.DELTA,
                base_revision=base.picture_revision,
                picture_revision=target.picture_revision,
                observed_at=target.observed_at,
                picture_checksum=target.checksum,
                changed=changed,
                removed=removed,
                sources=_sources_for_changed_values(target, changed),
            )

    @staticmethod
    def _full_update(
        picture: OperationalPicture, reason: FullSnapshotReason
    ) -> OperationalUpdate:
        return OperationalUpdate(
            schema_version=picture.schema_version,
            mode=UpdateMode.FULL,
            picture_revision=picture.picture_revision,
            observed_at=picture.observed_at,
            picture_checksum=picture.checksum,
            sources=tuple(picture.sources.values()),
            picture=picture,
            reason=reason,
        )
