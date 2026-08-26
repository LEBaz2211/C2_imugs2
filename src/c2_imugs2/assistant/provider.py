"""Mockable LangChain model provider for an OpenAI-compatible endpoint."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
import re
from typing import Any, Protocol, runtime_checkable

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, SecretStr

from .config import AssistantSettings
from .models import (
    AssistantStructuredOutput,
    ModelInvocationResult,
)


@runtime_checkable
class ChatModelProvider(Protocol):
    """One-shot model boundary used by :class:`AssistantOrchestrator`."""

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        *,
        response_model: type[AssistantStructuredOutput] | None = None,
    ) -> ModelInvocationResult:
        """Invoke the model exactly once; implementations must not run agent loops."""

def _default_model_factory(**kwargs: Any) -> Any:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**kwargs)


class LangChainOpenAIProvider:
    """LangChain adapter configured for LM Studio's OpenAI-compatible API.

    LangChain retries are disabled.  If native structured output is requested
    but the installed model wrapper cannot construct it, the adapter selects
    the plain chat model *before* invoking it.  It never retries a failed
    structured request as a second generation.
    """

    def __init__(
        self,
        settings: AssistantSettings,
        *,
        model: Any | None = None,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        settings.validate()
        self.settings = settings
        if model is not None:
            self._model = model
            return

        api_key = settings.require_api_key()
        factory = model_factory or _default_model_factory
        self._model = factory(
            model=settings.model,
            base_url=settings.base_url,
            api_key=SecretStr(api_key),
            timeout=settings.request_timeout_seconds,
            max_retries=0,
            temperature=settings.temperature,
            top_p=settings.top_p,
            presence_penalty=settings.presence_penalty,
            reasoning_effort=settings.reasoning_effort,
            streaming=False,
            disable_streaming=True,
            extra_body={
                # ChatOpenAI aliases its ``max_tokens`` constructor argument to
                # ``max_completion_tokens``. LM Studio documents and honors
                # ``max_tokens`` on /v1/chat/completions, so keep the
                # compatibility key in extra_body where the OpenAI client
                # merges it into the top-level JSON request.
                "max_tokens": settings.max_output_tokens,
                "top_k": settings.top_k,
                "min_p": settings.min_p,
                "repeat_penalty": settings.repeat_penalty,
                "chat_template_kwargs": {
                    "enable_thinking": settings.enable_thinking,
                    "preserve_thinking": settings.preserve_thinking,
                    "reasoning_effort": settings.reasoning_effort,
                },
            },
        )

    def invoke(
        self,
        messages: Sequence[BaseMessage],
        *,
        response_model: type[AssistantStructuredOutput] | None = None,
    ) -> ModelInvocationResult:
        runnable = self._model
        native_requested = self.settings.native_structured_output and response_model is not None

        if native_requested:
            runnable = self._structured_runnable_or_plain(response_model)

        raw_result = runnable.invoke(list(messages))
        # Even without native schema support, parse the prompt-requested JSON
        # envelope locally. This is not a model retry or repair request.
        return self._normalize_result(raw_result, response_model)

    def _structured_runnable_or_plain(self, response_model: type[BaseModel]) -> Any:
        builder = getattr(self._model, "with_structured_output", None)
        if not callable(builder):
            return self._model
        try:
            return builder(
                response_model,
                method=self.settings.structured_output_method,
                include_raw=True,
            )
        except TypeError:
            # Older LangChain integrations may not implement ``include_raw``.
            try:
                return builder(response_model, method=self.settings.structured_output_method)
            except (AttributeError, NotImplementedError, TypeError, ValueError):
                return self._model
        except (AttributeError, NotImplementedError, ValueError):
            return self._model

    @classmethod
    def _normalize_result(
        cls,
        result: Any,
        response_model: type[AssistantStructuredOutput] | None,
    ) -> ModelInvocationResult:
        structured: AssistantStructuredOutput | None = None
        raw = result

        if isinstance(result, dict) and (
            "parsed" in result or "raw" in result or "parsing_error" in result
        ):
            raw = result.get("raw")
            parsed = result.get("parsed")
            structured = cls._coerce_structured(parsed, response_model)
        else:
            structured = cls._coerce_structured(result, response_model)

        if structured is None and response_model is not None:
            structured = cls._parse_structured_text(cls._message_text(raw), response_model)

        text = structured.answer if structured is not None else cls._message_text(raw)
        raw_text = cls._message_text(raw)
        usage_source = raw if raw is not None else result
        usage = cls._usage_metadata(usage_source)

        return ModelInvocationResult(
            text=text,
            structured=structured,
            usage_metadata=usage,
            raw_text=raw_text,
            tool_calls=cls._message_tool_calls(raw),
        )

    @staticmethod
    def _usage_metadata(message: Any) -> dict[str, Any] | None:
        usage = getattr(message, "usage_metadata", None)
        if usage is None and hasattr(message, "response_metadata"):
            response_metadata = getattr(message, "response_metadata") or {}
            if isinstance(response_metadata, Mapping):
                usage = response_metadata.get("token_usage")
        return dict(usage) if isinstance(usage, Mapping) else None

    @classmethod
    def _message_tool_calls(cls, message: Any) -> tuple[dict[str, Any], ...]:
        values = getattr(message, "tool_call_chunks", None)
        if not values:
            values = getattr(message, "tool_calls", None)
        if not values:
            additional = getattr(message, "additional_kwargs", None)
            if isinstance(additional, Mapping):
                values = additional.get("tool_calls")
        if not isinstance(values, (list, tuple)):
            return ()

        calls: list[dict[str, Any]] = []
        for value in values:
            raw = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
            if not isinstance(raw, Mapping):
                continue
            function = raw.get("function")
            function = function if isinstance(function, Mapping) else {}
            name = raw.get("name") or function.get("name")
            arguments = raw.get("args")
            if arguments is None:
                arguments = function.get("arguments")
            call = {
                key: cls._json_safe_tool_value(item)
                for key, item in {
                    "id": raw.get("id"),
                    "index": raw.get("index"),
                    "name": name,
                    "arguments": arguments,
                }.items()
                if item is not None
            }
            if call:
                calls.append(call)
        return tuple(calls)

    @classmethod
    def _json_safe_tool_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Mapping):
            return {
                str(key): cls._json_safe_tool_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [cls._json_safe_tool_value(item) for item in value]
        return str(value)

    @staticmethod
    def _coerce_structured(
        value: Any,
        response_model: type[AssistantStructuredOutput] | None,
    ) -> AssistantStructuredOutput | None:
        if response_model is None or value is None:
            return None
        if isinstance(value, response_model):
            return value
        if isinstance(value, dict):
            try:
                return response_model.model_validate(value)
            except ValueError:
                return None
        return None

    @classmethod
    def _parse_structured_text(
        cls,
        text: str,
        response_model: type[AssistantStructuredOutput],
    ) -> AssistantStructuredOutput | None:
        stripped = text.strip()
        if not stripped:
            return None

        candidates = [stripped]
        fenced = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            stripped,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fenced:
            candidates.insert(0, fenced.group(1).strip())

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                return response_model.model_validate(payload)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

        # Some local reasoning models put a short thinking preamble before the
        # requested object. Decode the first valid object without accepting a
        # second model request or trusting trailing prose.
        decoder = json.JSONDecoder()
        for index, character in enumerate(stripped):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(stripped[index:])
                return response_model.model_validate(payload)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        return None

    @staticmethod
    def _message_text(message: Any) -> str:
        content = getattr(message, "content", message)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            return "\n".join(parts)
        if content is None:
            return ""
        return str(content)
