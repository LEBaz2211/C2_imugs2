from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
import pytest

from c2_imugs2.assistant.config import (
    AssistantConfigurationError,
    AssistantSettings,
    DEFAULT_LM_STUDIO_BASE_URL,
    DEFAULT_LM_STUDIO_MODEL,
)
from c2_imugs2.assistant.models import AssistantStructuredOutput
from c2_imugs2.assistant.orchestrator import (
    AssistantBusyError,
    AssistantInputError,
    AssistantOrchestrator,
)
from c2_imugs2.assistant.prompts import PromptCatalog, PromptConfigurationError
from c2_imugs2.assistant.provider import LangChainOpenAIProvider
from c2_imugs2.operations.service import OperationalContextService, OperationalUpdateError
from c2_imugs2.operations.models import (
    Freshness,
    OperationalItem,
    OperationalPicture,
    OperationalReadModel,
    OperationalSection,
    SectionMetadata,
)


class FakeChatModel:
    def __init__(
        self,
        responses: list[str],
        *,
        structured_error: Exception | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        self.responses = iter(responses)
        self.structured_error = structured_error
        self.usage = usage
        self.invocations: list[list[BaseMessage]] = []
        self.structured_builds = 0

    def with_structured_output(self, *args: Any, **kwargs: Any) -> Any:
        self.structured_builds += 1
        if self.structured_error is not None:
            raise self.structured_error
        return self

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        self.invocations.append(messages)
        if self.usage is not None:
            return AIMessage(content=next(self.responses), usage_metadata=self.usage)
        return AIMessage(content=next(self.responses))


class RevisionContext:
    def __init__(self) -> None:
        self.calls: list[str | None] = []
        self.next_revision = 0

    def get_operational_update(
        self,
        since_revision: str | None = None,
        *,
        since_checksum: str | None = None,
    ) -> int:
        self.calls.append(since_revision)
        self.next_revision += 1
        return self.next_revision


BASE_TIME = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def picture_materializer(
    current: OperationalPicture | None, update: int
) -> OperationalPicture:
    observed_at = BASE_TIME + timedelta(seconds=update)
    return OperationalPicture.from_read_model(
        OperationalReadModel.empty(observed_at),
        picture_revision=f"test-runtime:{update}",
    )


SCENARIO_BINDING = {
    "scenario_id": "scenario-a",
    "version": "v1",
    "map_collection": "scenario_scenario_a_v1",
    "content_hash": "content-a",
    "map_feature_hash": "features-a",
    "activation_id": "activation-a",
    "activation_token": "token-a",
    "status": "ready",
    "ready": True,
}

PARADE_MAP_FEATURE = {
    "feature_id": "parade-area",
    "name": "parade",
    "feature_type": "geofence",
    "origin": "user",
    "geometry_status": "exact",
    "coordinate_count": 5,
    "geometry": {
        "geometry_type": "Polygon",
        "coordinates": [
            [
                [4.3919, 50.8455],
                [4.3931, 50.8452],
                [4.3934, 50.8457],
                [4.3922, 50.8459],
                [4.3919, 50.8455],
            ]
        ],
    },
    "freshness": "fresh",
    "provenance": "active operating map",
    "source_id": "MapDB.active",
}

OPERATOR_OBJECTIVE = {
    "feature_id": "entry-1",
    "name": "Entry 1",
    "feature_type": "objective",
    "geometry": {
        "geometry_type": "Point",
        "coordinates": [4.3932479, 50.8445956],
    },
    "active_map_asset": False,
    "usage": "inline_geometry_only",
    "source_id": "adapter.operator_objectives",
}


def scenario_picture_materializer(
    current: OperationalPicture | None, update: int
) -> OperationalPicture:
    observed_at = BASE_TIME + timedelta(seconds=update)
    empty = OperationalReadModel.empty(observed_at)
    sections = dict(empty.sections)
    sections["scenario"] = OperationalSection(
        metadata=SectionMetadata(observed_at, Freshness.FRESH),
        items={
            "scenario-a@v1": OperationalItem(
                "scenario-a@v1",
                "active_scenario",
                observed_at,
                Freshness.FRESH,
                SCENARIO_BINDING,
            )
        },
    )
    return OperationalPicture.from_read_model(
        OperationalReadModel(
            schema_version=empty.schema_version,
            observed_at=observed_at,
            sections=sections,
            sources=empty.sources,
        ),
        picture_revision=f"scenario-runtime:{update}",
    )


def map_feature_picture_materializer(
    current: OperationalPicture | None, update: int
) -> OperationalPicture:
    observed_at = BASE_TIME + timedelta(seconds=update)
    empty = OperationalReadModel.empty(observed_at)
    sections = dict(empty.sections)
    sections["scenario"] = OperationalSection(
        metadata=SectionMetadata(observed_at, Freshness.FRESH),
        items={
            "scenario-a@v1": OperationalItem(
                "scenario-a@v1",
                "active_scenario",
                observed_at,
                Freshness.FRESH,
                {
                    **SCENARIO_BINDING,
                    "map": "rma",
                    "feature_count": 1,
                    "road_count": 0,
                    "map_features": [PARADE_MAP_FEATURE],
                    "operator_objectives": [OPERATOR_OBJECTIVE],
                    "map_feature_observation": {
                        "freshness": "fresh",
                        "returned_count": 1,
                        "feature_limit": 64,
                        "geometry_coordinate_limit": 128,
                        "truncated": False,
                    },
                    "operator_objective_observation": {
                        "freshness": "fresh",
                        "returned_count": 1,
                        "feature_limit": 64,
                        "truncated": False,
                        "usage": "inline Point mission geometry only",
                    },
                },
            )
        },
    )
    return OperationalPicture.from_read_model(
        OperationalReadModel(
            schema_version=empty.schema_version,
            observed_at=observed_at,
            sections=sections,
            sources=empty.sources,
        ),
        picture_revision=f"scenario-runtime:{update}",
    )


def test_default_settings_target_requested_lm_studio_model_without_a_secret() -> None:
    settings = AssistantSettings()

    assert settings.base_url == DEFAULT_LM_STUDIO_BASE_URL
    assert settings.model == DEFAULT_LM_STUDIO_MODEL
    assert settings.prompt_version == "mission/v1"
    assert settings.reasoning_effort == "xhigh"
    assert settings.enable_thinking is True
    assert settings.preserve_thinking is True
    assert settings.max_output_tokens == 32_768
    assert settings.context_limit == 262_144
    assert "api_key=" not in repr(settings)


def test_reasoning_and_sampling_settings_are_environment_adjustable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("C2_IMUGS2_LLM_REASONING_EFFORT", "medium")
    monkeypatch.setenv("C2_IMUGS2_LLM_ENABLE_THINKING", "false")
    monkeypatch.setenv("C2_IMUGS2_LLM_PRESERVE_THINKING", "false")
    monkeypatch.setenv("C2_IMUGS2_LLM_MAX_OUTPUT_TOKENS", "4096")
    monkeypatch.setenv("C2_IMUGS2_LLM_TEMPERATURE", "0.6")
    monkeypatch.setenv("C2_IMUGS2_LLM_TOP_P", "0.8")
    monkeypatch.setenv("C2_IMUGS2_LLM_TOP_K", "40")
    monkeypatch.setenv("C2_IMUGS2_LLM_MIN_P", "0.1")
    monkeypatch.setenv("C2_IMUGS2_LLM_PRESENCE_PENALTY", "1.5")
    monkeypatch.setenv("C2_IMUGS2_LLM_REPEAT_PENALTY", "1.1")

    settings = AssistantSettings.from_env()

    assert settings.reasoning_effort == "medium"
    assert settings.enable_thinking is False
    assert settings.preserve_thinking is False
    assert settings.max_output_tokens == 4096
    assert settings.temperature == 0.6
    assert settings.top_p == 0.8
    assert settings.top_k == 40
    assert settings.min_p == 0.1
    assert settings.presence_penalty == 1.5
    assert settings.repeat_penalty == 1.1


def test_reasoning_effort_rejects_values_qwen38_does_not_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("C2_IMUGS2_LLM_REASONING_EFFORT", "max")

    with pytest.raises(AssistantConfigurationError, match="low, medium, or xhigh"):
        AssistantSettings.from_env()


def test_provider_reads_key_from_environment_and_disables_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = AssistantSettings()
    monkeypatch.delenv(settings.api_key_env_var, raising=False)

    with pytest.raises(AssistantConfigurationError, match=settings.api_key_env_var):
        LangChainOpenAIProvider(settings, model_factory=lambda **kwargs: object())

    monkeypatch.setenv(settings.api_key_env_var, "test-only-key")
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeChatModel:
        captured.update(kwargs)
        return FakeChatModel(["unused"])

    LangChainOpenAIProvider(settings, model_factory=factory)

    assert set(captured) == {
        "model",
        "base_url",
        "api_key",
        "timeout",
        "max_retries",
        "temperature",
        "top_p",
        "presence_penalty",
        "reasoning_effort",
        "streaming",
        "disable_streaming",
        "extra_body",
    }
    assert captured["base_url"] == DEFAULT_LM_STUDIO_BASE_URL
    assert captured["model"] == DEFAULT_LM_STUDIO_MODEL
    assert captured["api_key"].get_secret_value() == "test-only-key"
    assert captured["max_retries"] == 0
    assert captured["timeout"] == settings.request_timeout_seconds
    assert captured["temperature"] == 1.0
    assert captured["top_p"] == 0.95
    assert captured["presence_penalty"] == 0.0
    assert captured["reasoning_effort"] == "xhigh"
    assert captured["streaming"] is False
    assert captured["disable_streaming"] is True
    assert captured["extra_body"] == {
        "max_tokens": 32_768,
        "top_k": 20,
        "min_p": 0.0,
        # LM Studio's Chat Completions compatibility parameter is named
        # repeat_penalty (Qwen calls the same sampler repetition_penalty).
        "repeat_penalty": 1.0,
        "chat_template_kwargs": {
            "enable_thinking": True,
            "preserve_thinking": True,
            "reasoning_effort": "xhigh",
        },
    }


def test_plain_lm_studio_response_is_parsed_locally_without_a_repair_request() -> None:
    model = FakeChatModel(
        [
            "```json\n"
            '{"answer":"Draft ready","assumptions":[],"warnings":["validate"],'
            '"mission_proposal":{"mission_id":"draft-1"}}\n'
            "```"
        ]
    )
    provider = LangChainOpenAIProvider(AssistantSettings(), model=model)

    result = provider.invoke(
        [HumanMessage(content="draft a mission")],
        response_model=AssistantStructuredOutput,
    )

    assert len(model.invocations) == 1
    assert model.structured_builds == 0
    assert result.text == "Draft ready"
    assert result.structured is not None
    assert result.structured.mission_proposal == {"mission_id": "draft-1"}


def test_invalid_json_gracefully_returns_the_single_raw_generation() -> None:
    model = FakeChatModel(["The planner is waiting for a connected vehicle."])
    provider = LangChainOpenAIProvider(AssistantSettings(), model=model)

    result = provider.invoke(
        [HumanMessage(content="why is it waiting?")],
        response_model=AssistantStructuredOutput,
    )

    assert len(model.invocations) == 1
    assert result.text == "The planner is waiting for a connected vehicle."
    assert result.structured is None


def test_unsupported_native_schema_falls_back_before_the_one_invocation() -> None:
    settings = AssistantSettings(native_structured_output=True)
    model = FakeChatModel(
        ['{"answer":"ok","assumptions":[],"warnings":[],"mission_proposal":null}'],
        structured_error=NotImplementedError("not supported"),
    )
    provider = LangChainOpenAIProvider(settings, model=model)

    result = provider.invoke(
        [HumanMessage(content="status")],
        response_model=AssistantStructuredOutput,
    )

    assert model.structured_builds == 1
    assert len(model.invocations) == 1
    assert result.structured is not None
    assert result.text == "ok"


def test_orchestrator_injects_a_fresh_full_picture_on_every_message() -> None:
    settings = AssistantSettings(max_history_turns=2)
    context = RevisionContext()
    model = FakeChatModel(
        [
            '{"answer":"First","assumptions":[],"warnings":[],"mission_proposal":null}',
            '{"answer":"Second","assumptions":[],"warnings":[],'
            '"mission_proposal":{"mission_id":"draft-2"}}',
        ]
    )
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    first = assistant.chat(conversation_id="conversation-1", user_message="show status")
    second = assistant.chat(conversation_id="conversation-1", user_message="draft it")

    assert len(model.invocations) == 2
    assert context.calls == [None, "test-runtime:1"]
    assert first.picture_revision == "test-runtime:1"
    assert second.picture_revision == "test-runtime:2"
    assert second.mission_proposal == {"mission_id": "draft-2"}

    first_current = model.invocations[0][-1]
    second_current = model.invocations[1][-1]
    assert isinstance(first_current, HumanMessage)
    assert '"picture_revision":"test-runtime:1"' in str(first_current.content)
    assert '"picture_revision":"test-runtime:2"' in str(second_current.content)

    # Previous conversation messages are stored without old operational JSON;
    # only the newly rendered message carries the materialized current picture.
    assert model.invocations[1][1].content == "show status"
    assert "test-runtime:1" not in str(model.invocations[1][1].content)


def test_response_carries_binding_from_the_exact_picture_sent_to_the_model() -> None:
    settings = AssistantSettings()
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"bound"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=scenario_picture_materializer,
    )

    response = assistant.chat(conversation_id="binding", user_message="draft")

    assert response.picture_revision == "scenario-runtime:1"
    assert response.picture_scenario_binding is not None
    assert response.picture_scenario_binding.model_dump() == SCENARIO_BINDING
    serialized_request = "\n".join(
        str(message.content) for message in model.invocations[0]
    )
    assert '"current_environment"' in serialized_request
    assert '"activation_token"' not in serialized_request
    assert '"scenario_id"' not in serialized_request
    assert '"map_collection"' not in serialized_request
    assert '"content_hash"' not in serialized_request
    assert '"map_feature_hash"' not in serialized_request


