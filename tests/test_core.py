from pathlib import Path
from typing import Any

from c2_imugs2.cli import build_service
from c2_imugs2.domain import AgentProfile
from c2_imugs2.domain import MissionRequest, MissionStatus
from c2_imugs2.mission_config import load_and_validate_mission
from c2_imugs2.mission_service import MissionService
from c2_imugs2.repositories import read_json
from c2_imugs2.repositories import AgentRepository, EdgeDispatchRepository, MissionRepository, PlanRepository
from c2_imugs2.task_plan import validate_task_plan


ROOT = Path(__file__).resolve().parents[1]


class FakePlanner:
    def create_plan(self, mission_config: dict[str, Any], agents: list[AgentProfile]) -> dict[str, Any]:
        return {
            "mission_id": mission_config["mission_id"],
            "tasks": {
                agents[0].agent_id: {
                    "task_id": "fake-task",
                    "primitives": [],
                    "objectives": [],
                }
            },
        }


def test_normalizes_legacy_objective_geometry():
    mission = {
        "mission_id": "legacy",
        "behavior": 0,
        "vehicles": ["ugv-alpha"],
        "objective": {
            "geometry": {
                "geometry_type": "Point",
                "coordinates": [4.0, 50.0],
            }
        },
    }
    normalized = load_and_validate_mission(mission)
    assert "geometries" in normalized["objective"]
    assert normalized["objective"]["geometries"][0]["geometry"]["geometry_type"] == "Point"


def test_normalizes_old_icd_aliases():
    mission = {
        "mission_id": "legacy-aliases",
        "behavior": 0,
        "vehicles": ["ugv-alpha"],
        "transit": {
            "optimalization": {"road_usage": 1},
            "vehicle_constraints": {"max_acceleration": 1.0},
            "desired_speed": 3.5,
        },
        "objective": {
            "geometry": {"feature_id": "delivery-point-east"},
            "maximize_area_coverage": True,
            "vehicle_orientation": 90,
        },
    }

    normalized = load_and_validate_mission(mission)

    assert normalized["transit"]["optimization"] == {"road_usage": 1}
    assert normalized["transit"]["desired_vehicle_constraints"]["max_acceleration"] == 1.0
    assert normalized["transit"]["desired_vehicle_constraints"]["max_speed"] == 3.5
    assert normalized["objective"]["geometries"] == [{"feature_id": "delivery-point-east"}]
    assert normalized["objective"]["maximize_coverage"] is True
    assert normalized["objective"]["vehicle_orientation"] == [90]


def test_service_init_approve_start(tmp_path):
    service = build_service(ROOT / "fixtures", tmp_path)
    mission = read_json(ROOT / "fixtures" / "missions" / "simple_navigation.json")

    result = service.init_mission(mission)
    assert result.status == MissionStatus.PLANNED
    validate_task_plan(result.plan)
    assert result.plan["tasks"]

    accepted = service.change_status(result.mission_id, MissionRequest.APPROVE)
    assert accepted.status == MissionStatus.ACCEPTED

    started = service.change_status(result.mission_id, MissionRequest.START)
    assert started.status == MissionStatus.STARTED
    assert started.feedback["tasks"]


def test_service_accepts_swappable_planner(tmp_path):
    service = MissionService(
        missions=MissionRepository(tmp_path / "missions"),
        plans=PlanRepository(tmp_path / "plans"),
        agents=AgentRepository(ROOT / "fixtures" / "agents.json"),
        planner=FakePlanner(),
        edge_dispatch=EdgeDispatchRepository(tmp_path / "edge_dispatch"),
    )
    mission = read_json(ROOT / "fixtures" / "missions" / "simple_navigation.json")

    result = service.init_mission(mission)

    assert result.plan["tasks"]["ugv-alpha"]["task_id"] == "fake-task"
