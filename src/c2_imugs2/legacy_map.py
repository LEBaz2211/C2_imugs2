from __future__ import annotations

import json
import statistics
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request


FEATURE_TYPE_BY_FOLDER = {
    "free_linestrings": "road",
    "free_polygons": "workspace",
    "risk_polygons": "risk",
    "virtual_geofences": "geofence",
}

ALLOWED_USER_FEATURE_GEOMETRIES = {
    "objective": {"Point"},
    "road": {"LineString"},
    "geofence": {"Polygon"},
    "workspace": {"Polygon"},
    "risk": {"Polygon"},
}


def load_legacy_geojson_map(repo_root: Path, map_name: str = "rma") -> dict[str, Any]:
    map_dir = repo_root / "legacy_ros" / "config" / "data" / "map" / map_name
    if not map_dir.is_dir():
        raise FileNotFoundError(f"Unknown legacy map '{map_name}' at {map_dir}")

    features: list[dict[str, Any]] = []
    for path in sorted(map_dir.rglob("*.geojson")):
        folder_type = FEATURE_TYPE_BY_FOLDER.get(path.parent.name, "custom")
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_features = data.get("features", [data]) if data.get("type") == "FeatureCollection" else [data]
        for index, feature in enumerate(raw_features):
            if feature.get("type") != "Feature" or not isinstance(feature.get("geometry"), dict):
                continue
            normalized = dict(feature)
            properties = dict(normalized.get("properties") or {})
            feature_type = str(properties.get("feature_type") or folder_type)
            feature_id = str(properties.get("feature_id") or normalized.get("id") or uuid.uuid5(uuid.NAMESPACE_URL, f"{path}:{index}"))
            properties.update(
                {
                    "feature_id": feature_id,
                    "feature_type": feature_type,
                    "name": properties.get("name") or path.stem,
                    "source_file": str(path.relative_to(repo_root)),
                }
            )
            normalized["id"] = feature_id
            normalized["properties"] = properties
            features.append(normalized)

    features.extend(load_user_geojson_map(repo_root, map_name).get("features", []))
    return {"type": "FeatureCollection", "features": features}


def load_user_geojson_map(repo_root: Path, map_name: str = "rma") -> dict[str, Any]:
    path = _user_features_path(repo_root, map_name)
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        return {"type": "FeatureCollection", "features": []}
    return data


def save_user_geojson_feature(repo_root: Path, map_name: str, feature: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_user_geojson_feature(feature)
    collection = load_user_geojson_map(repo_root, map_name)
    collection["features"].append(normalized)
    path = _user_features_path(repo_root, map_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection, indent=2), encoding="utf-8")
    return normalized


def delete_user_geojson_feature(repo_root: Path, map_name: str, feature_id: str) -> bool:
    collection = load_user_geojson_map(repo_root, map_name)
    features = collection.get("features", [])
    kept = [
        feature
        for feature in features
        if str((feature.get("properties") or {}).get("feature_id") or feature.get("id")) != feature_id
    ]
    if len(kept) == len(features):
        return False
    collection["features"] = kept
    path = _user_features_path(repo_root, map_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection, indent=2), encoding="utf-8")
    return True


