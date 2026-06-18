from __future__ import annotations

import uuid
from typing import Any


def waypoint_task(agent_id: str, waypoints: list[list[float]], speed: float, mission_id: str) -> tuple[str, dict[str, Any]]:
    task_id = str(uuid.uuid4())
    primitive_id = str(uuid.uuid4())

    primitive = {
        "primitive_id": primitive_id,
        "primitive_type": "waypoint",
        "continuous": False,
        "primitive_inputs": [],
        "primitive_outputs": [],
        "completion": {
            "ends_objective": True,
            "ends_task": False,
            "followed_by_primitives": [],
            "inherit_other_primitives": False,
            "resume_after": False,
        },
    }

    objectives = []
    for waypoint in waypoints:
        objectives.append(
            {
                "objective_id": str(uuid.uuid4()),
                "objective_type": "combined_primitives",
                "parallel_execution": True,
                "primitives": [
                    {
                        "primitive_id": primitive_id,
                        "parameters": {
                            "coordinates": waypoint,
                            "speed": speed,
                            "max_speed": speed,
                            "mobility_profile": 0,
                            "wait_time": 0,
                        },
                    }
                ],
            }
        )

    return agent_id, {"task_id": task_id, "primitives": [primitive], "objectives": objectives}


def validate_task_plan(plan: dict[str, Any]) -> None:
    if not isinstance(plan.get("mission_id"), str):
        raise ValueError("Task plan must contain string mission_id")
    tasks = plan.get("tasks")
    if not isinstance(tasks, dict) or not tasks:
        raise ValueError("Task plan must contain non-empty tasks object")
    for agent_id, task in tasks.items():
        if not isinstance(agent_id, str) or not isinstance(task, dict):
            raise ValueError("Task plan tasks must be keyed by agent id")
        for field in ("task_id", "primitives", "objectives"):
            if field not in task:
                raise ValueError(f"Task for agent {agent_id} is missing {field}")

