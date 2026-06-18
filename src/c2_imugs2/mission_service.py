from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import MissionRecord, MissionRequest, MissionStatus, TaskState
from .mission_config import load_and_validate_mission
from .ports import (
    AgentRepositoryPort,
    EdgeDispatcherPort,
    MissionRepositoryPort,
    PlanRepositoryPort,
    PlannerPort,
)


@dataclass
class InitMissionResult:
    mission_id: str
    status: MissionStatus
    plan: dict[str, Any]
    feedback: dict[str, Any]


class MissionService:
    def __init__(
        self,
        missions: MissionRepositoryPort,
        plans: PlanRepositoryPort,
        agents: AgentRepositoryPort,
        planner: PlannerPort,
        edge_dispatch: EdgeDispatcherPort,
    ):
        self.missions = missions
        self.plans = plans
        self.agents = agents
        self.planner = planner
        self.edge_dispatch = edge_dispatch

    def init_mission(self, config: dict[str, Any]) -> InitMissionResult:
        mission_config = load_and_validate_mission(config)
        mission_id = mission_config["mission_id"]
        selected_agents = self.agents.get_many(mission_config["vehicles"])

        record = MissionRecord(mission_id=mission_id, config=mission_config, status=MissionStatus.NONE)
        self.missions.save(record)

        plan = self.planner.create_plan(mission_config, selected_agents)
        self.plans.save(mission_id, plan)

        feedback = self._feedback(mission_config, plan, MissionStatus.PLANNED)
        record.status = MissionStatus.PLANNED
        record.feedback = feedback
        self.missions.save(record)
        return InitMissionResult(mission_id=mission_id, status=record.status, plan=plan, feedback=feedback)

    def change_status(self, mission_id: str, request: MissionRequest) -> MissionRecord:
        record = self.missions.get(mission_id)
        if request == MissionRequest.APPROVE:
            record.status = MissionStatus.ACCEPTED
        elif request == MissionRequest.START:
            record.status = MissionStatus.STARTED
            self._dispatch_to_edges(mission_id)
        elif request == MissionRequest.PAUSE:
            record.status = MissionStatus.PAUSED
        elif request == MissionRequest.STOP:
            record.status = MissionStatus.STOPPED
        elif request == MissionRequest.DELETE:
            record.status = MissionStatus.DELETED
        elif request == MissionRequest.INIT:
            record.status = MissionStatus.NONE
        else:
            raise ValueError(f"Unsupported mission request: {request}")

        record.feedback = self._feedback(record.config, self.plans.get(mission_id), record.status)
        self.missions.save(record)
        return record

    def _dispatch_to_edges(self, mission_id: str) -> None:
        plan = self.plans.get(mission_id)
        for agent_id, task in plan["tasks"].items():
            self.edge_dispatch.save_dispatch(mission_id, agent_id, task, int(TaskState.EXECUTE))

    def _feedback(self, mission_config: dict[str, Any], plan: dict[str, Any], status: MissionStatus) -> dict[str, Any]:
        tasks = []
        for agent_id, task in plan["tasks"].items():
            waypoints = []
            for objective in task["objectives"]:
                for primitive in objective["primitives"]:
                    params = primitive.get("parameters", {})
                    if "coordinates" in params:
                        waypoints.append(
                            {
                                "waypoint_id": primitive["primitive_id"],
                                "coordinates": params["coordinates"],
                                "average_speed": params.get("speed"),
                            }
                        )
            tasks.append({"vehicle_id": agent_id, "task_id": task["task_id"], "waypoints": waypoints})

        return {
            "mission_id": mission_config["mission_id"],
            "status": int(status),
            "behavior": int(mission_config["behavior"]),
            "tasks": tasks,
            "issue": 0,
        }
