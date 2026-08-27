"""Adapter for legacy map assets and mutable operator-authored features."""

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
    backend_map_dir = repo_root / "backend" / "config" / "data" / "map" / map_name
    legacy_map_dir = repo_root / "legacy_ros" / "config" / "data" / "map" / map_name
    map_dir = backend_map_dir if backend_map_dir.is_dir() else legacy_map_dir
    if not map_dir.is_dir():
        raise FileNotFoundError(f"Unknown backend map '{map_name}' at {backend_map_dir}")

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
    """Load a previously frozen overlay without performing implicit network I/O.

    New OSM data is fetched only by the explicit Scenario Lab polygon query and
    becomes authoritative only after scenario activation stores it in MapDB.
    """
    cache_path = repo_root / "data" / "runtime" / f"osm_roads_{map_name}.geojson"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("features"):
                return cached
        except json.JSONDecodeError:
            pass

    return _local_road_overlay(load_legacy_geojson_map(repo_root, map_name))


def query_osm_roads_for_bbox(
    repo_root: Path,
    map_name: str,
    bbox: tuple[float, float, float, float],
    max_features: int = 160,
) -> dict[str, Any]:
    """Fetch OSM highway LineStrings for a bbox without persisting runtime map assets."""
    west, south, east, north = _validate_bbox(bbox)
    overpass = _query_overpass_roads((west, south, east, north))
    if overpass is None:
        raise ValueError("OpenStreetMap Overpass query failed")

    collection = _overpass_roads_to_feature_collection(overpass, feature_type="scenario_osm_road")
    features = collection.get("features", [])[: max(1, max_features)]
    for feature in features:
        properties = dict(feature.get("properties") or {})
        properties.update(
            {
                "feature_type": "scenario_osm_road",
                "source": "openstreetmap-overpass",
                "source_tool": "scenario_lab_osm_section",
            }
        )
        feature["properties"] = properties
    geojson = {"type": "FeatureCollection", "features": features}
    return {
        "feature_count": len(features),
        "bbox": [west, south, east, north],
        "features": features,
        "geojson": geojson,
        "map": map_name,
        "persisted": False,
    }


