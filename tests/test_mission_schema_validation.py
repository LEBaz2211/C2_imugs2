from pathlib import Path
import math

import pytest

from c2_imugs2.core.mission_config import (
    MissionValidationError,
    load_and_validate_mission,
    normalize_mission_config,
    validate_mission_config,
)


ROOT = Path(__file__).resolve().parents[1]


def _mission() -> dict:
    return {
        "mission_id": "schema-test",
        "phase": 0,
        "behavior": 0,
        "vehicles": ["robot-1"],
        "objective": {
            "geometries": [
                {
                    "geometry": {
                        "geometry_type": "Point",
                        "coordinates": [4.0, 50.0],
                    }
                }
            ]
        },
    }


def test_load_and_validate_executes_canonical_schema_with_useful_json_path() -> None:
    mission = _mission()
    mission["phase"] = "planning"

    with pytest.raises(MissionValidationError, match=r"JSON Schema.*\$\.phase.*integer"):
        load_and_validate_mission(mission, repo_root=ROOT)


def test_schema_validation_happens_after_legacy_alias_normalization() -> None:
    mission = _mission()
    mission["objective"] = {
        "geometry": {
            "geometry_type": "Point",
            "coordinates": [4.0, 50.0],
        }
    }

    normalized = load_and_validate_mission(mission, repo_root=ROOT)

    assert normalized["objective"]["geometries"][0]["geometry"]["geometry_type"] == "Point"


def test_direct_legacy_geometry_literals_normalize_to_canonical_envelopes() -> None:
    mission = _mission()
    ring = [[4.0, 50.0], [4.1, 50.0], [4.1, 50.1], [4.0, 50.0]]
    road = [[4.0, 50.0], [4.1, 50.1]]
    mission["objective"]["line_of_sight"] = {
        "geometry_type": "Polygon",
        "coordinates": ring,
    }
    mission["transit"] = {
        "roads": [
            {
                "geometry_type": "LineString",
                "coordinates": road,
            }
        ]
    }
    mission["start"] = {
        "geometry": {
            "geometry_type": "Point",
            "coordinates": [4.0, 50.0],
        }
    }

    normalized = load_and_validate_mission(mission, repo_root=ROOT)

    assert normalized["objective"]["line_of_sight"] == {
        "geometry": {
            "geometry_type": "Polygon",
            "coordinates": [ring],
        }
    }
    assert normalized["transit"]["roads"] == [
        {
            "geometry": {
                "geometry_type": "LineString",
                "coordinates": road,
            }
        }
    ]
    assert normalized["start"]["geometry"] == {
        "geometry": {
            "geometry_type": "Point",
            "coordinates": [4.0, 50.0],
        }
    }


@pytest.mark.parametrize(
    ("field_path", "value", "message"),
    [
        (
            ("objective", "line_of_sight"),
            {
                "geometry": {
                    "geometry_type": "LineString",
                    "coordinates": [[4.0, 50.0]],
                }
            },
            "at least two positions",
        ),
        (
            ("objective", "vehicle_orientation_origin"),
            {
                "geometry": {
                    "geometry_type": "Point",
                    "coordinates": [math.nan, 50.0],
                }
            },
            "finite numeric coordinates",
        ),
        (
            ("transit", "geofence"),
            {
                "geometry_type": "Polygon",
                "coordinates": [
                    [4.0, 50.0],
                    [4.1, 50.0],
                    [4.1, 50.1],
                    [4.0, 50.1],
                ],
            },
            "must be closed",
        ),
        (
            ("transit", "roads"),
            [
                {
                    "geometry": {
                        "geometry_type": "LineString",
                        "coordinates": [[4.0, 50.0], [math.inf, 50.1]],
                    }
                }
            ],
            "finite numeric coordinates",
        ),
        (
            ("start", "geometry"),
            {
                "geometry_type": "Point",
                "coordinates": [4.0],
            },
            "exactly \\[longitude, latitude\\]",
        ),
    ],
)
def test_semantic_validation_covers_every_recognized_optional_geometry_ref(
    field_path: tuple[str, str], value: object, message: str
) -> None:
    mission = _mission()
    section = mission.setdefault(field_path[0], {})
    section[field_path[1]] = value
    normalized = normalize_mission_config(mission)

    with pytest.raises(MissionValidationError, match=message):
        validate_mission_config(normalized)


def test_schema_rejects_ambiguous_geometry_reference() -> None:
    mission = _mission()
    mission["objective"]["geometries"][0]["feature_id"] = "point-1"

    with pytest.raises(MissionValidationError, match=r"\$\.objective\.geometries\[0\]"):
        load_and_validate_mission(mission, repo_root=ROOT)


def test_non_object_mission_has_domain_error_instead_of_attribute_error() -> None:
    with pytest.raises(MissionValidationError, match="JSON object"):
        load_and_validate_mission([])  # type: ignore[arg-type]


def test_wrong_objective_type_reaches_schema_validation() -> None:
    mission = _mission()
    mission["objective"] = None

    with pytest.raises(MissionValidationError, match=r"JSON Schema.*\$\.objective.*object"):
        load_and_validate_mission(mission, repo_root=ROOT)