def test_model_messages_include_exact_active_map_feature_without_internal_binding() -> None:
    settings = AssistantSettings()
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"The parade area is available."}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=map_feature_picture_materializer,
    )

    response = assistant.chat(
        conversation_id="map-feature-projection",
        user_message="Can I cover parade?",
        debug=True,
    )

    assert response.picture_scenario_binding is not None
    assert response.picture_scenario_binding.activation_token == "token-a"
    assert response.debug_trace is not None
    assert response.debug_trace["model_messages"] == [
        {
            "role": {"system": "system", "human": "user"}[message.type],
            "content": message.content,
        }
        for message in model.invocations[0]
    ]
    current_prompt = str(model.invocations[0][-1].content)
    encoded_picture = current_prompt.split("```json\n", 1)[1].split("\n```", 1)[0]
    model_picture = json.loads(encoded_picture)
    projected_feature = model_picture["current_environment"]["map_features"][0]
    assert projected_feature == {
        key: value for key, value in PARADE_MAP_FEATURE.items() if key != "source_id"
    }
    assert model_picture["current_environment"]["operator_objectives"] == [
        {
            key: value
            for key, value in OPERATOR_OBJECTIVE.items()
            if key != "source_id"
        }
    ]
    serialized_picture = json.dumps(model_picture, sort_keys=True)
    for internal_key in (
        "scenario_id",
        "version",
        "map_collection",
        "content_hash",
        "map_feature_hash",
        "activation_id",
        "activation_token",
        "source_id",
    ):
        assert f'"{internal_key}"' not in serialized_picture


