from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .services import (
    ApplicationServiceError,
    BackendMissionApplicationService,
    ScenarioApplicationService,
)
from ..assistant.config import AssistantConfigurationError
from ..assistant.models import AssistantResponse, AssistantScenarioBinding
from ..assistant.orchestrator import (
    AssistantBusyError,
    AssistantInputError,
    AssistantModelResponseError,
    AssistantOrchestrator,
)
from ..core.mission_config import MissionValidationError
from ..core.models import MissionRequest
from ..operations.service import OperationalContextService


class AssistantMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(min_length=1, max_length=256)
    message: str = Field(min_length=1)
    debug: bool = False


def _http_error(exc: ApplicationServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _require_complete_scenario_binding(
    binding: AssistantScenarioBinding | None,
    *,
    source: str,
) -> AssistantScenarioBinding:
    if binding is None:
        raise ValueError(f"{source} environment binding is absent")
    missing = binding.missing_identity_fields()
    if missing:
        raise ValueError(
            f"{source} environment binding is incomplete: {', '.join(missing)}"
        )
    return binding


def _binding_is_ready(binding: AssistantScenarioBinding) -> bool:
    return binding.ready and (binding.status or "").lower() == "ready"


def _require_same_scenario_binding(
    picture_binding: AssistantScenarioBinding,
    active_binding: AssistantScenarioBinding,
) -> None:
    differences = picture_binding.identity_differences(active_binding)
    if differences:
        raise ValueError(
            "current environment changed while the assistant response was being generated; "
            f"differing binding fields: {', '.join(differences)}"
        )


def _append_api_debug_event(
    result: dict[str, Any], event: Mapping[str, Any]
) -> None:
    trace = result.get("debug_trace")
    if not isinstance(trace, dict):
        return
    events = trace.get("events")
    if not isinstance(events, list):
        return
    safe_event = dict(event)
    if len(events) < 512:
        events.append(safe_event)
    else:
        trace["events_truncated"] = int(trace.get("events_truncated", 0)) + 1
        events[-1] = safe_event


def _assistant_response_payload(
    response: AssistantResponse,
    *,
    validate_proposal: Callable[
        [dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]
    ]
    | None,
) -> dict[str, Any]:
    """Apply the deterministic proposal gate to a completed assistant reply."""

    result = response.model_dump(mode="json")
    if result.get("debug_trace") is None:
        # Preserve the original non-debug response contract rather than adding
        # a new null-valued field to every existing client response.
        result.pop("debug_trace", None)

    proposal = response.mission_proposal
    if proposal is None:
        _append_api_debug_event(
            result,
            {"type": "proposal_validation", "status": "not_present"},
        )
        return result

    active_binding: AssistantScenarioBinding | None = None
    try:
        picture_binding = _require_complete_scenario_binding(
            response.picture_scenario_binding,
            source="operational picture",
        )
        if validate_proposal is None:
            raise ValueError(
                "post-generation current environment validation is unavailable"
            )
        validated, active_scenario = validate_proposal(proposal)
        active_binding = _require_complete_scenario_binding(
            AssistantScenarioBinding.from_mapping(active_scenario),
            source="post-generation current environment",
        )
        _require_same_scenario_binding(picture_binding, active_binding)
    except (ApplicationServiceError, MissionValidationError, TypeError, ValueError) as exc:
        result["mission_proposal_validation"] = {
            "valid": False,
            "scope": "schema_semantics_and_current_environment",
            "issues": [{"message": str(exc)}],
        }
        if active_binding is not None:
            result["mission_proposal_validation"]["scenario_binding"] = (
                active_binding.model_dump(mode="json")
            )
        _append_api_debug_event(
            result,
            {"type": "proposal_validation", "status": "invalid", "issue_count": 1},
        )
    else:
        command_ready = _binding_is_ready(active_binding)
        result["mission_proposal"] = validated
        result["mission_proposal_validation"] = {
            "valid": True,
            "scope": "schema_semantics_and_current_environment",
            "issues": [],
            "scenario_binding": active_binding.model_dump(mode="json"),
            "command_ready": command_ready,
            "command_issues": (
                []
                if command_ready
                else [
                    {
                        "message": (
                            "The proposal is editable and valid, but Init/Re-init remains disabled "
                            "until the current environment is ready "
                            f"(status={active_binding.status!r}, ready={active_binding.ready})."
                        )
                    }
                ]
            ),
        }
        _append_api_debug_event(
            result,
            {"type": "proposal_validation", "status": "valid", "issue_count": 0},
        )
    return result


def mission_router(
    service: BackendMissionApplicationService,
    refresh_mission: Callable[[str], None],
) -> APIRouter:
    router = APIRouter(prefix="/api/missions", tags=["missions"])

    @router.post("/init")
    async def init_mission(mission_config: dict[str, Any]) -> dict[str, Any]:
        try:
            return service.initialize(mission_config)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.get("/{mission_id}")
    async def get_mission(mission_id: str) -> dict[str, Any]:
        refresh_mission(mission_id)
        try:
            return service.get(mission_id)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.post("/{mission_id}/approve")
    async def approve(mission_id: str) -> dict[str, Any]:
        try:
            return service.change_status(mission_id, MissionRequest.APPROVE, 4)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.post("/{mission_id}/start")
    async def start(mission_id: str) -> dict[str, Any]:
        try:
            return service.change_status(mission_id, MissionRequest.START, 5)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.delete("/{mission_id}")
    async def forget(mission_id: str) -> dict[str, Any]:
        return service.forget(mission_id)

    return router


def scenario_router(service: ScenarioApplicationService) -> APIRouter:
    router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

    @router.get("")
    async def catalog() -> dict[str, Any]:
        try:
            return await service.list_scenarios()
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.get("/active")
    async def active() -> dict[str, Any]:
        return service.active()

    @router.post("/activate")
    @router.post("/launch")
    async def activate(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.activate(payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    return router


def assistant_router(
    *,
    context: OperationalContextService,
    get_assistant: Callable[[], AssistantOrchestrator],
    status: Callable[[], dict[str, Any]],
    repo_root: Path,
    validate_proposal: Callable[
        [dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]
    ]
    | None = None,
) -> APIRouter:
    """Expose the assistant without coupling its orchestration to FastAPI."""

    router = APIRouter(prefix="/api/assistant", tags=["assistant"])

    @router.get("/status")
    async def assistant_status() -> dict[str, Any]:
        return status()

    @router.get("/operational-picture")
    async def operational_picture(
        since_revision: str | None = None,
        since_checksum: str | None = None,
    ) -> dict[str, Any]:
        try:
            update = await asyncio.to_thread(
                context.get_operational_update,
                since_revision,
                since_checksum=since_checksum,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"operational picture is unavailable: {type(exc).__name__}",
            ) from exc
        return update.to_dict()

    @router.post("/messages")
    async def send_message(payload: AssistantMessageRequest) -> dict[str, Any]:
        try:
            assistant = get_assistant()
            chat_kwargs: dict[str, Any] = {
                "conversation_id": payload.conversation_id,
                "user_message": payload.message,
            }
            if payload.debug:
                chat_kwargs["debug"] = True
            response = await asyncio.to_thread(
                assistant.chat,
                **chat_kwargs,
            )
        except AssistantInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AssistantBusyError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except AssistantConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except AssistantModelResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            # Keep provider exception details (which may include request
            # headers) out of the HTTP response.
            raise HTTPException(
                status_code=502,
                detail=f"assistant model request failed: {type(exc).__name__}",
            ) from exc

        return _assistant_response_payload(
            response,
            validate_proposal=validate_proposal,
        )

    @router.delete("/conversations/{conversation_id}")
    async def reset_conversation(conversation_id: str) -> dict[str, Any]:
        try:
            reset = get_assistant().reset_conversation(conversation_id)
        except AssistantInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AssistantConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"conversation_id": conversation_id, "reset": reset}

    return router