@pytest.mark.parametrize(
    ("geometry_type", "coordinates"),
    [
        ("Point", [4.0, 50.0]),
        ("LineString", [[4.0, 50.0], [4.1, 50.1]]),
        (
            "Polygon",
            [[[4.0, 50.0], [4.1, 50.0], [4.1, 50.1], [4.0, 50.0]]],
        ),
    ],
)
def test_supported_inline_geojson_shapes_are_accepted(
    geometry_type: str, coordinates: list,
) -> None:
    mission = _mission()
    mission["objective"]["geometries"][0]["geometry"] = {
        "geometry_type": geometry_type,
        "coordinates": coordinates,
    }

    validated = load_and_validate_mission(mission, repo_root=ROOT)

    assert validated["objective"]["geometries"][0]["geometry"] == {
        "geometry_type": geometry_type,
        "coordinates": coordinates,
    }


@pytest.mark.parametrize(
    ("geometry_type", "coordinates"),
    [
        ("Banana", [4.0, 50.0]),
        ("Point", "not coordinates"),
        ("Point", [4.0, 50.0, 12.0]),
        ("LineString", [[4.0, 50.0]]),
        ("Polygon", [[4.0, 50.0], [4.1, 50.0], [4.0, 50.0]]),
    ],
)
def test_schema_rejects_unsupported_or_malformed_inline_geometry(
    geometry_type: str, coordinates: object,
) -> None:
    mission = _mission()
    mission["objective"]["geometries"][0]["geometry"] = {
        "geometry_type": geometry_type,
        "coordinates": coordinates,
    }

    with pytest.raises(
        MissionValidationError,
        match=r"JSON Schema.*\$\.objective\.geometries\[0\]\.geometry",
    ):
        load_and_validate_mission(mission, repo_root=ROOT)


@pytest.mark.parametrize(
    "coordinates",
    [
        [181.0, 50.0],
        [4.0, -91.0],
    ],
)
def test_schema_rejects_out_of_range_inline_lon_lat(coordinates: list[float]) -> None:
    mission = _mission()
    mission["objective"]["geometries"][0]["geometry"]["coordinates"] = coordinates

    with pytest.raises(
        MissionValidationError,
        match=r"JSON Schema.*\$\.objective\.geometries\[0\]\.geometry",
    ):
        load_and_validate_mission(mission, repo_root=ROOT)


@pytest.mark.parametrize("coordinate", [math.nan, math.inf, -math.inf])
def test_semantic_validation_rejects_non_finite_inline_coordinates(
    coordinate: float,
) -> None:
    mission = _mission()
    mission["objective"]["geometries"][0]["geometry"]["coordinates"] = [
        coordinate,
        50.0,
    ]

    with pytest.raises(MissionValidationError, match="finite numeric"):
        validate_mission_config(mission)


def test_polygon_rings_must_be_closed_and_non_degenerate() -> None:
    mission = _mission()
    geometry = mission["objective"]["geometries"][0]["geometry"]
    geometry["geometry_type"] = "Polygon"
    geometry["coordinates"] = [
        [[4.0, 50.0], [4.1, 50.0], [4.1, 50.1], [4.0, 50.1]]
    ]

    with pytest.raises(MissionValidationError, match="must be closed"):
        load_and_validate_mission(mission, repo_root=ROOT)

    geometry["coordinates"] = [
        [[4.0, 50.0], [4.0, 50.0], [4.0, 50.0], [4.0, 50.0]]
    ]
    with pytest.raises(MissionValidationError, match="three distinct"):
        load_and_validate_mission(mission, repo_root=ROOT)


def test_polygon_interior_rings_are_rejected_by_schema_and_semantics() -> None:
    mission = _mission()
    geometry = mission["objective"]["geometries"][0]["geometry"]
    geometry["geometry_type"] = "Polygon"
    geometry["coordinates"] = [
        [[4.0, 50.0], [4.2, 50.0], [4.2, 50.2], [4.0, 50.0]],
        [[4.05, 50.05], [4.1, 50.05], [4.1, 50.1], [4.05, 50.05]],
    ]

    with pytest.raises(
        MissionValidationError,
        match=r"JSON Schema.*\$\.objective\.geometries\[0\]\.geometry",
    ):
        load_and_validate_mission(mission, repo_root=ROOT)

    with pytest.raises(MissionValidationError, match="cannot contain interior rings"):
        validate_mission_config(mission)


def test_feature_id_references_remain_geometry_agnostic() -> None:
    mission = _mission()
    mission["objective"]["geometries"] = [
        {"feature_id": "legacy-multipoint-or-external-asset"}
    ]
    mission["objective"]["vehicle_orientation_origin"] = {
        "feature_id": "legacy-orientation-origin"
    }
    mission["objective"]["line_of_sight"] = {"feature_id": "legacy-line-of-sight"}
    mission["start"] = {"geometry": {"feature_id": "legacy-start"}}
    mission["transit"] = {
        "geofence": {"feature_id": "legacy-geofence"},
        "roads": [{"feature_id": "legacy-road"}],
    }

    validated = load_and_validate_mission(mission, repo_root=ROOT)

    assert validated["objective"]["geometries"] == [
        {"feature_id": "legacy-multipoint-or-external-asset"}
    ]
    assert validated["objective"]["vehicle_orientation_origin"] == {
        "feature_id": "legacy-orientation-origin"
    }
    assert validated["objective"]["line_of_sight"] == {
        "feature_id": "legacy-line-of-sight"
    }
    assert validated["start"]["geometry"] == {"feature_id": "legacy-start"}
    assert validated["transit"]["geofence"] == {"feature_id": "legacy-geofence"}
    assert validated["transit"]["roads"] == [{"feature_id": "legacy-road"}]
