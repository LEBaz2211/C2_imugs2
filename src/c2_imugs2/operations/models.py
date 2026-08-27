"""Immutable operational read-model and picture value objects."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


OPERATIONAL_PICTURE_SCHEMA_VERSION = "1.0"
OPERATIONAL_SECTION_NAMES = (
    "scenario",
    "agents",
    "missions",
    "plans",
    "health",
    "warnings",
)

_SCHEMA_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+(?:\.[0-9]+)?$")


class OperationalPictureValidationError(ValueError):
    """Raised when an operational read model is incomplete or inconsistent."""


class Freshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


def _identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationalPictureValidationError(f"{field_name} must be a non-empty string")
    return value


def _schema_version(value: object) -> str:
    version = _identifier(value, "schema_version")
    if not _SCHEMA_VERSION_PATTERN.fullmatch(version):
        raise OperationalPictureValidationError(
            "schema_version must contain two or three numeric components"
        )
    return version


def _utc_datetime(value: object, field_name: str = "observed_at") -> datetime:
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise OperationalPictureValidationError(
                f"{field_name} must be an ISO-8601 timestamp"
            ) from exc
    else:
        raise OperationalPictureValidationError(
            f"{field_name} must be a timezone-aware datetime or ISO-8601 string"
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperationalPictureValidationError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _freshness(value: object) -> Freshness:
    if isinstance(value, Freshness):
        return value
    try:
        return Freshness(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in Freshness)
        raise OperationalPictureValidationError(
            f"freshness must be one of: {allowed}"
        ) from exc


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise OperationalPictureValidationError(f"{field_name} must be a list or tuple")
    normalized = tuple(_identifier(value, field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise OperationalPictureValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _json_value(value: object, path: str) -> Any:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise OperationalPictureValidationError(f"{path} must not contain NaN or infinity")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise OperationalPictureValidationError(f"{path} must use string object keys")
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            normalized[key] = _json_value(value[key], f"{path}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{path}[]") for item in value]
    raise OperationalPictureValidationError(
        f"{path} contains non-JSON value of type {type(value).__name__}"
    )


def _mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OperationalPictureValidationError(f"{field_name} must be an object")
    normalized = _json_value(value, field_name)
    assert isinstance(normalized, dict)
    return normalized


def _check_keys(
    data: Mapping[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    type_name: str,
) -> None:
    if not isinstance(data, Mapping):
        raise OperationalPictureValidationError(f"{type_name} must be an object")
    if any(not isinstance(key, str) for key in data):
        raise OperationalPictureValidationError(f"{type_name} must use string field names")
    unknown = sorted(set(data) - allowed)
    missing = sorted(required - set(data))
    if unknown:
        raise OperationalPictureValidationError(
            f"{type_name} has unknown fields: {', '.join(unknown)}"
        )
    if missing:
        raise OperationalPictureValidationError(
            f"{type_name} is missing fields: {', '.join(missing)}"
        )


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    kind: str
    observed_at: datetime
    freshness: Freshness
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _identifier(self.source_id, "source_id"))
        object.__setattr__(self, "kind", _identifier(self.kind, "source kind"))
        object.__setattr__(self, "observed_at", _utc_datetime(self.observed_at))
        object.__setattr__(self, "freshness", _freshness(self.freshness))
        object.__setattr__(self, "details", _mapping(self.details, "source details"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.source_id,
            "kind": self.kind,
            "observed_at": _timestamp(self.observed_at),
            "freshness": self.freshness.value,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SourceReference":
        _check_keys(
            data,
            allowed={"id", "kind", "observed_at", "freshness", "details"},
            required={"id", "kind", "observed_at", "freshness"},
            type_name="SourceReference",
        )
        return cls(
            source_id=data["id"],
            kind=data["kind"],
            observed_at=data["observed_at"],
            freshness=data["freshness"],
            details=data.get("details", {}),
        )


@dataclass(frozen=True)
class SectionMetadata:
    observed_at: datetime
    freshness: Freshness
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", _utc_datetime(self.observed_at))
        object.__setattr__(self, "freshness", _freshness(self.freshness))
        object.__setattr__(self, "source_ids", _string_tuple(self.source_ids, "source_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_at": _timestamp(self.observed_at),
            "freshness": self.freshness.value,
            "source_ids": list(self.source_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SectionMetadata":
        _check_keys(
            data,
            allowed={"observed_at", "freshness", "source_ids"},
            required={"observed_at", "freshness"},
            type_name="SectionMetadata",
        )
        return cls(
            observed_at=data["observed_at"],
            freshness=data["freshness"],
            source_ids=data.get("source_ids", ()),
        )


@dataclass(frozen=True)
class OperationalItem:
    item_id: str
    kind: str
    observed_at: datetime
    freshness: Freshness
    data: Mapping[str, Any] = field(default_factory=dict)
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _identifier(self.item_id, "item_id"))
        object.__setattr__(self, "kind", _identifier(self.kind, "item kind"))
        object.__setattr__(self, "observed_at", _utc_datetime(self.observed_at))
        object.__setattr__(self, "freshness", _freshness(self.freshness))
        object.__setattr__(self, "data", _mapping(self.data, "item data"))
        object.__setattr__(self, "source_ids", _string_tuple(self.source_ids, "source_ids"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "kind": self.kind,
            "observed_at": _timestamp(self.observed_at),
            "freshness": self.freshness.value,
            "source_ids": list(self.source_ids),
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperationalItem":
        _check_keys(
            data,
            allowed={"id", "kind", "observed_at", "freshness", "source_ids", "data"},
            required={"id", "kind", "observed_at", "freshness"},
            type_name="OperationalItem",
        )
        return cls(
            item_id=data["id"],
            kind=data["kind"],
            observed_at=data["observed_at"],
            freshness=data["freshness"],
            source_ids=data.get("source_ids", ()),
            data=data.get("data", {}),
        )


@dataclass(frozen=True)
class OperationalSection:
    metadata: SectionMetadata
    items: Mapping[str, OperationalItem] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, SectionMetadata):
            raise OperationalPictureValidationError("section metadata must be SectionMetadata")
        if not isinstance(self.items, Mapping):
            raise OperationalPictureValidationError("section items must be an object")
        if any(not isinstance(item_id, str) for item_id in self.items):
            raise OperationalPictureValidationError("section items must use string keys")
        items: dict[str, OperationalItem] = {}
        for item_id in sorted(self.items):
            item = self.items[item_id]
            normalized_id = _identifier(item_id, "section item key")
            if not isinstance(item, OperationalItem):
                raise OperationalPictureValidationError(
                    f"section item {normalized_id!r} must be OperationalItem"
                )
            if item.item_id != normalized_id:
                raise OperationalPictureValidationError(
                    f"section key {normalized_id!r} does not match item id {item.item_id!r}"
                )
            items[normalized_id] = item
        object.__setattr__(self, "items", items)

    @classmethod
    def empty(
        cls,
        observed_at: datetime,
        *,
        freshness: Freshness = Freshness.UNKNOWN,
        source_ids: tuple[str, ...] = (),
    ) -> "OperationalSection":
        return cls(
            metadata=SectionMetadata(
                observed_at=observed_at,
                freshness=freshness,
                source_ids=source_ids,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "items": {item_id: item.to_dict() for item_id, item in self.items.items()},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperationalSection":
        _check_keys(
            data,
            allowed={"metadata", "items"},
            required={"metadata", "items"},
            type_name="OperationalSection",
        )
        raw_items = data["items"]
        if not isinstance(raw_items, Mapping):
            raise OperationalPictureValidationError("OperationalSection.items must be an object")
        return cls(
            metadata=SectionMetadata.from_dict(data["metadata"]),
            items={item_id: OperationalItem.from_dict(item) for item_id, item in raw_items.items()},
        )


def _normalize_sections(value: object) -> dict[str, OperationalSection]:
    if not isinstance(value, Mapping):
        raise OperationalPictureValidationError("sections must be an object")
    if any(not isinstance(name, str) for name in value):
        raise OperationalPictureValidationError("sections must use string keys")
    actual = set(value)
    expected = set(OPERATIONAL_SECTION_NAMES)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown: {', '.join(unknown)}")
        raise OperationalPictureValidationError(
            f"sections must match schema ({'; '.join(details)})"
        )
    sections: dict[str, OperationalSection] = {}
    for name in OPERATIONAL_SECTION_NAMES:
        section = value[name]
        if not isinstance(section, OperationalSection):
            raise OperationalPictureValidationError(f"section {name!r} must be OperationalSection")
        sections[name] = section
    if len(sections["scenario"].items) > 1:
        raise OperationalPictureValidationError("scenario section may contain at most one active scenario")
    return sections


def _normalize_sources(value: object) -> dict[str, SourceReference]:
    if not isinstance(value, Mapping):
        raise OperationalPictureValidationError("sources must be an object")
    if any(not isinstance(source_id, str) for source_id in value):
        raise OperationalPictureValidationError("sources must use string keys")
    sources: dict[str, SourceReference] = {}
    for source_id in sorted(value):
        source = value[source_id]
        normalized_id = _identifier(source_id, "source key")
        if not isinstance(source, SourceReference):
            raise OperationalPictureValidationError(
                f"source {normalized_id!r} must be SourceReference"
            )
        if source.source_id != normalized_id:
            raise OperationalPictureValidationError(
                f"source key {normalized_id!r} does not match source id {source.source_id!r}"
            )
        sources[normalized_id] = source
    return sources


def _validate_source_references(
    sections: Mapping[str, OperationalSection], sources: Mapping[str, SourceReference]
) -> None:
    known = set(sources)
    for section_name, section in sections.items():
        missing = set(section.metadata.source_ids) - known
        if missing:
            raise OperationalPictureValidationError(
                f"section {section_name!r} references unknown sources: {', '.join(sorted(missing))}"
            )
        for item in section.items.values():
            missing = set(item.source_ids) - known
            if missing:
                raise OperationalPictureValidationError(
                    f"item {item.item_id!r} references unknown sources: {', '.join(sorted(missing))}"
                )


@dataclass(frozen=True)
class OperationalReadModel:
    schema_version: str
    observed_at: datetime
    sections: Mapping[str, OperationalSection]
    sources: Mapping[str, SourceReference]

    def __post_init__(self) -> None:
        schema_version = _schema_version(self.schema_version)
        observed_at = _utc_datetime(self.observed_at)
        sections = _normalize_sections(self.sections)
        sources = _normalize_sources(self.sources)
        _validate_source_references(sections, sources)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "sources", sources)

    @classmethod
    def empty(
        cls,
        observed_at: datetime,
        *,
        schema_version: str = OPERATIONAL_PICTURE_SCHEMA_VERSION,
        freshness: Freshness = Freshness.UNKNOWN,
    ) -> "OperationalReadModel":
        return cls(
            schema_version=schema_version,
            observed_at=observed_at,
            sections={
                name: OperationalSection.empty(observed_at, freshness=freshness)
                for name in OPERATIONAL_SECTION_NAMES
            },
            sources={},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observed_at": _timestamp(self.observed_at),
            "sections": {name: section.to_dict() for name, section in self.sections.items()},
            "sources": {source_id: source.to_dict() for source_id, source in self.sources.items()},
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperationalReadModel":
        _check_keys(
            data,
            allowed={"schema_version", "observed_at", "sections", "sources"},
            required={"schema_version", "observed_at", "sections", "sources"},
            type_name="OperationalReadModel",
        )
        raw_sections = data["sections"]
        raw_sources = data["sources"]
        if not isinstance(raw_sections, Mapping) or not isinstance(raw_sources, Mapping):
            raise OperationalPictureValidationError("sections and sources must be objects")
        return cls(
            schema_version=data["schema_version"],
            observed_at=data["observed_at"],
            sections={name: OperationalSection.from_dict(section) for name, section in raw_sections.items()},
            sources={source_id: SourceReference.from_dict(source) for source_id, source in raw_sources.items()},
        )


def _checksum(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class OperationalPicture:
    schema_version: str
    picture_revision: str
    observed_at: datetime
    sections: Mapping[str, OperationalSection]
    sources: Mapping[str, SourceReference]
    checksum: str = ""

    def __post_init__(self) -> None:
        read_model = OperationalReadModel(
            schema_version=self.schema_version,
            observed_at=self.observed_at,
            sections=self.sections,
            sources=self.sources,
        )
        revision = _identifier(self.picture_revision, "picture_revision")
        object.__setattr__(self, "schema_version", read_model.schema_version)
        object.__setattr__(self, "picture_revision", revision)
        object.__setattr__(self, "observed_at", read_model.observed_at)
        object.__setattr__(self, "sections", read_model.sections)
        object.__setattr__(self, "sources", read_model.sources)
        expected_checksum = _checksum(self._unsigned_dict())
        if self.checksum and self.checksum != expected_checksum:
            raise OperationalPictureValidationError("operational picture checksum mismatch")
        object.__setattr__(self, "checksum", expected_checksum)

    @classmethod
    def from_read_model(
        cls, read_model: OperationalReadModel, picture_revision: str
    ) -> "OperationalPicture":
        if not isinstance(read_model, OperationalReadModel):
            raise OperationalPictureValidationError("provider must return OperationalReadModel")
        return cls(
            schema_version=read_model.schema_version,
            picture_revision=picture_revision,
            observed_at=read_model.observed_at,
            sections=read_model.sections,
            sources=read_model.sources,
        )

    def to_read_model(self) -> OperationalReadModel:
        return OperationalReadModel(
            schema_version=self.schema_version,
            observed_at=self.observed_at,
            sections=self.sections,
            sources=self.sources,
        )

    def _unsigned_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "picture_revision": self.picture_revision,
            "observed_at": _timestamp(self.observed_at),
            "sections": {name: section.to_dict() for name, section in self.sections.items()},
            "sources": {source_id: source.to_dict() for source_id, source in self.sources.items()},
        }

    def to_dict(self) -> dict[str, Any]:
        result = self._unsigned_dict()
        result["checksum"] = self.checksum
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperationalPicture":
        _check_keys(
            data,
            allowed={
                "schema_version",
                "picture_revision",
                "observed_at",
                "sections",
                "sources",
                "checksum",
            },
            required={
                "schema_version",
                "picture_revision",
                "observed_at",
                "sections",
                "sources",
                "checksum",
            },
            type_name="OperationalPicture",
        )
        raw_sections = data["sections"]
        raw_sources = data["sources"]
        if not isinstance(raw_sections, Mapping) or not isinstance(raw_sources, Mapping):
            raise OperationalPictureValidationError("sections and sources must be objects")
        return cls(
            schema_version=data["schema_version"],
            picture_revision=data["picture_revision"],
            observed_at=data["observed_at"],
            sections={name: OperationalSection.from_dict(section) for name, section in raw_sections.items()},
            sources={source_id: SourceReference.from_dict(source) for source_id, source in raw_sources.items()},
            checksum=data["checksum"],
        )
