"""One-request assistant orchestration with revisioned operational context."""

from __future__ import annotations

from collections import OrderedDict, deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import json
import os
import re
from threading import Lock
from typing import Any, Protocol, TYPE_CHECKING

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from c2_imugs2.operational_picture import OperationalPicture

from .config import AssistantSettings
from .models import (
    AssistantResponse,
    AssistantScenarioBinding,
    AssistantStructuredOutput,
    ConversationTurn,
    ModelInvocationResult,
)
from .prompts import PromptCatalog
from .provider import ChatModelProvider

if TYPE_CHECKING:
    from c2_imugs2.operational_context import OperationalUpdate


class AssistantInputError(ValueError):
    """Raised before model invocation for invalid or unbounded input."""


class AssistantModelResponseError(RuntimeError):
    """Raised when the one allowed model generation has no usable answer."""


class AssistantBusyError(RuntimeError):
    """Raised instead of queueing another expensive local-model generation."""


class OperationalContextSource(Protocol):
    def get_operational_update(
        self,
        since_revision: str | None = None,
        *,
        since_checksum: str | None = None,
    ) -> "OperationalUpdate": ...


PictureMaterializer = Callable[[OperationalPicture | None, Any], OperationalPicture]


def _default_materializer(
    current: OperationalPicture | None, update: Any
) -> OperationalPicture:
    from c2_imugs2.operational_context import materialize_operational_update

    return materialize_operational_update(current, update)


@dataclass(slots=True)
class _ConversationSession:
    turns: deque[ConversationTurn]
    picture: OperationalPicture | None = None
    lock: Lock = field(default_factory=Lock)