def update_user_geojson_feature(repo_root: Path, map_name: str, feature_id: str, feature: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_user_geojson_feature(feature)
    normalized["id"] = feature_id
    normalized["properties"]["feature_id"] = feature_id

    collection = load_user_geojson_map(repo_root, map_name)
    features = collection.get("features", [])
    for index, existing in enumerate(features):
        existing_id = str((existing.get("properties") or {}).get("feature_id") or existing.get("id"))
        if existing_id == feature_id:
            features[index] = normalized
            path = _user_features_path(repo_root, map_name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(collection, indent=2), encoding="utf-8")
            return normalized
    return None


def normalize_user_geojson_feature(feature: dict[str, Any]) -> dict[str, Any]:
    if feature.get("type") != "Feature" or not isinstance(feature.get("geometry"), dict):
        raise ValueError("feature must be a GeoJSON Feature with a geometry")
    geometry = feature["geometry"]
    if geometry.get("type") not in {"Point", "LineString", "Polygon"}:
        raise ValueError("feature geometry type is not supported")

    properties = dict(feature.get("properties") or {})
    feature_type = str(properties.get("feature_type") or "custom")
    if feature_type not in ALLOWED_USER_FEATURE_GEOMETRIES:
        raise ValueError(f"feature_type must be one of {sorted(ALLOWED_USER_FEATURE_GEOMETRIES)}")
    geometry_type = str(geometry.get("type"))
    if geometry_type not in ALLOWED_USER_FEATURE_GEOMETRIES[feature_type]:
        allowed = ", ".join(sorted(ALLOWED_USER_FEATURE_GEOMETRIES[feature_type]))
        raise ValueError(f"{feature_type} features must use geometry type: {allowed}")

    feature_id = str(properties.get("feature_id") or feature.get("id") or uuid.uuid4())
    name = str(properties.get("name") or f"{feature_type}_{feature_id[:8]}")
    properties.update(
        {
            "feature_id": feature_id,
            "feature_type": feature_type,
            "name": name,
            "source_file": "data/runtime/user_features.geojson",
            "source": "user",
        }
    )
    return {"type": "Feature", "id": feature_id, "properties": properties, "geometry": geometry}


def load_osm_roads_overlay(repo_root: Path, map_name: str = "rma") -> dict[str, Any]:
    cache_path = repo_root / "data" / "runtime" / f"osm_roads_{map_name}.geojson"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("features"):
                return cached
        except json.JSONDecodeError:
            pass

    collection = load_legacy_geojson_map(repo_root, map_name)
    bbox = _feature_collection_bbox(collection)
    if bbox is None:
        return {"type": "FeatureCollection", "features": []}

    west, south, east, north = _expand_bbox(bbox, margin=0.0012)
    overpass = _query_overpass_roads((west, south, east, north))
    if overpass is None:
        return _local_road_overlay(collection)
    overlay = _overpass_roads_to_feature_collection(overpass, feature_type="osm_road")
    if not overlay.get("features"):
        overlay = _local_road_overlay(collection)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(overlay, indent=2), encoding="utf-8")
    except OSError:
        pass
    return overlay


def import_osm_roads_as_user_features(
    repo_root: Path,
    map_name: str,
    bbox: tuple[float, float, float, float],
    max_features: int = 80,
) -> dict[str, Any]:
    """Fetch OSM highway LineStrings for a bbox and persist them as runtime road features."""
    west, south, east, north = _validate_bbox(bbox)
    overpass = _query_overpass_roads((west, south, east, north))
    if overpass is None:
        raise ValueError("OpenStreetMap Overpass query failed")

    collection = _overpass_roads_to_feature_collection(overpass, feature_type="road")
    imported = []
    seen_ids = {
        str((feature.get("properties") or {}).get("feature_id") or feature.get("id"))
        for feature in load_user_geojson_map(repo_root, map_name).get("features", [])
    }
    for feature in collection.get("features", [])[: max(1, max_features)]:
        properties = dict(feature.get("properties") or {})
        feature_id = str(properties.get("feature_id") or feature.get("id"))
        if feature_id in seen_ids:
            continue
        properties.update(
            {
                "feature_id": feature_id,
                "feature_type": "road",
                "import_source": "openstreetmap-overpass",
                "source_tool": "scenario_lab_osm_import",
            }
        )
        feature["properties"] = properties
        imported.append(save_user_geojson_feature(repo_root, map_name, feature))
        seen_ids.add(feature_id)

    full_collection = load_legacy_geojson_map(repo_root, map_name)
    return {
        "imported_count": len(imported),
        "skipped_existing": len(collection.get("features", [])[: max(1, max_features)]) - len(imported),
        "bbox": [west, south, east, north],
        "features": imported,
        "geojson": full_collection,
        "map_features": feature_collection_to_map_features(full_collection),
    }


