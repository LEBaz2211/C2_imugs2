from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .domain import MissionRequest
from .mission_service import MissionService
from .planner import SimplePlanner
from .repositories import AgentRepository, EdgeDispatchRepository, MapRepository, MissionRepository, PlanRepository, read_json


DEFAULT_FIXTURES = Path("fixtures")
DEFAULT_RUNTIME = Path("data/runtime")


def build_service(fixtures_dir: Path = DEFAULT_FIXTURES, runtime_dir: Path = DEFAULT_RUNTIME) -> MissionService:
    map_repository = MapRepository(fixtures_dir / "map_features.json")
    agent_repository = AgentRepository(fixtures_dir / "agents.json")
    planner = SimplePlanner(map_repository)
    return MissionService(
        missions=MissionRepository(runtime_dir / "missions"),
        plans=PlanRepository(runtime_dir / "plans"),
        agents=agent_repository,
        planner=planner,
        edge_dispatch=EdgeDispatchRepository(runtime_dir / "edge_dispatch"),
    )


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    service = build_service(Path(args.fixtures), Path(args.runtime))
    mission = read_json(Path(args.fixtures) / "missions" / "simple_navigation.json")
    result = service.init_mission(mission)
    service.change_status(result.mission_id, MissionRequest.APPROVE)
    started = service.change_status(result.mission_id, MissionRequest.START)
    return {
        "mission_id": result.mission_id,
        "status": int(started.status),
        "plan": result.plan,
        "feedback": started.feedback,
    }


def run_init(args: argparse.Namespace) -> dict[str, Any]:
    service = build_service(Path(args.fixtures), Path(args.runtime))
    result = service.init_mission(read_json(Path(args.mission)))
    return {
        "mission_id": result.mission_id,
        "status": int(result.status),
        "plan": result.plan,
        "feedback": result.feedback,
    }


def run_status(args: argparse.Namespace) -> dict[str, Any]:
    service = build_service(Path(args.fixtures), Path(args.runtime))
    record = service.change_status(args.mission_id, MissionRequest[args.request.upper()])
    return record.to_dict()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C2 iMUGS2 replacement system CLI")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--runtime", default=str(DEFAULT_RUNTIME))
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="Run init -> approve -> start on the sample mission")
    demo_parser.set_defaults(func=run_demo)

    init_parser = subparsers.add_parser("init", help="Initialize a mission from JSON")
    init_parser.add_argument("mission")
    init_parser.set_defaults(func=run_init)

    status_parser = subparsers.add_parser("status", help="Change mission status")
    status_parser.add_argument("mission_id")
    status_parser.add_argument("request", choices=[request.name.lower() for request in MissionRequest])
    status_parser.set_defaults(func=run_status)

    args = parser.parse_args(argv)
    output = args.func(args)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