def test_debug_messages_match_the_request_and_never_include_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AssistantSettings()
    secret = "sk-lm-test:NeverExposeThis123"
    monkeypatch.setenv(settings.api_key_env_var, secret)
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"safe"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    response = assistant.chat(
        conversation_id="secrets",
        user_message=(
            f"Discuss the scenario. api_key={secret} "
            "Authorization: Bearer another-secret-value"
        ),
        debug=True,
    )

    trace = response.debug_trace
    assert trace is not None
    exact_messages = [
        {
            "role": {"system": "system", "human": "user"}[message.type],
            "content": message.content,
        }
        for message in model.invocations[0]
    ]
    assert trace["model_messages"] == exact_messages
    serialized = json.dumps(
        {"request": exact_messages, "debug": trace},
        sort_keys=True,
    )
    assert secret not in serialized
    assert "another-secret-value" not in serialized
    assert "Authorization" not in serialized
    assert "Discuss the scenario" in str(model.invocations[0][-1].content)


def test_orchestrator_materializes_real_operational_context_deltas() -> None:
    class ChangingReadProvider:
        def __init__(self) -> None:
            self.reads = 0

        def read_operational_model(self) -> OperationalReadModel:
            self.reads += 1
            return OperationalReadModel.empty(BASE_TIME + timedelta(seconds=self.reads))

    settings = AssistantSettings()
    read_provider = ChangingReadProvider()
    context = OperationalContextService(read_provider, runtime_id="assistant-test")
    model = FakeChatModel(['{"answer":"one"}', '{"answer":"two"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
    )

    first = assistant.chat(conversation_id="real-delta", user_message="first")
    second = assistant.chat(conversation_id="real-delta", user_message="second")

    assert first.picture_revision == "assistant-test:1"
    assert second.picture_revision == "assistant-test:2"
    assert '"picture_revision":"assistant-test:2"' in str(
        model.invocations[1][-1].content
    )


def test_invalid_delta_recovers_with_a_full_picture_before_model_invocation() -> None:
    def fail_one_delta(
        current: OperationalPicture | None, update: int
    ) -> OperationalPicture:
        if current is not None and update == 2:
            raise OperationalUpdateError("simulated checksum mismatch")
        return picture_materializer(current, update)

    settings = AssistantSettings()
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"one"}', '{"answer":"recovered"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=fail_one_delta,
    )

    assistant.chat(conversation_id="recovery", user_message="first")
    recovered = assistant.chat(conversation_id="recovery", user_message="second")

    assert context.calls == [None, "test-runtime:1", None]
    assert recovered.picture_revision == "test-runtime:3"
    assert len(model.invocations) == 2


