from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .domain import AgentProfile, MapFeature, MissionRecord, MissionStatus


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


class AgentRepository:
    def __init__(self, path: Path):
        self.path = path
        self._agents = {agent.agent_id: agent for agent in self._load()}

    def _load(self) -> list[AgentProfile]:
        data = read_json(self.path)
        items = data.get("agents", data) if isinstance(data, dict) else data
        return [AgentProfile.from_dict(item) for item in items]

    def get(self, agent_id: str) -> AgentProfile:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"Unknown agent id '{agent_id}'") from exc

    def get_many(self, agent_ids: list[str]) -> list[AgentProfile]:
        return [self.get(agent_id) for agent_id in agent_ids]

    def all(self) -> list[AgentProfile]:
        return list(self._agents.values())


class MapRepository:
    def __init__(self, path: Path):
        self.path = path
        self._features = {feature.feature_id: feature for feature in self._load()}

    def _load(self) -> list[MapFeature]:
        data = read_json(self.path)
        items = data.get("features", data) if isinstance(data, dict) else data
        return [MapFeature.from_dict(item) for item in items]

    def get(self, feature_id: str) -> MapFeature:
        try:
            return self._features[feature_id]
        except KeyError as exc:
            raise KeyError(f"Unknown map feature id '{feature_id}'") from exc

    def all(self) -> list[MapFeature]:
        return list(self._features.values())


class MissionRepository:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, record: MissionRecord) -> None:
        write_json(self.directory / f"{record.mission_id}.json", record.to_dict())

    def get(self, mission_id: str) -> MissionRecord:
        data = read_json(self.directory / f"{mission_id}.json")
        return MissionRecord(
            mission_id=data["mission_id"],
            status=MissionStatus(int(data["status"])),
            config=data["config"],
            feedback=data.get("feedback", {}),
        )


class PlanRepository:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, mission_id: str, plan: dict[str, Any]) -> None:
        write_json(self.directory / f"{mission_id}.json", plan)

    def get(self, mission_id: str) -> dict[str, Any]:
        return read_json(self.directory / f"{mission_id}.json")


class EdgeDispatchRepository:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save_dispatch(self, mission_id: str, agent_id: str, task: dict[str, Any], state: int) -> None:
        write_json(
            self.directory / mission_id / f"{agent_id}.json",
            {"mission_id": mission_id, "agent_id": agent_id, "task_state": state, "task": task},
        )

