from __future__ import annotations

from typing import Any, Protocol

from .domain import AgentProfile, MapFeature, MissionRecord


class AgentRepositoryPort(Protocol):
    def get(self, agent_id: str) -> AgentProfile: ...

    def get_many(self, agent_ids: list[str]) -> list[AgentProfile]: ...

    def all(self) -> list[AgentProfile]: ...


class MapRepositoryPort(Protocol):
    def get(self, feature_id: str) -> MapFeature: ...

    def all(self) -> list[MapFeature]: ...


class MissionRepositoryPort(Protocol):
    def save(self, record: MissionRecord) -> None: ...

    def get(self, mission_id: str) -> MissionRecord: ...


class PlanRepositoryPort(Protocol):
    def save(self, mission_id: str, plan: dict[str, Any]) -> None: ...

    def get(self, mission_id: str) -> dict[str, Any]: ...


class EdgeDispatcherPort(Protocol):
    def save_dispatch(self, mission_id: str, agent_id: str, task: dict[str, Any], state: int) -> None: ...


class PlannerPort(Protocol):
    def create_plan(self, mission_config: dict[str, Any], agents: list[AgentProfile]) -> dict[str, Any]: ...

