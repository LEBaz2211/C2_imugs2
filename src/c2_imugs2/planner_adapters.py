from __future__ import annotations

from typing import Any

from .domain import AgentProfile
from .ports import PlannerPort
from .task_plan import validate_task_plan


class ExternalPlannerAdapter:
    """Adapter seam for replacing SimplePlanner with the actual planner later.

    The old planner boundary was effectively:

    - input: mission id, mission_config JSON, selected Agent states
    - output: task_plan JSON shaped as {mission_id, tasks: {agent_id: ...}}

    A ROS2 service adapter, HTTP client, subprocess adapter, or imported planner
    library can all implement this class's small contract.
    """

    def __init__(self, client: PlannerPort):
        self.client = client

    def create_plan(self, mission_config: dict[str, Any], agents: list[AgentProfile]) -> dict[str, Any]:
        plan = self.client.create_plan(mission_config, agents)
        validate_task_plan(plan)
        return plan


class StaticPlannerAdapter:
    """Tiny test/dummy planner adapter useful for UI or API development."""

    def __init__(self, plan: dict[str, Any]):
        self.plan = plan

    def create_plan(self, mission_config: dict[str, Any], agents: list[AgentProfile]) -> dict[str, Any]:
        plan = dict(self.plan)
        plan["mission_id"] = mission_config["mission_id"]
        validate_task_plan(plan)
        return plan