def test_conversation_history_is_bounded_by_complete_turns() -> None:
    settings = AssistantSettings(max_history_turns=1)
    context = RevisionContext()
    model = FakeChatModel(
        [
            '{"answer":"a1"}',
            '{"answer":"a2"}',
            '{"answer":"a3"}',
        ]
    )
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    assistant.chat(conversation_id="bounded", user_message="unique-first")
    assistant.chat(conversation_id="bounded", user_message="unique-second")
    assistant.chat(conversation_id="bounded", user_message="unique-third")

    third_messages = model.invocations[2]
    contents = [str(message.content) for message in third_messages]
    assert len(third_messages) == 4  # system + one prior pair + current message
    assert all("unique-first" not in content for content in contents)
    assert any(content == "unique-second" for content in contents)


def test_conversation_count_is_bounded_and_draft_remains_available_for_follow_up() -> None:
    settings = AssistantSettings(max_history_turns=1, max_conversations=1)
    context = RevisionContext()
    model = FakeChatModel(
        [
            '{"answer":"drafted","mission_proposal":{"mission_id":"draft-1"}}',
            '{"answer":"other"}',
            '{"answer":"new session"}',
        ]
    )
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    assistant.chat(conversation_id="first", user_message="draft")
    assistant.chat(conversation_id="first", user_message="adjust the draft")

    assert '"mission_id":"draft-1"' in str(model.invocations[1][2].content)

    assistant.chat(conversation_id="second", user_message="status")
    assert context.calls == [None, "test-runtime:1", None]