def feature_collection_to_map_features(collection: dict[str, Any]) -> list[dict[str, Any]]:
    map_features = []
    for feature in collection.get("features", []):
        properties = dict(feature.get("properties") or {})
        feature_id = str(properties.get("feature_id") or feature.get("id"))
        feature_type = str(properties.get("feature_type") or "custom")
        map_features.append(
            {
                "feature_id": feature_id,
                "name": str(properties.get("name") or feature_id),
                "feature_type": feature_type,
                "geometry": feature["geometry"],
                "properties": properties,
            }
        )
    return map_features


def _query_overpass_roads(bbox: tuple[float, float, float, float]) -> dict[str, Any] | None:
    west, south, east, north = bbox
    query = f"""
    [out:json][timeout:10];
    (
      way["highway"]({south},{west},{north},{east});
    );
    out geom tags;
    """
    payload = parse.urlencode({"data": query}).encode("utf-8")
    for url in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
        req = request.Request(url, data=payload, method="POST", headers={"User-Agent": "c2-imugs2-ui-adapter/0.1"})
        try:
            with request.urlopen(req, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, error.HTTPError, json.JSONDecodeError):
            continue
    return None


def _overpass_roads_to_feature_collection(overpass: dict[str, Any], feature_type: str) -> dict[str, Any]:
    features = []
    for element in overpass.get("elements", []):
        geometry = element.get("geometry")
        if element.get("type") != "way" or not isinstance(geometry, list) or len(geometry) < 2:
            continue
        tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
        coordinates = [[float(point["lon"]), float(point["lat"])] for point in geometry if "lon" in point and "lat" in point]
        if len(coordinates) < 2:
            continue
        feature_id = f"osm-way-{element.get('id')}"
        features.append(
            {
                "type": "Feature",
                "id": feature_id,
                "properties": {
                    "feature_id": feature_id,
                    "feature_type": feature_type,
                    "name": tags.get("name") or tags.get("highway") or feature_id,
                    "highway": tags.get("highway"),
                    "source": "openstreetmap-overpass",
                },
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _validate_bbox(bbox: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    west, south, east, north = [float(value) for value in bbox]
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
        raise ValueError("bbox coordinates are outside valid longitude/latitude ranges")
    if west >= east or south >= north:
        raise ValueError("bbox must be [west, south, east, north]")
    if (east - west) * (north - south) > 0.01:
        raise ValueError("bbox is too large for an interactive OSM import")
    return west, south, east, north


def _user_features_path(repo_root: Path, map_name: str) -> Path:
    return repo_root / "data" / "runtime" / f"user_features_{map_name}.geojson"


def _feature_collection_bbox(collection: dict[str, Any]) -> tuple[float, float, float, float] | None:
    points: list[list[float]] = []
    for feature in collection.get("features", []):
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if isinstance(geometry, dict):
            points.extend(_flatten_points(geometry.get("coordinates")))
    if not points:
        return None
    if len(points) >= 4:
        median_lon = statistics.median(point[0] for point in points)
        median_lat = statistics.median(point[1] for point in points)
        clustered = [point for point in points if abs(point[0] - median_lon) <= 0.02 and abs(point[1] - median_lat) <= 0.02]
        if len(clustered) >= 2:
            points = clustered
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return min(lons), min(lats), max(lons), max(lats)


def _flatten_points(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    if len(value) >= 2 and isinstance(value[0], int | float) and isinstance(value[1], int | float):
        return [[float(value[0]), float(value[1])]]
    points: list[list[float]] = []
    for item in value:
        points.extend(_flatten_points(item))
    return points


def _expand_bbox(bbox: tuple[float, float, float, float], margin: float) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    return west - margin, south - margin, east + margin, north + margin


def _local_road_overlay(collection: dict[str, Any]) -> dict[str, Any]:
    features = []
    for feature in collection.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if properties.get("feature_type") != "road" or not isinstance(geometry, dict):
            continue
        overlay_feature = dict(feature)
        overlay_properties = dict(properties)
        overlay_properties["feature_type"] = "osm_road"
        overlay_properties["source"] = overlay_properties.get("source") or "legacy-road-fallback"
        overlay_feature["properties"] = overlay_properties
        features.append(overlay_feature)
    return {"type": "FeatureCollection", "features": features}
