"""Assistant-facing data models independent of HTTP and model providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from pydantic import BaseModel, ConfigDict, Field


class AssistantStructuredOutput(BaseModel):
    """Optional native structured result requested from capable model servers."""

    model_config = ConfigDict(extra="ignore")

    answer: str = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    mission_proposal: dict[str, Any] | None = None


class AssistantWorldBinding(BaseModel):
    """Internal runtime identity captured alongside the model-safe picture.

    These fields support exact post-generation validation but are deliberately
    excluded from the serialized messages sent to the model.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    IDENTITY_FIELDS: ClassVar[tuple[str, ...]] = (
        "world_id",
        "world_version",
        "deployment_id",
        "map_collection",
        "content_hash",
        "map_feature_hash",
        "launch_id",
        "map_snapshot_token",
    )

    world_id: str | None = None
    world_version: str | None = None
    deployment_id: str | None = None
    map_collection: str | None = None
    content_hash: str | None = None
    map_feature_hash: str | None = None
    launch_id: str | None = None
    map_snapshot_token: str | None = None
    status: str | None = None
    ready: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AssistantWorldBinding":
        def optional_text(field: str) -> str | None:
            raw = value.get(field)
            if raw is None:
                return None
            normalized = str(raw).strip()
            return normalized or None

        return cls(
            **{field: optional_text(field) for field in cls.IDENTITY_FIELDS},
            status=optional_text("status"),
            # Do not coerce strings such as "false" into a ready state.
            ready=value.get("ready") is True,
        )

    def missing_identity_fields(self) -> tuple[str, ...]:
        return tuple(field for field in self.IDENTITY_FIELDS if not getattr(self, field))

    def identity_differences(
        self, other: "AssistantWorldBinding"
    ) -> tuple[str, ...]:
        return tuple(
            field
            for field in self.IDENTITY_FIELDS
            if getattr(self, field) != getattr(other, field)
        )


class AssistantResponse(BaseModel):
    """Deterministic envelope returned to the API/UI integration layer."""

    conversation_id: str
    answer: str
    picture_revision: str
    picture_observed_at: str
    picture_world_binding: AssistantWorldBinding | None = None
    prompt_version: str
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    mission_proposal: dict[str, Any] | None = None
    model_usage: dict[str, Any] | None = None
    debug_trace: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ModelInvocationResult:
    """Normalized result of exactly one provider invocation."""

    text: str
    structured: AssistantStructuredOutput | None = None
    usage_metadata: dict[str, Any] | None = None
    raw_text: str = ""
    tool_calls: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    user: str
    assistant: str