def test_oversized_picture_is_rejected_without_calling_the_model() -> None:
    settings = AssistantSettings(max_operational_picture_chars=10)
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"must not run"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    with pytest.raises(AssistantInputError, match="compact the backend read model"):
        assistant.chat(conversation_id="too-large", user_message="status")

    assert model.invocations == []


def test_concurrent_model_work_is_rejected_instead_of_queued() -> None:
    settings = AssistantSettings()
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"must not run"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    assert assistant._model_lock.acquire(blocking=False)  # noqa: SLF001
    try:
        with pytest.raises(AssistantBusyError, match="current generation"):
            assistant.chat(conversation_id="busy", user_message="status")
    finally:
        assistant._model_lock.release()  # noqa: SLF001

    assert model.invocations == []


def test_overlapping_turn_for_same_conversation_is_rejected_without_waiting() -> None:
    settings = AssistantSettings()
    context = RevisionContext()
    model = FakeChatModel(['{"answer":"must not run"}'])
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )
    session = assistant._sessions.get("same-conversation")  # noqa: SLF001
    assert session.lock.acquire(blocking=False)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            turn = executor.submit(
                assistant.chat,
                conversation_id="same-conversation",
                user_message="overlapping turn",
            )
            with pytest.raises(AssistantBusyError, match="conversation is busy"):
                turn.result(timeout=1)
    finally:
        session.lock.release()

    assert context.calls == []
    assert model.invocations == []


def test_prompt_catalog_rejects_path_traversal_and_missing_fields(tmp_path: Path) -> None:
    catalog = PromptCatalog(tmp_path)
    with pytest.raises(PromptConfigurationError, match="unsafe prompt version"):
        catalog.load("../secret")

    prompt_root = tmp_path / "broken"
    prompt_root.mkdir()
    (prompt_root / "system.txt").write_text("system", encoding="utf-8")
    (prompt_root / "mission_contract.txt").write_text("contract", encoding="utf-8")
    (prompt_root / "structured_output.txt").write_text("structured", encoding="utf-8")
    (prompt_root / "user_message.txt").write_text("{user_message}", encoding="utf-8")

    with pytest.raises(PromptConfigurationError, match="missing required fields"):
        catalog.load("broken")


