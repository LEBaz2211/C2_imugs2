from __future__ import annotations

from copy import deepcopy
from typing import Any


class MissionValidationError(ValueError):
    pass


def normalize_mission_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy mission spellings/shapes into the replacement canonical form."""
    normalized = deepcopy(config)

    objective = normalized.setdefault("objective", {})
    if "geometries" not in objective and "geometry" in objective:
        objective["geometries"] = [_normalize_geometry_ref(objective.pop("geometry"))]
    if "geometries" not in objective and "feature_id" in objective:
        objective["geometries"] = [{"feature_id": objective.pop("feature_id")}]
    if isinstance(objective.get("geometries"), list):
        objective["geometries"] = [_normalize_geometry_ref(geometry_ref) for geometry_ref in objective["geometries"]]
    if "maximize_area_coverage" in objective and "maximize_coverage" not in objective:
        objective["maximize_coverage"] = objective.pop("maximize_area_coverage")
    if isinstance(objective.get("vehicle_orientation"), int | float):
        objective["vehicle_orientation"] = [objective["vehicle_orientation"]]

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
    if "geometry_type" in value or "coordinates" in value:
        return {"geometry": value}
    return value


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
        if not isinstance(geometry_ref, dict):
            raise MissionValidationError(f"objective.geometries[{index}] must be an object")
        has_feature = bool(geometry_ref.get("feature_id"))
        has_geometry = isinstance(geometry_ref.get("geometry"), dict)
        if has_feature == has_geometry:
            raise MissionValidationError(
                f"objective.geometries[{index}] must contain exactly one of feature_id or geometry"
            )


def load_and_validate_mission(config: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_mission_config(config)
    validate_mission_config(normalized)
    return normalized
