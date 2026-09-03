from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import uuid

import pytest

from c2_imugs2.api.services import (
    ApplicationServiceError,
    _ensure_backend_coverage_swaths,
    _preflight_mission_against_world,
)
from c2_imugs2.core.mission_config import load_and_validate_mission


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATHS = sorted((ROOT / "fixtures" / "mission_examples").glob("icd_*.json"))
ALL_EXAMPLE_CAPABILITIES = [
    "ballistic_protection",
    "camera",
    "cargo",
    "casualty_transport",
    "radio_relay",
]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _active_world_for(mission: dict) -> dict:
    return {
        "world_id": "user-provided-world",
        "agents": [
            {
                "agent_id": vehicle_id,
                "name": f"Test vehicle {index + 1}",
                "vehicle_type": "UGV",
                "status": "available",
                "current_location": [4.3900 + index * 0.0002, 50.8440],
                "constraints": {
                    "max_speed": 20.0,
                    "max_acceleration": 20.0,
                    "max_deceleration": 20.0,
                    "max_weight": 100.0,
                    "max_tilt_angle": 5.0,
                    "coverage_width_m": 20.0,
                },
                "capabilities": list(ALL_EXAMPLE_CAPABILITIES),
            }
            for index, vehicle_id in enumerate(mission["vehicles"])
        ],
    }


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_all_icd_examples_are_canonicalizable_world_independent_templates() -> None:
    assert len(EXAMPLE_PATHS) == 10

    for path in EXAMPLE_PATHS:
        mission = load_and_validate_mission(_read(path), repo_root=ROOT)
        uuid.UUID(mission["mission_id"])
        assert "required_world_id" not in mission
        assert not _contains_key(mission, "feature_id")
        assert mission["behavior"] in {0, 1}
        assert mission["objective"]["geometries"]
        for vehicle_id in mission["vehicles"]:
            uuid.UUID(vehicle_id)


def test_every_icd_example_passes_preflight_with_compatible_user_world_agents() -> None:
    for path in EXAMPLE_PATHS:
        mission = load_and_validate_mission(_read(path), repo_root=ROOT)
        _preflight_mission_against_world(mission, _active_world_for(mission))


def test_swaths_come_from_active_world_profiles_only_for_area_survey() -> None:
    reconnaissance = load_and_validate_mission(
        _read(ROOT / "fixtures" / "mission_examples" / "icd_05_reconnaissance.json"),
        repo_root=ROOT,
    )
    world = _active_world_for(reconnaissance)
    compatibility = deepcopy(reconnaissance)
    assert _ensure_backend_coverage_swaths(
        compatibility, world, reconnaissance["vehicles"]
    ) == [20.0]
    assert compatibility["objective"]["coverage_swath_widths"] == [20.0]
    assert "maximum_coverage_distances" not in compatibility["objective"]

    patrol = load_and_validate_mission(
        _read(ROOT / "fixtures" / "mission_examples" / "icd_06_route_patrol.json"),
        repo_root=ROOT,
    )
    assert _ensure_backend_coverage_swaths(
        deepcopy(patrol), _active_world_for(patrol), patrol["vehicles"]
    ) is None


def test_legacy_nested_casevac_point_is_repaired_without_changing_other_geometry() -> None:
    mission = load_and_validate_mission(
        _read(ROOT / "fixtures" / "mission_examples" / "icd_03b_casevac_pickup.json"),
        repo_root=ROOT,
    )
    assert mission["objective"]["geometries"][0]["geometry"]["coordinates"] == [
        4.391,
        50.844,
    ]
    assert mission["objective"]["line_of_sight"]["geometry"]["coordinates"] == [
        4.391,
        50.844,
    ]


def test_original_long_relay_is_rejected_as_mathematically_infeasible() -> None:
    relay = load_and_validate_mission(
        _read(ROOT / "fixtures" / "mission_examples" / "icd_04_communication_relay.json"),
        repo_root=ROOT,
    )
    relay["objective"]["geometries"][0]["geometry"]["coordinates"] = [
        [-75.467187499999994, 46.888402809673634],
        [-74.410253906249994, 46.050554993520711],
    ]

    with pytest.raises(ApplicationServiceError, match="communication relay is infeasible"):
        _preflight_mission_against_world(relay, _active_world_for(relay))


def test_required_capability_is_checked_before_ros_init() -> None:
    mission = load_and_validate_mission(
        _read(ROOT / "fixtures" / "mission_examples" / "icd_02a_goods_pickup.json"),
        repo_root=ROOT,
    )
    world = _active_world_for(mission)
    world["agents"][0]["capabilities"].remove("cargo")

    with pytest.raises(ApplicationServiceError, match="lacks required active-world capabilities"):
        _preflight_mission_against_world(mission, world)