def test_prompt_catalog_loads_family_manifest_and_ordered_sections(tmp_path: Path) -> None:
    prompt_root = tmp_path / "mission" / "test"
    (prompt_root / "system").mkdir(parents=True)
    (prompt_root / "system" / "first.txt").write_text("first", encoding="utf-8")
    (prompt_root / "system" / "second.txt").write_text("second", encoding="utf-8")
    (prompt_root / "contract.txt").write_text("contract", encoding="utf-8")
    (prompt_root / "example.txt").write_text("example", encoding="utf-8")
    (prompt_root / "output.txt").write_text("output", encoding="utf-8")
    (prompt_root / "user.txt").write_text(
        "{picture_revision} {picture_observed_at} "
        "{operational_picture_json} {user_message}",
        encoding="utf-8",
    )
    (prompt_root / "prompt.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "mission/test",
                "system": ["system/first.txt", "system/second.txt"],
                "mission_contract": "contract.txt",
                "examples": ["example.txt"],
                "user_message": "user.txt",
                "structured_output": "output.txt",
            }
        ),
        encoding="utf-8",
    )

    bundle = PromptCatalog(tmp_path).load("mission/test")

    assert bundle.version == "mission/test"
    assert bundle.system == "first\n\nsecond"
    assert bundle.examples == "example"


def test_prompt_catalog_rejects_manifest_component_traversal(tmp_path: Path) -> None:
    prompt_root = tmp_path / "mission" / "unsafe"
    prompt_root.mkdir(parents=True)
    (prompt_root / "prompt.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "mission/unsafe",
                "system": ["../outside.txt"],
                "mission_contract": "contract.txt",
                "user_message": "user.txt",
                "structured_output": "output.txt",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PromptConfigurationError, match="unsafe prompt manifest"):
        PromptCatalog(tmp_path).load("mission/unsafe")


def test_default_prompt_preserves_identity_and_allows_stale_working_copy_edits() -> None:
    bundle = PromptCatalog().load("mission/v1")
    normalized_system = " ".join(bundle.system.split())

    assert "set `mission_id` to the empty string" in bundle.mission_contract
    assert "preserve the exact non-empty `mission_id`" in bundle.mission_contract
    assert "explicitly Re-initialized" in bundle.mission_contract
    assert "Do not reject the revision solely" in normalized_system


def test_v1_prompt_is_capability_accurate_and_structured() -> None:
    bundle = PromptCatalog().load("mission/v1")

    assert bundle.version == "mission/v1"
    assert "# Objective" in bundle.system
    assert "# Instruction Priority" in bundle.system
    assert "# Capabilities And Boundaries" in bundle.system
    assert "# Uncertainty" in bundle.system
    assert "no direct access to source code" in bundle.system
    assert "backend/" not in bundle.system
    assert "legacy_ros/" not in bundle.system
    assert "set `mission_id` to the empty string" in bundle.mission_contract
    assert "current_environment.operator_objectives" in bundle.system
    assert "never put its `feature_id`" in bundle.mission_contract
    assert "<example>" in bundle.examples


def test_debug_trace_reports_exact_context_usage_from_model_usage() -> None:
    settings = AssistantSettings()
    context = RevisionContext()
    model = FakeChatModel(
        ['{"answer":"done"}'],
        usage={
            "input_tokens": 150_000,
            "output_tokens": 3_000,
            "total_tokens": 153_000,
        },
    )
    assistant = AssistantOrchestrator(
        context=context,
        model=LangChainOpenAIProvider(settings, model=model),
        settings=settings,
        picture_materializer=picture_materializer,
    )

    response = assistant.chat(conversation_id="ctx", user_message="status", debug=True)

    assert response.debug_trace is not None
    usage = response.debug_trace["context_usage"]
    assert usage["prompt_tokens"] == 150_000
    assert usage["completion_tokens"] == 3_000
    assert usage["total_tokens"] == 153_000
    assert usage["context_limit"] == 262_144
    assert usage["context_used_percent"] == 58.36
    assert usage["remaining_tokens"] == 262_144 - 153_000
    final_event = next(
        event
        for event in response.debug_trace["events"]
        if event["type"] == "model_final"
    )
    assert final_event["context_usage"] == usage
    assert response.model_usage == {
        "input_tokens": 150_000,
        "output_tokens": 3_000,
        "total_tokens": 153_000,
    }