class _ConversationStore:
    def __init__(self, max_history_turns: int, max_conversations: int) -> None:
        self._max_history_turns = max_history_turns
        self._max_conversations = max_conversations
        self._sessions: OrderedDict[str, _ConversationSession] = OrderedDict()
        self._lock = Lock()

    def get(self, conversation_id: str) -> _ConversationSession:
        with self._lock:
            session = self._sessions.get(conversation_id)
            if session is None:
                session = _ConversationSession(
                    turns=deque(maxlen=self._max_history_turns)
                )
                self._sessions[conversation_id] = session
                while len(self._sessions) > self._max_conversations:
                    self._sessions.popitem(last=False)
            else:
                self._sessions.move_to_end(conversation_id)
            return session

    def reset(self, conversation_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(conversation_id, None) is not None


@dataclass(slots=True)
class _PreparedTurn:
    conversation_id: str
    user_message: str
    session: _ConversationSession
    picture: OperationalPicture
    picture_dict: dict[str, Any]
    prompt_messages: list[BaseMessage]
    debug_trace: dict[str, Any] | None


_INTERNAL_ENVIRONMENT_KEY = re.compile(
    r"(?:scenario|activation|collection|(?:^|_)version$|(?:^|_)hash$|"
    r"(?:^|_)source(?:_ids?)?$|^sources?$)",
    re.IGNORECASE,
)
_INTERNAL_ENVIRONMENT_TOKEN = re.compile(
    r"\b(?:MapDB\.)?scenario(?:s)?(?:[._:/-][A-Za-z0-9_.:/-]+)?\b",
    re.IGNORECASE,
)
_SENSITIVE_DEBUG_KEY = re.compile(
    r"(?:authorization|api[-_]?key|token|secret|password|cookie)",
    re.IGNORECASE,
)
_BEARER_SECRET = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_LABELLED_SECRET = re.compile(
    r"(?i)\b(?:authorization|api[-_ ]?key|token|secret|password)\s*[:=]\s*\S+"
)
_OPENAI_STYLE_SECRET = re.compile(r"\bsk-[A-Za-z0-9_:+./=-]{8,}\b")
_MAX_DEBUG_EVENTS = 512
_MAX_DEBUG_TOOL_CALLS = 128


class AssistantOrchestrator:
    """Materialize current context, render a prompt, and generate once.

    A conversation stores only a bounded number of dialogue turns and the last
    validated operational picture. On every message it requests an update,
    materializes a full current picture, and embeds a model-safe projection in
    the new human prompt. Delta recovery may make a second context-service
    read, but this class contains exactly one model-provider request.
    """

    def __init__(
        self,
        *,
        context: OperationalContextSource,
        model: ChatModelProvider,
        settings: AssistantSettings | None = None,
        prompt_catalog: PromptCatalog | None = None,
        picture_materializer: PictureMaterializer | None = None,
    ) -> None:
        self.settings = settings or AssistantSettings.from_env()
        self.settings.validate()
        self._context = context
        self._model = model
        self._model_lock = Lock()
        self._materialize = picture_materializer or _default_materializer
        self._sessions = _ConversationStore(
            self.settings.max_history_turns,
            self.settings.max_conversations,
        )
        self._prompt_bundle = (prompt_catalog or PromptCatalog()).load(
            self.settings.prompt_version
        )
        self._prompt = self._prompt_bundle.chat_prompt(structured_output=True)

    def chat(
        self,
        *,
        conversation_id: str,
        user_message: str,
        debug: bool = False,
    ) -> AssistantResponse:
        """Answer one user message using one and only one LLM request."""

        turn = self._prepare_turn(
            conversation_id=conversation_id,
            user_message=user_message,
            debug=debug,
        )
        try:
            result = self._model.invoke(
                turn.prompt_messages,
                response_model=AssistantStructuredOutput,
            )
            self._record_model_final(turn.debug_trace, result)
            return self._finalize_turn(turn, result)
        finally:
            self._release_turn(turn)

    def _prepare_turn(
        self,
        *,
        conversation_id: str,
        user_message: str,
        debug: bool,
    ) -> _PreparedTurn:
        conversation_id = self._validate_conversation_id(conversation_id)
        # Preserve operator wording; only credentials are removed. Runtime
        # identity abstraction applies to backend-provided context, not to an
        # operator who explicitly asks about an older term.
        user_message = self._redact_sensitive_text(
            self._validate_user_message(user_message)
        )
        session = self._sessions.get(conversation_id)
        if not session.lock.acquire(blocking=False):
            raise AssistantBusyError(
                "assistant conversation is busy; retry after its current message finishes"
            )

        model_lock_acquired = False
        try:
            picture = self._next_picture(session.picture)
            picture_dict = picture.to_dict()
            model_picture = self._model_operational_picture(picture)
            picture_json = json.dumps(
                model_picture,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            if len(picture_json) > self.settings.max_operational_picture_chars:
                raise AssistantInputError(
                    "operational picture exceeds the configured prompt limit; "
                    "compact the backend read model before invoking the LLM"
                )

            prompt_messages = self._prompt.format_messages(
                history=self._history_messages(session.turns),
                picture_revision=model_picture["picture_revision"],
                picture_observed_at=model_picture["observed_at"],
                operational_picture_json=picture_json,
                user_message=user_message,
            )
            # Apply the same final secret filter to the actual messages sent
            # and the debug copy. This makes debug.model_messages exact while
            # retaining the invariant that debug can never expose a credential.
            prompt_messages = [
                message.model_copy(
                    update={
                        "content": self._redact_sensitive_value(message.content)
                    }
                )
                for message in prompt_messages
            ]
            if not self._model_lock.acquire(blocking=False):
                raise AssistantBusyError(
                    "assistant model is busy; retry after the current generation finishes"
                )
            model_lock_acquired = True
            debug_trace = (
                self._build_debug_trace(prompt_messages)
                if debug
                else None
            )
            return _PreparedTurn(
                conversation_id=conversation_id,
                user_message=user_message,
                session=session,
                picture=picture,
                picture_dict=picture_dict,
                prompt_messages=prompt_messages,
                debug_trace=debug_trace,
            )
        except Exception:
            if model_lock_acquired:
                self._model_lock.release()
            session.lock.release()
            raise

    def _finalize_turn(
        self,
        turn: _PreparedTurn,
        result: ModelInvocationResult,
    ) -> AssistantResponse:
        answer = result.text.strip()
        if not answer:
            raise AssistantModelResponseError("LLM returned an empty answer")
        structured = result.structured
        response = AssistantResponse(
            conversation_id=turn.conversation_id,
            answer=answer,
            picture_revision=turn.picture.picture_revision,
            picture_observed_at=turn.picture_dict["observed_at"],
            picture_scenario_binding=self._picture_scenario_binding(turn.picture),
            prompt_version=self._prompt_bundle.version,
            assumptions=list(structured.assumptions) if structured else [],
            warnings=list(structured.warnings) if structured else [],
            mission_proposal=structured.mission_proposal if structured else None,
            model_usage=result.usage_metadata,
            debug_trace=turn.debug_trace,
        )
        turn.session.picture = turn.picture
        turn.session.turns.append(
            ConversationTurn(
                user=turn.user_message,
                assistant=self._model_safe_text(self._history_answer(response)),
            )
        )
        return response

    def _release_turn(self, turn: _PreparedTurn) -> None:
        self._model_lock.release()
        turn.session.lock.release()

    def reset_conversation(self, conversation_id: str) -> bool:
        """Forget in-memory dialogue and picture state for one conversation."""

        return self._sessions.reset(self._validate_conversation_id(conversation_id))

    def _next_picture(self, current: OperationalPicture | None) -> OperationalPicture:
        since_revision = current.picture_revision if current is not None else None
        update = self._context.get_operational_update(
            since_revision,
            since_checksum=current.checksum if current is not None else None,
        )
        try:
            return self._materialize(current, update)
        except Exception as exc:
            from c2_imugs2.operational_context import OperationalUpdateError

            if not isinstance(exc, OperationalUpdateError):
                raise
            full_update = self._context.get_operational_update(None)
            return self._materialize(None, full_update)

    def _model_operational_picture(
        self, picture: OperationalPicture
    ) -> dict[str, Any]:
        """Project internal runtime state into the model-facing environment view."""

        environment_section = picture.sections["scenario"]
        environment_item = (
            next(iter(environment_section.items.values()))
            if environment_section.items
            else None
        )
        environment_data = dict(environment_item.data) if environment_item else {}
        map_facts = self._environment_safe_value(
            {
                "name": environment_data.get("map"),
                "feature_count": environment_data.get("feature_count"),
                "road_count": environment_data.get("road_count"),
            }
        )
        assert isinstance(map_facts, dict)
        map_facts = {key: value for key, value in map_facts.items() if value is not None}
        map_features = self._environment_safe_value(
            environment_data.get("map_features", [])
        )
        if not isinstance(map_features, list):
            map_features = []
        observation = self._environment_safe_value(
            environment_data.get("map_feature_observation", {})
        )
        readiness = self._environment_safe_value(
            {
                "status": environment_data.get("status") or "inactive",
                "ready": environment_data.get("ready") is True,
                "freshness": environment_item.freshness.value
                if environment_item is not None
                else environment_section.metadata.freshness.value,
                "message": environment_data.get("message"),
                "error": environment_data.get("error"),
            }
        )
        assert isinstance(readiness, dict)
        readiness = {key: value for key, value in readiness.items() if value is not None}

        current_environment: dict[str, Any] = {
            "readiness": readiness,
            "map": map_facts,
            "map_features": map_features,
        }
        if isinstance(observation, dict) and observation:
            current_environment["map_feature_observation"] = observation

        picture_dict = picture.to_dict()
        return {
            "context_schema": "1.0",
            # This opaque revision is required for per-message grounding and
            # does not disclose the separately held environment binding.
            "picture_revision": picture.picture_revision,
            "observed_at": picture_dict["observed_at"],
            "current_environment": current_environment,
            "agents": self._project_model_section(picture.sections["agents"]),
            "missions": self._project_model_section(picture.sections["missions"]),
            "plans": self._project_model_section(picture.sections["plans"]),
            "health": self._project_model_section(
                picture.sections["health"], excluded_item_ids={"storage-indexes"}
            ),
            "warnings": self._project_model_section(picture.sections["warnings"]),
        }

    def _project_model_section(
        self,
        section: Any,
        *,
        excluded_item_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        excluded_item_ids = excluded_item_ids or set()
        return {
            "metadata": {
                "observed_at": section.metadata.to_dict()["observed_at"],
                "freshness": section.metadata.freshness.value,
            },
            "items": [
                {
                    "id": self._model_safe_text(item.item_id),
                    "kind": self._model_safe_text(item.kind),
                    "observed_at": item.to_dict()["observed_at"],
                    "freshness": item.freshness.value,
                    "data": self._environment_safe_value(item.data),
                }
                for item in section.items.values()
                if item.item_id not in excluded_item_ids
            ],
        }

    def _build_debug_trace(
        self,
        messages: list[BaseMessage],
    ) -> dict[str, Any]:
        model_messages = [
            {
                "role": self._message_role(message),
                "content": message.content,
            }
            for message in messages
        ]
        trace: dict[str, Any] = {
            "redacted": True,
            "model_messages": model_messages,
            "request_options": {
                "model": self.settings.model,
                "stream": False,
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_output_tokens,
                "top_p": self.settings.top_p,
                "top_k": self.settings.top_k,
                "min_p": self.settings.min_p,
                "presence_penalty": self.settings.presence_penalty,
                "repeat_penalty": self.settings.repeat_penalty,
                "reasoning_effort": self.settings.reasoning_effort,
                "enable_thinking": self.settings.enable_thinking,
                "preserve_thinking": self.settings.preserve_thinking,
                "tools": [],
            },
            "events": [],
            "tool_calls": [],
        }
        self._append_debug_event(
            trace,
            {
                "type": "context_read",
                "view": "current_environment",
            },
        )
        self._append_debug_event(
            trace,
            {
                "type": "model_request_start",
                "stream": False,
                "message_count": len(model_messages),
            },
        )
        return trace

    @staticmethod
    def _message_role(message: BaseMessage) -> str:
        role = getattr(message, "type", "")
        return {
            "human": "user",
            "ai": "assistant",
            "system": "system",
            "tool": "tool",
        }.get(str(role), str(role) or "unknown")

    def _record_model_final(
        self,
        trace: dict[str, Any] | None,
        result: ModelInvocationResult,
    ) -> None:
        if trace is None:
            return
        safe_calls = [self._redact_sensitive_value(call) for call in result.tool_calls]
        for call in safe_calls:
            if call not in trace["tool_calls"]:
                self._append_debug_tool_call(trace, call)
        self._append_debug_event(
            trace,
            {
                "type": "model_final",
                "raw_response": result.raw_text,
                "parsed_answer": result.text,
                "usage": result.usage_metadata,
                "tool_calls": safe_calls,
            },
        )

    def _append_debug_event(
        self, trace: dict[str, Any], event: Mapping[str, Any]
    ) -> None:
        safe_event = self._redact_sensitive_value(event)
        events = trace["events"]
        if len(events) < _MAX_DEBUG_EVENTS:
            events.append(safe_event)
            return
        trace["events_truncated"] = int(trace.get("events_truncated", 0)) + 1
        if event.get("type") in {"model_final", "proposal_validation"}:
            # Keep terminal evidence visible by replacing the final retained
            # non-terminal event once the bounded trace is full.
            events[-1] = safe_event

    @staticmethod
    def _append_debug_tool_call(trace: dict[str, Any], tool_call: Any) -> None:
        calls = trace["tool_calls"]
        if len(calls) < _MAX_DEBUG_TOOL_CALLS:
            calls.append(tool_call)
        else:
            trace["tool_calls_truncated"] = int(
                trace.get("tool_calls_truncated", 0)
            ) + 1

    def _environment_safe_value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                self._model_safe_text(str(key)): self._environment_safe_value(item)
                for key, item in value.items()
                if not _INTERNAL_ENVIRONMENT_KEY.search(str(key))
                and not _SENSITIVE_DEBUG_KEY.search(str(key))
            }
        if isinstance(value, (list, tuple)):
            return [self._environment_safe_value(item) for item in value]
        if isinstance(value, str):
            return self._model_safe_text(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self._model_safe_text(str(value))

    def _redact_sensitive_value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): (
                    "[REDACTED]"
                    if _SENSITIVE_DEBUG_KEY.search(str(key))
                    else self._redact_sensitive_value(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self._redact_sensitive_value(item) for item in value]
        if isinstance(value, str):
            return self._redact_sensitive_text(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self._redact_sensitive_text(str(value))

    def _model_safe_text(self, value: str) -> str:
        text = self._redact_sensitive_text(value)
        text = _INTERNAL_ENVIRONMENT_TOKEN.sub("current environment", text)
        # Backend labels may use underscored or compound forms, so word-boundary
        # replacement alone is not sufficient to keep that identity vocabulary
        # out of the serialized model context.
        text = re.sub("scenario", "environment", text, flags=re.IGNORECASE)
        text = re.sub(
            r"(?i)\bactivation(?:[_ -]?(?:id|token|phase))?\b(?:\s*[:=]\s*\S+)?",
            "environment readiness",
            text,
        )
        return text

    def _redact_sensitive_text(self, value: str) -> str:
        text = value
        secret = os.getenv(self.settings.api_key_env_var)
        if secret and secret.strip():
            text = text.replace(secret, "[REDACTED]")
        text = _BEARER_SECRET.sub("Bearer [REDACTED]", text)
        text = _LABELLED_SECRET.sub("[REDACTED]", text)
        text = _OPENAI_STYLE_SECRET.sub("[REDACTED]", text)
        return text

    @staticmethod
    def _history_messages(turns: deque[ConversationTurn]) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for turn in turns:
            messages.append(HumanMessage(content=turn.user))
            messages.append(AIMessage(content=turn.assistant))
        return messages

    @staticmethod
    def _picture_scenario_binding(
        picture: OperationalPicture,
    ) -> AssistantScenarioBinding | None:
        items = picture.sections["scenario"].items
        if not items:
            return None
        item = next(iter(items.values()))
        return AssistantScenarioBinding.from_mapping(item.data)

    @staticmethod
    def _history_answer(response: AssistantResponse) -> str:
        details: list[str] = [response.answer]
        if response.assumptions:
            details.append("Assumptions: " + "; ".join(response.assumptions))
        if response.warnings:
            details.append("Warnings: " + "; ".join(response.warnings))
        if response.mission_proposal is not None:
            details.append(
                "Mission working-copy proposal; runtime commands and status are "
                "reported separately by the current environment: "
                + json.dumps(
                    response.mission_proposal,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            )
        return "\n".join(details)

    @staticmethod
    def _validate_conversation_id(conversation_id: str) -> str:
        if not isinstance(conversation_id, str) or not conversation_id.strip():
            raise AssistantInputError("conversation_id must be a non-empty string")
        value = conversation_id.strip()
        if len(value) > 256:
            raise AssistantInputError("conversation_id exceeds 256 characters")
        return value

    def _validate_user_message(self, user_message: str) -> str:
        if not isinstance(user_message, str) or not user_message.strip():
            raise AssistantInputError("user_message must be a non-empty string")
        value = user_message.strip()
        if len(value) > self.settings.max_user_message_chars:
            raise AssistantInputError("user_message exceeds the configured character limit")
        return value
