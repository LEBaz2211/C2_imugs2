from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from c2_imugs2.api import create_app
from c2_imugs2.assistant.models import AssistantResponse, AssistantWorldBinding
from c2_imugs2.assistant.orchestrator import AssistantBusyError
from c2_imugs2.infrastructure.legacy.rest import LegacyRestResponse
from c2_imugs2.operations.models import OperationalReadModel
from c2_imugs2.operations.service import OperationalContextService


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_WORLD = {
    "world_id": "assistant-test",
    "world_version": "v1",
    "deployment_id": "deployment-assistant-test",
    "status": "ready",
    "ready": True,
    "agents": [],
    "map_collection": "world_assistant_test_v1",
    "content_hash": "content-test-v1",
    "map_feature_hash": "features-test-v1",
    "launch_id": "launch-1",
    "map_snapshot_token": "token-1",
    "snapshot": {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e",
                "properties": {
                    "feature_id": "dbfd7aea-2f43-4653-b62a-aa0cd8ef9e0e",
                    "feature_type": "geofence",
                },
                "geometry": {"type": "Polygon", "coordinates": []},
            }
        ],
    },
    "live_features": {"type": "FeatureCollection", "features": []},
}
PICTURE_WORLD_BINDING = AssistantWorldBinding.from_mapping(ACTIVE_WORLD)


class FakeRestClient:
    def health(self) -> LegacyRestResponse:
        return LegacyRestResponse(True, 204, "")


class FakeRosbridgeClient:
    url = "ws://fake-rosbridge:9090"

    async def diagnostics(self) -> dict[str, Any]:
        return {"checks": [], "nodes": [], "topics": [], "services": []}


class ReadyWorldManager:
    def __init__(self, **overrides: Any) -> None:
        self.state = {**ACTIVE_WORLD, **overrides}

    def active(self) -> dict[str, Any]:
        return self.validated_active() or {}

    def validated_active(self) -> dict[str, Any]:
        return dict(self.state)

    def require_ready(self, vehicle_ids: list[str] | None = None) -> dict[str, Any]:
        return self.validated_active()


class ChangingOperationalProvider:
    def __init__(self) -> None:
        self.reads = 0

    def read_operational_model(self) -> OperationalReadModel:
        self.reads += 1
        return OperationalReadModel.empty(
            datetime(2026, 8, 22, tzinfo=timezone.utc)
            + timedelta(seconds=self.reads)
        )


class FakeAssistant:
    def __init__(
        self,
        mission_proposal: dict[str, Any],
        picture_world_binding: AssistantWorldBinding | None = PICTURE_WORLD_BINDING,
    ) -> None:
        self.mission_proposal = mission_proposal
        self.picture_world_binding = picture_world_binding
        self.calls: list[tuple[str, str]] = []
        self.debug_calls: list[bool] = []
        self.operational_picture_calls: list[dict[str, Any] | None] = []
        self.operational_picture_preview_calls: list[dict[str, Any] | None] = []
        self.resets: list[str] = []

    def _response(
        self,
        *,
        conversation_id: str,
        debug: bool,
    ) -> AssistantResponse:
        debug_trace = (
            {
                "redacted": True,
                "model_messages": [
                    {"role": "user", "content": "exact model-safe prompt"}
                ],
                "request_options": {
                    "model": "fake",
                    "stream": False,
                    "temperature": 0.0,
                    "max_tokens": 10,
                    "tools": [],
                },
                "events": [{"type": "model_final", "raw_response": "Draft ready"}],
                "tool_calls": [],
            }
            if debug
            else None
        )
        return AssistantResponse(
            conversation_id=conversation_id,
            answer="Draft ready",
            picture_revision="api-test:2",
            picture_observed_at="2026-08-22T00:00:02Z",
            picture_world_binding=self.picture_world_binding,
            prompt_version="v2",
            assumptions=["The active vehicle remains available."],
            warnings=[],
            mission_proposal=self.mission_proposal,
            debug_trace=debug_trace,
        )

    def chat(
        self,
        *,
        conversation_id: str,
        user_message: str,
        debug: bool = False,
        operational_picture_options: dict[str, Any] | None = None,
    ) -> AssistantResponse:
        self.calls.append((conversation_id, user_message))
        self.debug_calls.append(debug)
        self.operational_picture_calls.append(operational_picture_options)
        return self._response(conversation_id=conversation_id, debug=debug)

    def reset_conversation(self, conversation_id: str) -> bool:
        self.resets.append(conversation_id)
        return True

    def preview_operational_picture(
        self, operational_picture_options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.operational_picture_preview_calls.append(operational_picture_options)
        picture = {
            "context_schema": "1.0",
            "picture_revision": "api-test:preview",
            "observed_at": "2026-08-22T00:00:01Z",
            "current_environment": {},
            "missions": {"metadata": {}, "items": []},
        }
        return {
            "operational_picture": picture,
            "available_operational_picture": picture,
        }


class BusyAssistant(FakeAssistant):
    def chat(
        self,
        *,
        conversation_id: str,
        user_message: str,
        debug: bool = False,
    ) -> AssistantResponse:
        raise AssistantBusyError("assistant conversation is busy")


def _client(
    assistant: FakeAssistant,
    context: OperationalContextService,
    *,
    world_manager: ReadyWorldManager | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            ROOT,
            rest_client=FakeRestClient(),
            rosbridge_client=FakeRosbridgeClient(),
            world_manager=world_manager or ReadyWorldManager(),
            assistant=assistant,  # type: ignore[arg-type]
            operational_context=context,
        )
    )


