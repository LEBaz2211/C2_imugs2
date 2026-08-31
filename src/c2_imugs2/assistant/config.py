"""Environment-backed assistant configuration.

Secrets are intentionally not fields on :class:`AssistantSettings`.  The API
key is resolved from the named environment variable only when the provider is
constructed, so settings can be logged or returned by diagnostics safely.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal


DEFAULT_LM_STUDIO_BASE_URL = "http://10.67.80.81:8000/v1"
DEFAULT_LM_STUDIO_MODEL = "Inferact/Qwen3.8-Flash-Next-NVFP4"
DEFAULT_CONTEXT_LIMIT = 262_144
DEFAULT_API_KEY_ENV_VAR = "C2_IMUGS2_LLM_API_KEY"


class AssistantConfigurationError(ValueError):
    """Raised before a model request when assistant configuration is invalid."""


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise AssistantConfigurationError(f"{name} must be an integer") from exc
    if value < minimum:
        raise AssistantConfigurationError(f"{name} must be at least {minimum}")
    return value


def _env_float(
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float | None = None,
) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise AssistantConfigurationError(f"{name} must be a number") from exc
    if value < minimum:
        raise AssistantConfigurationError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise AssistantConfigurationError(f"{name} must be at most {maximum}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise AssistantConfigurationError(
        f"{name} must be one of true/false, yes/no, on/off, or 1/0"
    )


@dataclass(frozen=True, slots=True)
class AssistantSettings:
    """Non-secret configuration for one assistant instance."""

    base_url: str = DEFAULT_LM_STUDIO_BASE_URL
    model: str = DEFAULT_LM_STUDIO_MODEL
    api_key_env_var: str = DEFAULT_API_KEY_ENV_VAR
    # Qwen3.8's maximum reasoning mode can consume tens of thousands of
    # completion tokens before it emits the answer.  A small completion cap
    # therefore produces a successful HTTP response with empty message
    # content.  Keep the defaults large enough for xhigh, while retaining an
    # explicit environment override for operators with a smaller context.
    # The vLLM endpoint serves the Flash model with a 32768-token output cap.
    request_timeout_seconds: float = 900.0
    max_output_tokens: int = 32_768
    # Total context window of the served model.  Debug traces compare the
    # server-reported prompt/completion usage against this limit.
    context_limit: int = DEFAULT_CONTEXT_LIMIT
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0
    presence_penalty: float = 0.0
    repeat_penalty: float = 1.0
    reasoning_effort: Literal["low", "medium", "xhigh"] = "xhigh"
    enable_thinking: bool = True
    preserve_thinking: bool = True
    prompt_version: str = "mission/v1"
    max_history_turns: int = 6
    max_conversations: int = 128
    max_user_message_chars: int = 12_000
    max_operational_picture_chars: int = 100_000
    native_structured_output: bool = False
    structured_output_method: Literal["json_schema", "function_calling", "json_mode"] = (
        "json_schema"
    )

    @classmethod
    def from_env(cls) -> "AssistantSettings":
        """Load non-secret settings from ``C2_IMUGS2_LLM_*`` variables."""

        method = os.getenv("C2_IMUGS2_LLM_STRUCTURED_METHOD", "json_schema")
        if method not in {"json_schema", "function_calling", "json_mode"}:
            raise AssistantConfigurationError(
                "C2_IMUGS2_LLM_STRUCTURED_METHOD must be json_schema, "
                "function_calling, or json_mode"
            )

        reasoning_effort = os.getenv(
            "C2_IMUGS2_LLM_REASONING_EFFORT", "xhigh"
        ).strip().lower()
        if reasoning_effort not in {"low", "medium", "xhigh"}:
            raise AssistantConfigurationError(
                "C2_IMUGS2_LLM_REASONING_EFFORT must be low, medium, or xhigh"
            )

        settings = cls(
            base_url=os.getenv("C2_IMUGS2_LLM_BASE_URL", DEFAULT_LM_STUDIO_BASE_URL),
            model=os.getenv("C2_IMUGS2_LLM_MODEL", DEFAULT_LM_STUDIO_MODEL),
            api_key_env_var=os.getenv(
                "C2_IMUGS2_LLM_API_KEY_ENV_VAR", DEFAULT_API_KEY_ENV_VAR
            ),
            request_timeout_seconds=_env_float(
                "C2_IMUGS2_LLM_TIMEOUT_SECONDS", 900.0, minimum=1.0
            ),
            max_output_tokens=_env_int(
                "C2_IMUGS2_LLM_MAX_OUTPUT_TOKENS", 32_768, minimum=1
            ),
            context_limit=_env_int(
                "C2_IMUGS2_LLM_CONTEXT_LIMIT", DEFAULT_CONTEXT_LIMIT, minimum=1
            ),
            temperature=_env_float(
                "C2_IMUGS2_LLM_TEMPERATURE", 1.0, minimum=0.0
            ),
            top_p=_env_float(
                "C2_IMUGS2_LLM_TOP_P", 0.95, minimum=0.0, maximum=1.0
            ),
            top_k=_env_int("C2_IMUGS2_LLM_TOP_K", 20, minimum=1),
            min_p=_env_float(
                "C2_IMUGS2_LLM_MIN_P", 0.0, minimum=0.0, maximum=1.0
            ),
            presence_penalty=_env_float(
                "C2_IMUGS2_LLM_PRESENCE_PENALTY", 0.0, minimum=-2.0
            ),
            repeat_penalty=_env_float(
                "C2_IMUGS2_LLM_REPEAT_PENALTY", 1.0, minimum=0.0
            ),
            reasoning_effort=reasoning_effort,  # type: ignore[arg-type]
            enable_thinking=_env_bool(
                "C2_IMUGS2_LLM_ENABLE_THINKING", True
            ),
            preserve_thinking=_env_bool(
                "C2_IMUGS2_LLM_PRESERVE_THINKING", True
            ),
            prompt_version=os.getenv("C2_IMUGS2_LLM_PROMPT_VERSION", "mission/v1"),
            max_history_turns=_env_int(
                "C2_IMUGS2_LLM_MAX_HISTORY_TURNS", 6, minimum=0
            ),
            max_conversations=_env_int(
                "C2_IMUGS2_LLM_MAX_CONVERSATIONS", 128, minimum=1
            ),
            max_user_message_chars=_env_int(
                "C2_IMUGS2_LLM_MAX_USER_CHARS", 12_000, minimum=1
            ),
            max_operational_picture_chars=_env_int(
                "C2_IMUGS2_LLM_MAX_PICTURE_CHARS", 100_000, minimum=1
            ),
            native_structured_output=_env_bool(
                "C2_IMUGS2_LLM_NATIVE_STRUCTURED_OUTPUT", False
            ),
            structured_output_method=method,  # type: ignore[arg-type]
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.base_url.strip():
            raise AssistantConfigurationError("LLM base_url cannot be empty")
        if not self.model.strip():
            raise AssistantConfigurationError("LLM model cannot be empty")
        if not self.api_key_env_var.strip():
            raise AssistantConfigurationError("LLM API-key environment variable cannot be empty")
        if self.request_timeout_seconds <= 0:
            raise AssistantConfigurationError("LLM request timeout must be positive")
        if self.max_output_tokens <= 0:
            raise AssistantConfigurationError("LLM max output tokens must be positive")
        if self.context_limit <= 0:
            raise AssistantConfigurationError("LLM context limit must be positive")
        if self.temperature < 0:
            raise AssistantConfigurationError("LLM temperature cannot be negative")
        if not 0 <= self.top_p <= 1:
            raise AssistantConfigurationError("LLM top_p must be between 0 and 1")
        if self.top_k < 1:
            raise AssistantConfigurationError("LLM top_k must be positive")
        if not 0 <= self.min_p <= 1:
            raise AssistantConfigurationError("LLM min_p must be between 0 and 1")
        if not -2 <= self.presence_penalty <= 2:
            raise AssistantConfigurationError(
                "LLM presence penalty must be between -2 and 2"
            )
        if self.repeat_penalty < 0:
            raise AssistantConfigurationError("LLM repeat penalty cannot be negative")
        if self.reasoning_effort not in {"low", "medium", "xhigh"}:
            raise AssistantConfigurationError(
                "LLM reasoning effort must be low, medium, or xhigh"
            )
        if self.max_history_turns < 0:
            raise AssistantConfigurationError("assistant history limit cannot be negative")
        if self.max_conversations < 1:
            raise AssistantConfigurationError("assistant conversation limit must be positive")
        if self.max_user_message_chars <= 0:
            raise AssistantConfigurationError("user-message limit must be positive")
        if self.max_operational_picture_chars <= 0:
            raise AssistantConfigurationError("operational-picture limit must be positive")
        if self.structured_output_method not in {
            "json_schema",
            "function_calling",
            "json_mode",
        }:
            raise AssistantConfigurationError("unsupported structured-output method")

    def require_api_key(self) -> str:
        """Resolve the API key from the configured environment variable."""

        value = os.getenv(self.api_key_env_var)
        if value is None or not value.strip():
            raise AssistantConfigurationError(
                f"set {self.api_key_env_var} before starting the LLM assistant"
            )
        return value
