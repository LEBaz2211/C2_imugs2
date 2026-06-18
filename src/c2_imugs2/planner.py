from __future__ import annotations

from collections import defaultdict
from typing import Any

from .domain import AgentProfile, Behavior
from .geometry import Point, distance, geometry_points, representative_point
from .ports import MapRepositoryPort
from .task_plan import validate_task_plan, waypoint_task


class SimplePlanner:
    """Deterministic planner that preserves the old planner's input/output contract."""

    def __init__(self, map_repository: MapRepositoryPort):
        self.map_repository = map_repository

    def create_plan(self, mission_config: dict[str, Any], agents: list[AgentProfile]) -> dict[str, Any]:
        if not agents:
            raise ValueError("Planner requires at least one agent")

        destinations = self._destinations(mission_config)
        speed = self._mission_speed(mission_config, agents)
        allocations = self._allocate(agents, destinations, preserve_order=bool(mission_config["objective"].get("vehicle_order")))

        tasks = {}
        for agent in agents:
            waypoints = allocations.get(agent.agent_id, [])
            if not waypoints:
                continue
            agent_id, task = waypoint_task(
                agent_id=agent.agent_id,
                waypoints=[[point[0], point[1]] for point in waypoints],
                speed=speed,
                mission_id=mission_config["mission_id"],
            )
            tasks[agent_id] = task

        plan = {"mission_id": mission_config["mission_id"], "tasks": tasks}
        validate_task_plan(plan)
        return plan

    def _destinations(self, mission_config: dict[str, Any]) -> list[Point]:
        behavior = Behavior(int(mission_config["behavior"]))
        destinations: list[Point] = []
        for geometry_ref in mission_config["objective"]["geometries"]:
            geometry = self._resolve_geometry(geometry_ref)
            if behavior == Behavior.NAVIGATE and (geometry.get("type") or geometry.get("geometry_type")) == "MultiPoint":
                destinations.extend(geometry_points(geometry))
            else:
                destinations.append(representative_point(geometry))
        if not destinations:
            raise ValueError("Mission contains no usable objective destinations")
        return destinations

    def _resolve_geometry(self, geometry_ref: dict[str, Any]) -> dict[str, Any]:
        if "feature_id" in geometry_ref:
            return self.map_repository.get(geometry_ref["feature_id"]).geometry
        return geometry_ref["geometry"]

    def _mission_speed(self, mission_config: dict[str, Any], agents: list[AgentProfile]) -> float:
        transit = mission_config.get("transit") or {}
        constraints = transit.get("desired_vehicle_constraints") or transit.get("vehicle_constraints") or {}
        if "max_speed" in constraints:
            return float(constraints["max_speed"])
        agent_speeds = [
            float(agent.constraints["max_speed"])
            for agent in agents
            if isinstance(agent.constraints.get("max_speed"), int | float)
        ]
        return min(agent_speeds) if agent_speeds else 1.0

    def _allocate(self, agents: list[AgentProfile], destinations: list[Point], preserve_order: bool) -> dict[str, list[Point]]:
        allocations: dict[str, list[Point]] = defaultdict(list)
        remaining = list(destinations)

        if preserve_order:
            for index, destination in enumerate(destinations):
                allocations[agents[index % len(agents)].agent_id].append(destination)
            return dict(allocations)

        while remaining:
            for agent in agents:
                if not remaining:
                    break
                best = min(remaining, key=lambda point: distance(agent.current_location, point))
                allocations[agent.agent_id].append(best)
                remaining.remove(best)
        return dict(allocations)