def test_assistant_api_returns_validated_draft_without_initializing_it() -> None:
    proposal = json.loads(
        (ROOT / "fixtures" / "mission_examples" / "simple_navigation_themis.json").read_text(
            encoding="utf-8"
        )
    )
    assistant = FakeAssistant(proposal)
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    status = client.get("/api/assistant/status").json()
    assert status["configured"] is True
    assert status["streaming"] is False
    assert status["reasoning_effort"] == "xhigh"
    assert status["thinking_enabled"] is True
    assert status["preserve_thinking"] is True
    assert status["max_output_tokens"] == 32_768
    response = client.post(
        "/api/assistant/messages",
        json={"conversation_id": "operator-1", "message": "Draft a point mission"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Draft ready"
    assert payload["mission_proposal_validation"] == {
        "valid": True,
        "scope": "schema_semantics_and_current_environment",
        "issues": [],
        "world_binding": {
                "world_id": "assistant-test",
                "world_version": "v1",
                "deployment_id": "deployment-assistant-test",
                "map_collection": "world_assistant_test_v1",
            "content_hash": "content-test-v1",
            "map_feature_hash": "features-test-v1",
                "launch_id": "launch-1",
            "map_snapshot_token": "token-1",
            "status": "ready",
            "ready": True,
        },
        "command_ready": True,
        "command_issues": [],
    }
    assert payload["mission_proposal"]["mission_id"] == proposal["mission_id"]
    assert "debug_trace" not in payload
    assert assistant.calls == [("operator-1", "Draft a point mission")]

    reset = client.delete("/api/assistant/conversations/operator-1")
    assert reset.json() == {"conversation_id": "operator-1", "reset": True}


def test_nonstream_debug_trace_is_opt_in_and_uses_the_existing_envelope() -> None:
    assistant = FakeAssistant({"mission_id": "incomplete"})
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    response = client.post(
        "/api/assistant/messages",
        json={"conversation_id": "debug-sync", "message": "Draft", "debug": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == "debug-sync"
    assert payload["debug_trace"]["redacted"] is True
    assert payload["debug_trace"]["model_messages"] == [
        {"role": "user", "content": "exact model-safe prompt"}
    ]
    assert payload["debug_trace"]["events"][-1] == {
        "type": "proposal_validation",
        "status": "invalid",
        "issue_count": 1,
    }
    assert assistant.debug_calls == [True]


def test_operational_picture_endpoint_returns_full_then_checksum_bound_delta() -> None:
    assistant = FakeAssistant({"not": "used"})
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    full = client.get("/api/assistant/operational-picture").json()
    delta = client.get(
        "/api/assistant/operational-picture",
        params={
            "since_revision": full["picture_revision"],
            "since_checksum": full["picture_checksum"],
        },
    ).json()

    assert full["mode"] == "full"
    assert full["picture"]["picture_revision"] == "api-test:1"
    assert delta["mode"] == "delta"
    assert delta["base_revision"] == "api-test:1"
    assert delta["picture_revision"] == "api-test:2"


def test_assistant_api_forwards_bounded_operational_picture_selection() -> None:
    assistant = FakeAssistant({"not": "used"})
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    response = client.post(
        "/api/assistant/messages",
        json={
            "conversation_id": "operator-context",
            "message": "What is selected?",
            "operational_picture": {
                "sections": ["missions", "plans"],
                "mission_ids": ["mission-a"],
                "operator_missions": [
                    {"mission_id": "mission-a", "name": "Browser draft"}
                ],
                "exclude_paths": ["missions.items[*].data.operator_context"],
            },
        },
    )

    assert response.status_code == 200
    assert assistant.operational_picture_calls == [
        {
            "sections": ["missions", "plans"],
            "mission_ids": ["mission-a"],
            "operator_missions": [
                {"mission_id": "mission-a", "name": "Browser draft"}
            ],
            "item_ids": {},
            "exclude_paths": ["missions.items[*].data.operator_context"],
        }
    ]


def test_assistant_api_rejects_blank_operational_picture_exclude_paths() -> None:
    assistant = FakeAssistant({"not": "used"})
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    response = client.post(
        "/api/assistant/messages",
        json={
            "conversation_id": "bad-context-filter",
            "message": "What is selected?",
            "operational_picture": {"sections": [], "exclude_paths": ["   "]},
        },
    )

    assert response.status_code == 422


def test_assistant_api_previews_exact_model_projection_without_chat() -> None:
    assistant = FakeAssistant({"not": "used"})
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    response = client.post(
        "/api/assistant/operational-picture/preview",
        json={
            "sections": ["missions", "health"],
            "mission_ids": ["mission-a"],
            "item_ids": {
                "missions": ["mission-a"],
                "health": ["backend"],
            },
            "operator_missions": [
                {"mission_id": "mission-a", "name": "Browser draft"}
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["operational_picture"]["picture_revision"] == (
        "api-test:preview"
    )
    assert assistant.calls == []
    assert assistant.operational_picture_preview_calls == [
        {
            "sections": ["missions", "health"],
            "mission_ids": ["mission-a"],
            "operator_missions": [
                {"mission_id": "mission-a", "name": "Browser draft"}
            ],
            "item_ids": {
                "missions": ["mission-a"],
                "health": ["backend"],
            },
            "exclude_paths": [],
        }
    ]


def test_assistant_api_marks_an_invalid_model_draft_unusable() -> None:
    assistant = FakeAssistant({"mission_id": "incomplete"})
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(assistant, context)

    response = client.post(
        "/api/assistant/messages",
        json={"conversation_id": "operator-2", "message": "Draft a mission"},
    )

    assert response.status_code == 200
    validation = response.json()["mission_proposal_validation"]
    assert validation["valid"] is False
    assert "JSON Schema" in validation["issues"][0]["message"]


def test_assistant_api_rejects_absent_binding_but_allows_stale_bound_draft_edit() -> None:
    proposal = json.loads(
        (ROOT / "fixtures" / "mission_examples" / "simple_navigation_themis.json").read_text(
            encoding="utf-8"
        )
    )
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")

    absent = _client(FakeAssistant(proposal, None), context).post(
        "/api/assistant/messages",
        json={"conversation_id": "missing-binding", "message": "Draft a mission"},
    )
    not_ready_binding = AssistantWorldBinding.from_mapping(
        {**ACTIVE_WORLD, "status": "stale", "ready": False}
    )
    not_ready = _client(
        FakeAssistant(proposal, not_ready_binding),
        context,
        world_manager=ReadyWorldManager(
            status="stale",
            ready=False,
            agents=[{"agent_id": proposal["vehicles"][0]}],
        ),
    ).post(
        "/api/assistant/messages",
        json={"conversation_id": "stale-binding", "message": "Change the width"},
    )

    assert absent.status_code == 200
    assert absent.json()["mission_proposal_validation"]["valid"] is False
    assert "binding is absent" in absent.json()["mission_proposal_validation"]["issues"][0]["message"]
    assert not_ready.status_code == 200
    stale_validation = not_ready.json()["mission_proposal_validation"]
    assert stale_validation["valid"] is True
    assert stale_validation["command_ready"] is False
    assert "Init/Re-init remains disabled" in stale_validation["command_issues"][0]["message"]


def test_assistant_api_assigns_new_mission_id_programmatically() -> None:
    proposal = json.loads(
        (ROOT / "fixtures" / "mission_examples" / "simple_navigation_themis.json").read_text(
            encoding="utf-8"
        )
    )
    proposal["mission_id"] = ""
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")

    response = _client(FakeAssistant(proposal), context).post(
        "/api/assistant/messages",
        json={"conversation_id": "new-id", "message": "Draft a new mission"},
    )

    assert response.status_code == 200
    assigned = response.json()["mission_proposal"]["mission_id"]
    assert assigned
    assert assigned != proposal["mission_id"]


def test_assistant_api_rejects_proposal_if_active_world_changed_during_generation() -> None:
    proposal = json.loads(
        (ROOT / "fixtures" / "mission_examples" / "simple_navigation_themis.json").read_text(
            encoding="utf-8"
        )
    )
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(
        FakeAssistant(proposal),
        context,
        world_manager=ReadyWorldManager(launch_id="launch-2"),
    )

    response = client.post(
        "/api/assistant/messages",
        json={"conversation_id": "world-race", "message": "Draft a mission"},
    )

    assert response.status_code == 200
    validation = response.json()["mission_proposal_validation"]
    assert validation["valid"] is False
    assert "current environment changed" in validation["issues"][0]["message"]
    assert "launch_id" in validation["issues"][0]["message"]
    assert validation["world_binding"]["launch_id"] == "launch-2"


def test_assistant_busy_error_is_exposed_as_retryable_http_429() -> None:
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(BusyAssistant({"not": "used"}), context)

    response = client.post(
        "/api/assistant/messages",
        json={"conversation_id": "busy", "message": "status"},
    )

    assert response.status_code == 429
    assert "conversation is busy" in response.json()["detail"]


def test_stream_endpoint_is_not_exposed() -> None:
    context = OperationalContextService(ChangingOperationalProvider(), runtime_id="api-test")
    client = _client(FakeAssistant({"not": "used"}), context)

    response = client.post(
        "/api/assistant/messages/stream",
        json={"conversation_id": "no-stream", "message": "status"},
    )

    assert response.status_code == 404