def query_osm_roads_for_polygon(
    repo_root: Path,
    map_name: str,
    polygon: list[list[float]],
    max_features: int = 50000,
) -> dict[str, Any]:
    """Fetch OSM highway ways for a polygon and return only the parts inside it."""
    ring = _validate_polygon_ring(polygon)
    west, south, east, north = _validate_bbox(_bbox_from_points(ring))
    overpass = _query_overpass_roads(_expand_bbox((west, south, east, north), margin=0.00008))
    if overpass is None:
        raise ValueError("OpenStreetMap Overpass query failed")

    collection = _overpass_roads_to_feature_collection(overpass, feature_type="scenario_osm_road")
    features: list[dict[str, Any]] = []
    source_way_count = 0
    for feature in collection.get("features", []):
        geometry = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else {}
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list):
            continue
        clipped_lines = _clip_linestring_to_polygon(coordinates, ring)
        if not clipped_lines:
            continue
        source_way_count += 1
        for index, line in enumerate(clipped_lines):
            if len(features) >= max(1, max_features):
                break
            clipped = json.loads(json.dumps(feature))
            feature_id = str((clipped.get("properties") or {}).get("feature_id") or clipped.get("id"))
            if len(clipped_lines) > 1:
                feature_id = f"{feature_id}-clip-{index + 1}"
            properties = dict(clipped.get("properties") or {})
            properties.update(
                {
                    "feature_id": feature_id,
                    "feature_type": "scenario_osm_road",
                    "source": "openstreetmap-overpass",
                    "source_tool": "scenario_lab_osm_polygon",
                    "clip": "polygon",
                }
            )
            clipped["id"] = feature_id
            clipped["properties"] = properties
            clipped["geometry"] = {"type": "LineString", "coordinates": line}
            features.append(clipped)
        if len(features) >= max(1, max_features):
            break

    geojson = {"type": "FeatureCollection", "features": features}
    return {
        "feature_count": len(features),
        "source_way_count": source_way_count,
        "bbox": [west, south, east, north],
        "polygon": ring,
        "features": features,
        "geojson": geojson,
        "map": map_name,
        "persisted": False,
        "clipped_to_polygon": True,
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


def _validate_polygon_ring(polygon: list[list[float]]) -> list[list[float]]:
    if not isinstance(polygon, list) or len(polygon) < 3:
        raise ValueError("polygon must contain at least three [lon, lat] points")
    ring = []
    for point in polygon:
        if not isinstance(point, list | tuple) or len(point) < 2:
            raise ValueError("polygon points must be [lon, lat]")
        lon = float(point[0])
        lat = float(point[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("polygon coordinates are outside valid longitude/latitude ranges")
        ring.append([lon, lat])
    if ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    if len(ring) < 4:
        raise ValueError("polygon must contain at least three distinct points")
    return ring


def _bbox_from_points(points: list[list[float]]) -> tuple[float, float, float, float]:
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return min(lons), min(lats), max(lons), max(lats)


def _clip_linestring_to_polygon(coordinates: list[Any], polygon: list[list[float]]) -> list[list[list[float]]]:
    points = [point for point in (_lonlat_or_none(value) for value in coordinates) if point is not None]
    if len(points) < 2:
        return []
    if all(_point_in_or_on_polygon(point, polygon) for point in points):
        return [_dedupe_points(points)]

    clipped: list[list[list[float]]] = []
    current: list[list[float]] = []
    for start, end in zip(points, points[1:]):
        cuts = _segment_polygon_cut_ratios(start, end, polygon)
        for first_ratio, second_ratio in zip(cuts, cuts[1:]):
            if second_ratio - first_ratio <= 1e-10:
                continue
            midpoint = _interpolate_point(start, end, (first_ratio + second_ratio) / 2)
            if _point_in_or_on_polygon(midpoint, polygon):
                first = _interpolate_point(start, end, first_ratio)
                second = _interpolate_point(start, end, second_ratio)
                if not current or current[-1] != first:
                    current.append(first)
                if current[-1] != second:
                    current.append(second)
            elif current:
                if len(current) >= 2:
                    clipped.append(_dedupe_points(current))
                current = []
    if len(current) >= 2:
        clipped.append(_dedupe_points(current))
    return [line for line in clipped if len(line) >= 2]


def _segment_polygon_cut_ratios(start: list[float], end: list[float], polygon: list[list[float]]) -> list[float]:
    ratios = [0.0, 1.0]
    for first, second in zip(polygon, polygon[1:]):
        ratios.extend(_segment_intersection_ratios(start, end, first, second))
    unique_ratios: list[float] = []
    for ratio in sorted(max(0.0, min(1.0, value)) for value in ratios):
        if not unique_ratios or abs(unique_ratios[-1] - ratio) > 1e-9:
            unique_ratios.append(ratio)
    return unique_ratios


def _segment_intersection_ratios(start: list[float], end: list[float], first: list[float], second: list[float]) -> list[float]:
    x1, y1 = start
    x2, y2 = end
    x3, y3 = first
    x4, y4 = second
    rx = x2 - x1
    ry = y2 - y1
    sx = x4 - x3
    sy = y4 - y3
    denominator = rx * sy - ry * sx
    qpx = x3 - x1
    qpy = y3 - y1
    if abs(denominator) <= 1e-12:
        if abs(qpx * ry - qpy * rx) > 1e-12:
            return []
        ratios = []
        for point in (first, second):
            ratio = _point_ratio_on_segment(point, start, end)
            if ratio is not None:
                ratios.append(ratio)
        if _point_on_segment(start, first, second):
            ratios.append(0.0)
        if _point_on_segment(end, first, second):
            ratios.append(1.0)
        return ratios
    ratio = (qpx * sy - qpy * sx) / denominator
    other_ratio = (qpx * ry - qpy * rx) / denominator
    if -1e-10 <= ratio <= 1 + 1e-10 and -1e-10 <= other_ratio <= 1 + 1e-10:
        return [ratio]
    return []


def _point_ratio_on_segment(point: list[float], start: list[float], end: list[float]) -> float | None:
    if not _point_on_segment(point, start, end):
        return None
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if abs(dx) >= abs(dy) and abs(dx) > 1e-12:
        return (point[0] - start[0]) / dx
    if abs(dy) > 1e-12:
        return (point[1] - start[1]) / dy
    return 0.0


def _lonlat_or_none(value: Any) -> list[float] | None:
    if isinstance(value, list | tuple) and len(value) >= 2 and isinstance(value[0], int | float) and isinstance(value[1], int | float):
        return [round(float(value[0]), 7), round(float(value[1]), 7)]
    return None


def _interpolate_point(start: list[float], end: list[float], ratio: float) -> list[float]:
    return [
        round(start[0] + (end[0] - start[0]) * ratio, 7),
        round(start[1] + (end[1] - start[1]) * ratio, 7),
    ]


def _dedupe_points(points: list[list[float]]) -> list[list[float]]:
    deduped: list[list[float]] = []
    for point in points:
        if not deduped or deduped[-1] != point:
            deduped.append(point)
    return deduped


def _point_in_or_on_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    if _point_on_polygon_boundary(point, polygon):
        return True
    lon, lat = point
    inside = False
    for first, second in zip(polygon, polygon[1:]):
        lon1, lat1 = first
        lon2, lat2 = second
        crosses = (lat1 > lat) != (lat2 > lat)
        if crosses:
            intersect_lon = (lon2 - lon1) * (lat - lat1) / ((lat2 - lat1) or 1e-12) + lon1
            if lon < intersect_lon:
                inside = not inside
    return inside


def _point_on_polygon_boundary(point: list[float], polygon: list[list[float]]) -> bool:
    return any(_point_on_segment(point, first, second) for first, second in zip(polygon, polygon[1:]))


def _point_on_segment(point: list[float], first: list[float], second: list[float]) -> bool:
    lon, lat = point
    lon1, lat1 = first
    lon2, lat2 = second
    cross = (lat - lat1) * (lon2 - lon1) - (lon - lon1) * (lat2 - lat1)
    if abs(cross) > 1e-10:
        return False
    dot = (lon - lon1) * (lon2 - lon1) + (lat - lat1) * (lat2 - lat1)
    if dot < -1e-10:
        return False
    squared_len = (lon2 - lon1) ** 2 + (lat2 - lat1) ** 2
    return dot <= squared_len + 1e-10


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
