from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .services import (
    ApplicationServiceError,
    BackendMissionApplicationService,
    WorldApplicationService,
)
from ..assistant.config import AssistantConfigurationError
from ..assistant.models import AssistantResponse, AssistantWorldBinding
from ..assistant.orchestrator import (
    AssistantBusyError,
    AssistantInputError,
    AssistantModelResponseError,
    AssistantOrchestrator,
)
from ..core.mission_config import MissionValidationError
from ..core.models import MissionRequest
from ..operations.service import OperationalContextService


class AssistantOperationalPictureOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[
        Literal["agents", "missions", "plans", "health", "warnings"]
    ] = Field(max_length=5)
    mission_ids: list[str] | None = Field(default=None, max_length=64)
    operator_missions: list[dict[str, Any]] = Field(
        default_factory=list, max_length=64
    )
    item_ids: dict[
        Literal["agents", "missions", "plans", "health", "warnings"],
        list[str],
    ] = Field(default_factory=dict, max_length=5)
    exclude_paths: list[str] = Field(default_factory=list, max_length=256)

    @field_validator("exclude_paths")
    @classmethod
    def validate_exclude_paths(cls, value: list[str]) -> list[str]:
        for path in value:
            if not isinstance(path, str) or not path.strip():
                raise ValueError("operational picture exclude paths must be text")
            if len(path) > 256:
                raise ValueError("operational picture exclude path is too long")
        return value

    @field_validator("item_ids")
    @classmethod
    def validate_item_ids(
        cls, value: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        for section, item_ids in value.items():
            if len(item_ids) > 256:
                raise ValueError(
                    f"operational picture {section} item selection exceeds 256 IDs"
                )
        return value


class AssistantMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(min_length=1, max_length=256)
    message: str = Field(min_length=1)
    debug: bool = False
    operational_picture: AssistantOperationalPictureOptions | None = None


def _http_error(exc: ApplicationServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _require_complete_world_binding(
    binding: AssistantWorldBinding | None,
    *,
    source: str,
) -> AssistantWorldBinding:
    if binding is None:
        raise ValueError(f"{source} environment binding is absent")
    missing = binding.missing_identity_fields()
    if missing:
        raise ValueError(
            f"{source} environment binding is incomplete: {', '.join(missing)}"
        )
    return binding


def _binding_is_ready(binding: AssistantWorldBinding) -> bool:
    return binding.ready and (binding.status or "").lower() == "ready"


def _require_same_world_binding(
    picture_binding: AssistantWorldBinding,
    active_binding: AssistantWorldBinding,
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

    active_binding: AssistantWorldBinding | None = None
    try:
        picture_binding = _require_complete_world_binding(
            response.picture_world_binding,
            source="operational picture",
        )
        if validate_proposal is None:
            raise ValueError(
                "post-generation current environment validation is unavailable"
            )
        validated, active_world = validate_proposal(proposal)
        active_binding = _require_complete_world_binding(
            AssistantWorldBinding.from_mapping(active_world),
            source="post-generation current environment",
        )
        _require_same_world_binding(picture_binding, active_binding)
    except (ApplicationServiceError, MissionValidationError, TypeError, ValueError) as exc:
        result["mission_proposal_validation"] = {
            "valid": False,
            "scope": "schema_semantics_and_current_environment",
            "issues": [{"message": str(exc)}],
        }
        if active_binding is not None:
            result["mission_proposal_validation"]["world_binding"] = (
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
            "world_binding": active_binding.model_dump(mode="json"),
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


def world_router(service: WorldApplicationService) -> APIRouter:
    router = APIRouter(prefix="/api/worlds", tags=["worlds"])

    @router.get("")
    async def catalog() -> dict[str, Any]:
        try:
            return await service.list_worlds()
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.post("")
    async def create(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.create_world(payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.get("/active")
    async def active() -> dict[str, Any]:
        return service.active()

    @router.post("/active/features")
    async def create_live_feature(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.create_live_feature, payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.put("/active/features/{feature_id}")
    async def update_live_feature(feature_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.update_live_feature, feature_id, payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.delete("/active/features/{feature_id}")
    async def delete_live_feature(feature_id: str) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.delete_live_feature, feature_id)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.get("/{world_id}")
    async def get(world_id: str) -> dict[str, Any]:
        try:
            return await service.get_world(world_id)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.put("/{world_id}")
    async def update(world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.update_world(world_id, payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.delete("/{world_id}")
    async def delete(world_id: str) -> dict[str, Any]:
        try:
            return await service.delete_world(world_id)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.post("/{world_id}/launch")
    async def launch(world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            revision = payload.get("revision")
            if isinstance(revision, bool) or not isinstance(revision, int):
                raise ApplicationServiceError(422, "revision must be an integer")
            return await service.launch(world_id, revision)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.post("/{world_id}/road-imports/query")
    async def query_road_import(world_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.query_road_import, world_id, payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.get("/{world_id}/road-imports/{import_id}")
    async def get_road_import(world_id: str, import_id: str) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.get_road_import, world_id, import_id)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.delete("/{world_id}/road-imports/{import_id}")
    async def delete_road_import(
        world_id: str,
        import_id: str,
        revision: int = Query(..., ge=1),
    ) -> dict[str, Any]:
        try:
            return await service.invoke(
                service.world_runtime.delete_road_import, world_id, import_id, revision
            )
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    return router


def vehicle_model_router(service: WorldApplicationService) -> APIRouter:
    router = APIRouter(prefix="/api/vehicle-models", tags=["vehicle-models"])

    @router.get("")
    async def list_models() -> dict[str, Any]:
        try:
            return {"vehicle_models": await service.invoke(service.world_runtime.list_vehicle_models)}
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.post("")
    async def create_model(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.create_vehicle_model, payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.put("/{model_id}")
    async def update_model(model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.update_vehicle_model, model_id, payload)
        except ApplicationServiceError as exc:
            raise _http_error(exc) from exc

    @router.delete("/{model_id}")
    async def delete_model(model_id: str) -> dict[str, Any]:
        try:
            return await service.invoke(service.world_runtime.delete_vehicle_model, model_id)
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

    @router.post("/operational-picture/preview")
    async def operational_picture_preview(
        payload: AssistantOperationalPictureOptions,
    ) -> dict[str, Any]:
        try:
            assistant = get_assistant()
            return await asyncio.to_thread(
                assistant.preview_operational_picture,
                payload.model_dump(mode="json"),
            )
        except AssistantInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except AssistantConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "operational picture preview is unavailable: "
                    f"{type(exc).__name__}"
                ),
            ) from exc

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
            if payload.operational_picture is not None:
                chat_kwargs["operational_picture_options"] = (
                    payload.operational_picture.model_dump(mode="json")
                )
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
