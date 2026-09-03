"""Canonical mission normalization and schema/semantic validation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import json
import math
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class MissionValidationError(ValueError):
    pass


_SUPPORTED_INLINE_GEOMETRY_TYPES = {"Point", "MultiPoint", "LineString", "Polygon"}


def normalize_mission_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy mission spellings/shapes into the replacement canonical form."""
    if not isinstance(config, dict):
        raise MissionValidationError("Mission config must be a JSON object")
    normalized = deepcopy(config)

    # The original ICD defines a missing/null behavior as NAVIGATE. Keep this
    # default at the canonical boundary so every downstream implementation sees
    # an explicit behavior value.
    if normalized.get("behavior") is None:
        normalized["behavior"] = 0

    objective = normalized.setdefault("objective", {})
    if isinstance(objective, dict):
        if "geometries" not in objective and "geometry" in objective:
            objective["geometries"] = [_normalize_geometry_ref(objective.pop("geometry"))]
        if "geometries" not in objective and "feature_id" in objective:
            objective["geometries"] = [{"feature_id": objective.pop("feature_id")}]
        if isinstance(objective.get("geometries"), list):
            objective["geometries"] = [
                _normalize_geometry_ref(geometry_ref) for geometry_ref in objective["geometries"]
            ]
        for key in ("vehicle_orientation_origin", "line_of_sight"):
            if isinstance(objective.get(key), dict):
                objective[key] = _normalize_geometry_ref(objective[key])
        if "maximize_area_coverage" in objective and "maximize_coverage" not in objective:
            objective["maximize_coverage"] = objective.pop("maximize_area_coverage")
        if isinstance(objective.get("vehicle_orientation"), int | float):
            objective["vehicle_orientation"] = [objective["vehicle_orientation"]]

        # COVERAGE means survey/patrol by default. Explicit false remains the
        # supported way to request reach-only behavior for a coverage geometry.
        if normalized.get("behavior") == 1 and "maximize_coverage" not in objective:
            objective["maximize_coverage"] = True

    for section_name in ("start", "transit", "objective"):
        section = normalized.get(section_name)
        if not isinstance(section, dict):
            continue
        if "vehicle_formation_distances" in section and "vehicle_formation_distance" not in section:
            section["vehicle_formation_distance"] = section.pop("vehicle_formation_distances")
        if "maximum_coverage_distances" not in section and "maximize_coverage_distances" in section:
            section["maximum_coverage_distances"] = section.pop("maximize_coverage_distances")

    transit = normalized.get("transit")
    if isinstance(transit, dict):
        if isinstance(transit.get("geofence"), dict):
            transit["geofence"] = _normalize_geometry_ref(transit["geofence"])
        if isinstance(transit.get("roads"), list):
            transit["roads"] = [
                _normalize_geometry_ref(road) if isinstance(road, dict) else road
                for road in transit["roads"]
            ]
        if "optimalization" in transit and "optimization" not in transit:
            transit["optimization"] = transit.pop("optimalization")
        if "vehicle_constraints" in transit and "desired_vehicle_constraints" not in transit:
            transit["desired_vehicle_constraints"] = transit.pop("vehicle_constraints")
        if "desired_speed" in transit:
            desired_speed = transit.pop("desired_speed")
            constraints = transit.setdefault("desired_vehicle_constraints", {})
            if not isinstance(constraints, dict):
                constraints = {}
                transit["desired_vehicle_constraints"] = constraints
            if isinstance(constraints, dict) and "max_speed" not in constraints:
                constraints["max_speed"] = desired_speed
        if "geofence_maximum_coverage" in transit and "geofence_maximize_coverage" not in transit:
            transit["geofence_maximize_coverage"] = transit.pop("geofence_maximum_coverage")

    start = normalized.get("start")
    if isinstance(start, dict):
        if isinstance(start.get("geometry"), dict):
            start["geometry"] = _normalize_geometry_ref(start["geometry"])
        if "vehicle_orientations" in start and "vehicle_orientation" not in start:
            start["vehicle_orientation"] = start.pop("vehicle_orientations")

    normalized.setdefault("schema_version", "1.0")
    return normalized


