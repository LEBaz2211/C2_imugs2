from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Behavior(IntEnum):
    NAVIGATE = 0
    COVERAGE = 1
    NAVIGATE_NO_PLANNING = 2


class VehicleFormation(IntEnum):
    NONE = 0
    COLUMN = 1
    LINE = 2
    WEDGE = 3
    VEE = 4
    LEFT_FLANK = 5
    RIGHT_FLANK = 6


class MissionStatus(IntEnum):
    NONE = 0
    PLANNED = 1
    PLANNED_ALTERNATIVE = 2
    PLANNED_FAILED = 3
    ACCEPTED = 4
    STARTED = 5
    PAUSED = 6
    FAILED = 7
    STOPPED = 8
    DELETED = 9
    COMPLETED = 10


class MissionRequest(IntEnum):
    INIT = 0
    APPROVE = 1
    START = 2
    PAUSE = 3
    STOP = 4
    DELETE = 5


class TaskState(IntEnum):
    STOP = 0
    EXECUTE = 1
    PAUSE = 2
    DELETE = 3
    COMPLETED = 4


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    current_location: tuple[float, float]
    name: str = ""
    vehicle_type: str = "UGV"
    status: str = "available"
    constraints: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProfile":
        location = data.get("current_location") or data.get("localization")
        if not isinstance(location, list | tuple) or len(location) < 2:
            raise ValueError(f"Agent {data.get('agent_id', '<unknown>')} has no current_location")
        return cls(
            agent_id=str(data["agent_id"]),
            current_location=(float(location[0]), float(location[1])),
            name=str(data.get("name", "")),
            vehicle_type=str(data.get("vehicle_type", "UGV")),
            status=str(data.get("status", "available")),
            constraints=dict(data.get("constraints", {})),
            capabilities=list(data.get("capabilities", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "vehicle_type": self.vehicle_type,
            "status": self.status,
            "current_location": list(self.current_location),
            "constraints": self.constraints,
            "capabilities": self.capabilities,
        }


@dataclass(frozen=True)
class MapFeature:
    feature_id: str
    feature_type: str
    geometry: dict[str, Any]
    name: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MapFeature":
        properties = dict(data.get("properties", {}))
        feature_id = data.get("feature_id") or properties.get("feature_id") or data.get("id")
        feature_type = data.get("feature_type") or properties.get("feature_type") or "unknown"
        geometry = data.get("geometry")
        if not feature_id or not isinstance(geometry, dict):
            raise ValueError(f"Invalid map feature: {data}")
        return cls(
            feature_id=str(feature_id),
            feature_type=str(feature_type),
            geometry=geometry,
            name=str(data.get("name") or properties.get("name") or feature_id),
            properties=properties,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "feature_type": self.feature_type,
            "geometry": self.geometry,
            "properties": self.properties,
        }


@dataclass
class MissionRecord:
    mission_id: str
    config: dict[str, Any]
    status: MissionStatus = MissionStatus.NONE
    feedback: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "status": int(self.status),
            "config": self.config,
            "feedback": self.feedback,
        }