def _normalize_geometry_ref(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return value
    if "feature_id" in value and "geometry" not in value:
        return {"feature_id": value["feature_id"]}
    geometry = value.get("geometry")
    if isinstance(geometry, dict) and "feature_id" in geometry and "coordinates" not in geometry:
        return {"feature_id": geometry["feature_id"]}
    if isinstance(geometry, dict):
        normalized = deepcopy(value)
        normalized["geometry"] = _normalize_inline_geometry_literal(geometry)
        return normalized
    if "geometry_type" in value or "coordinates" in value:
        return {"geometry": _normalize_inline_geometry_literal(value)}
    return value


def _normalize_inline_geometry_literal(value: dict[str, Any]) -> dict[str, Any]:
    """Lift the backend's flat Polygon coordinates into the canonical ring shape."""

    normalized = deepcopy(value)
    coordinates = normalized.get("coordinates")
    if normalized.get("geometry_type") == "Point":
        # Several original ICD examples wrapped Point coordinates as [[[lon,
        # lat]]]. Accept that legacy mistake without weakening canonical Point
        # validation for any other shape.
        while (
            isinstance(coordinates, list)
            and len(coordinates) == 1
            and isinstance(coordinates[0], list)
            and not _looks_like_position(coordinates)
        ):
            coordinates = coordinates[0]
        normalized["coordinates"] = coordinates
    if (
        normalized.get("geometry_type") == "Polygon"
        and isinstance(coordinates, list)
        and coordinates
        and _looks_like_position(coordinates[0])
    ):
        normalized["coordinates"] = [coordinates]
    return normalized


def _looks_like_position(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and not isinstance(value[0], (list, dict))
        and not isinstance(value[1], (list, dict))
    )


def validate_mission_config(config: dict[str, Any]) -> None:
    required = ("mission_id", "behavior", "vehicles", "objective")
    for key in required:
        if key not in config:
            raise MissionValidationError(f"Mission config is missing required field '{key}'")

    if int(config["behavior"]) not in (0, 1, 2):
        raise MissionValidationError("Mission behavior must be 0, 1, or 2")

    vehicles = config["vehicles"]
    if not isinstance(vehicles, list) or not vehicles:
        raise MissionValidationError("Mission vehicles must be a non-empty list")
    if any(not isinstance(vehicle_id, str) or not vehicle_id for vehicle_id in vehicles):
        raise MissionValidationError("Mission vehicles must contain non-empty string ids")

    objective = config["objective"]
    if not isinstance(objective, dict):
        raise MissionValidationError("Mission objective must be an object")

    geometries = objective.get("geometries")
    if not isinstance(geometries, list) or not geometries:
        raise MissionValidationError("Mission objective.geometries must be a non-empty list")

    for index, geometry_ref in enumerate(geometries):
        _validate_geometry_ref(geometry_ref, f"objective.geometries[{index}]")

    for key in ("vehicle_orientation_origin", "line_of_sight"):
        if key in objective:
            _validate_geometry_ref(objective[key], f"objective.{key}")

    transit = config.get("transit")
    if isinstance(transit, dict):
        if "geofence" in transit:
            _validate_geometry_ref(transit["geofence"], "transit.geofence")
        if "roads" in transit:
            roads = transit["roads"]
            if not isinstance(roads, list):
                raise MissionValidationError("transit.roads must be an array")
            for index, road in enumerate(roads):
                _validate_geometry_ref(road, f"transit.roads[{index}]")

    start = config.get("start")
    if isinstance(start, dict) and "geometry" in start:
        _validate_geometry_ref(start["geometry"], "start.geometry")

    for field_name, label in (
        ("maximum_coverage_distances", "vehicle separation distances"),
        ("coverage_swath_widths", "coverage swath widths"),
    ):
        values = objective.get(field_name)
        if values is None:
            continue
        if not isinstance(values, list) or not values:
            raise MissionValidationError(
                f"objective.{field_name} must be a non-empty list"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            or value <= 0
            for value in values
        ):
            raise MissionValidationError(
                f"objective.{field_name} must contain positive finite {label} in metres"
            )
        if len(values) not in (1, len(vehicles)):
            raise MissionValidationError(
                f"objective.{field_name} must contain one shared value or one value per mission vehicle"
            )

    _validate_objective_semantics(objective, vehicles)
    _validate_transit_semantics(transit)
    _validate_time_window(start.get("start_time") if isinstance(start, dict) else None, "start.start_time")
    _validate_time_window(objective.get("arrival_time"), "objective.arrival_time")
    if config.get("mission_end_time") is not None:
        _parse_iso8601(config["mission_end_time"], "mission_end_time")


def _validate_objective_semantics(objective: dict[str, Any], vehicles: list[str]) -> None:
    minimum = objective.get("minimum_distance")
    maximum = objective.get("maximum_distance")
    for field_name, value in (("minimum_distance", minimum), ("maximum_distance", maximum)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
            raise MissionValidationError(f"objective.{field_name} must be a finite number")
    if maximum is not None and maximum < 0:
        raise MissionValidationError("objective.maximum_distance must be non-negative")
    if minimum is not None and maximum is not None and max(0.0, minimum) > maximum:
        raise MissionValidationError(
            "objective.minimum_distance cannot exceed objective.maximum_distance"
        )

    orientations = objective.get("vehicle_orientation")
    if orientations is not None:
        if not isinstance(orientations, list) or not orientations:
            raise MissionValidationError("objective.vehicle_orientation must be a non-empty array")
        if len(orientations) not in (1, len(vehicles)):
            raise MissionValidationError(
                "objective.vehicle_orientation must contain one shared heading or one heading per vehicle"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            for value in orientations
        ):
            raise MissionValidationError("objective.vehicle_orientation must contain finite headings")

    formation_distance = objective.get("vehicle_formation_distance")
    if formation_distance is not None and (
        isinstance(formation_distance, bool)
        or not isinstance(formation_distance, int | float)
        or not math.isfinite(formation_distance)
        or formation_distance <= 0
    ):
        raise MissionValidationError("objective.vehicle_formation_distance must be positive")


def _validate_transit_semantics(transit: Any) -> None:
    if not isinstance(transit, dict):
        return
    optimization = transit.get("optimization")
    if isinstance(optimization, dict):
        for key in ("visibility", "energy", "road_usage"):
            value = optimization.get(key)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise MissionValidationError(
                    f"transit.optimization.{key} must be between 0 and 1"
                )
    constraints = transit.get("desired_vehicle_constraints")
    if isinstance(constraints, dict):
        for key, value in constraints.items():
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                or value < 0
            ):
                raise MissionValidationError(
                    f"transit.desired_vehicle_constraints.{key} must be a non-negative finite number"
                )


def _validate_time_window(value: Any, path: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise MissionValidationError(f"{path} must be an object")
    parsed = {
        key: _parse_iso8601(value.get(key), f"{path}.{key}")
        for key in ("earliest", "target", "latest")
    }
    if not parsed["earliest"] <= parsed["target"] <= parsed["latest"]:
        raise MissionValidationError(
            f"{path} must satisfy earliest <= target <= latest"
        )


def _parse_iso8601(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise MissionValidationError(f"{path} must be an ISO8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissionValidationError(f"{path} must be an ISO8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise MissionValidationError(f"{path} must include a timezone")
    return parsed


def _validate_geometry_ref(geometry_ref: Any, path: str) -> None:
    """Validate one canonical geometry ref without resolving feature IDs."""

    if not isinstance(geometry_ref, dict):
        raise MissionValidationError(f"{path} must be an object")
    has_feature = bool(geometry_ref.get("feature_id"))
    has_geometry = "geometry" in geometry_ref
    if has_feature and has_geometry:
        raise MissionValidationError(
            f"{path} must contain exactly one of feature_id or geometry"
        )
    if has_feature:
        return
    if not has_geometry:
        raise MissionValidationError(
            f"{path} must contain exactly one of feature_id or geometry"
        )
    geometry = geometry_ref.get("geometry")
    if not isinstance(geometry, dict):
        raise MissionValidationError(f"{path}.geometry must be an object")
    _validate_inline_geometry(geometry, f"{path}.geometry")


def _validate_inline_geometry(geometry: dict[str, Any], path: str) -> None:
    geometry_type = geometry.get("geometry_type")
    if geometry_type not in _SUPPORTED_INLINE_GEOMETRY_TYPES:
        supported = ", ".join(sorted(_SUPPORTED_INLINE_GEOMETRY_TYPES))
        raise MissionValidationError(
            f"{path}.geometry_type must be one of: {supported}"
        )

    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        _validate_lon_lat(coordinates, f"{path}.coordinates")
        return

    if not isinstance(coordinates, list):
        raise MissionValidationError(f"{path}.coordinates must be an array")

    if geometry_type in {"MultiPoint", "LineString"}:
        minimum_positions = 1 if geometry_type == "MultiPoint" else 2
        if len(coordinates) < minimum_positions:
            count_word = "two" if minimum_positions == 2 else "one"
            raise MissionValidationError(
                f"{path}.coordinates must contain at least {count_word} positions"
            )
        for index, position in enumerate(coordinates):
            _validate_lon_lat(position, f"{path}.coordinates[{index}]")
        return

    if not coordinates:
        raise MissionValidationError(
            f"{path}.coordinates must contain at least one linear ring"
        )
    if len(coordinates) > 1:
        raise MissionValidationError(
            f"{path}.coordinates cannot contain interior rings because the backend "
            "mission contract cannot represent them"
        )
    for ring_index, ring in enumerate(coordinates):
        ring_path = f"{path}.coordinates[{ring_index}]"
        if not isinstance(ring, list) or len(ring) < 4:
            raise MissionValidationError(
                f"{ring_path} must contain at least four positions"
            )
        for position_index, position in enumerate(ring):
            _validate_lon_lat(position, f"{ring_path}[{position_index}]")
        if ring[0] != ring[-1]:
            raise MissionValidationError(
                f"{ring_path} must be closed (first and last positions must match)"
            )
        if len({tuple(position) for position in ring[:-1]}) < 3:
            raise MissionValidationError(
                f"{ring_path} must contain at least three distinct positions"
            )


def _validate_lon_lat(value: Any, path: str) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise MissionValidationError(f"{path} must be exactly [longitude, latitude]")
    longitude, latitude = value
    if any(
        isinstance(coordinate, bool)
        or not isinstance(coordinate, int | float)
        or not math.isfinite(coordinate)
        for coordinate in value
    ):
        raise MissionValidationError(f"{path} must contain finite numeric coordinates")
    if not -180 <= longitude <= 180:
        raise MissionValidationError(f"{path}[0] longitude must be between -180 and 180")
    if not -90 <= latitude <= 90:
        raise MissionValidationError(f"{path}[1] latitude must be between -90 and 90")


def validate_mission_schema(
    config: Any,
    *,
    repo_root: Path | None = None,
) -> None:
    """Execute the canonical draft-2020-12 schema and report JSON paths."""

    validator = _mission_schema_validator(_mission_schema_path(repo_root))
    errors = sorted(validator.iter_errors(config), key=_schema_error_sort_key)
    if not errors:
        return
    details = [_format_schema_error(error) for error in errors[:8]]
    if len(errors) > len(details):
        details.append(f"... and {len(errors) - len(details)} more schema error(s)")
    raise MissionValidationError(
        "Mission config failed JSON Schema validation: " + "; ".join(details)
    )


def load_and_validate_mission(
    config: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    normalized = normalize_mission_config(config)
    validate_mission_schema(normalized, repo_root=repo_root)
    validate_mission_config(normalized)
    return normalized


def _mission_schema_path(repo_root: Path | None) -> Path:
    candidates = []
    if repo_root is not None:
        candidates.append(Path(repo_root) / "schemas" / "mission_config.schema.json")
    configured_root = os.environ.get("C2_IMUGS2_REPO_ROOT")
    if configured_root:
        candidates.append(Path(configured_root) / "schemas" / "mission_config.schema.json")
    # The editable install and API image both retain the repository schema at
    # this path. It is also the safe fallback for tests whose runtime repo_root
    # is a temporary data directory rather than the source checkout.
    candidates.append(Path(__file__).resolve().parents[3] / "schemas" / "mission_config.schema.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise RuntimeError(f"canonical mission schema was not found (searched: {searched})")


@lru_cache(maxsize=4)
def _mission_schema_validator(schema_path: Path) -> Draft202012Validator:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not load canonical mission schema {schema_path}: {exc}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_error_sort_key(error: Any) -> tuple[str, str]:
    path = ".".join(str(part) for part in error.absolute_path)
    return path, str(error.message)


def _format_schema_error(error: Any) -> str:
    path = "$"
    for part in error.absolute_path:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return f"{path}: {error.message}"
