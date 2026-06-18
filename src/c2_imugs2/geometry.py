from __future__ import annotations

from math import hypot
from typing import Any, Iterable


Point = tuple[float, float]


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def representative_point(geometry: dict[str, Any]) -> Point:
    geometry_type = geometry.get("type") or geometry.get("geometry_type")
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        raise ValueError(f"Geometry has no coordinates: {geometry}")

    if geometry_type == "Point":
        return _point(coordinates)
    if geometry_type == "MultiPoint":
        return centroid(_points(coordinates))
    if geometry_type == "LineString":
        return centroid(_points(coordinates))
    if geometry_type == "Polygon":
        ring = coordinates[0] if coordinates and isinstance(coordinates[0], list) else coordinates
        return centroid(_points(ring))
    if geometry_type == "MultiPolygon":
        first_polygon = coordinates[0]
        ring = first_polygon[0]
        return centroid(_points(ring))

    # Best effort for fixtures with valid coordinates but weak metadata.
    flattened = list(_flatten_points(coordinates))
    if flattened:
        return centroid(flattened)
    raise ValueError(f"Unsupported geometry type: {geometry_type}")


def geometry_points(geometry: dict[str, Any]) -> list[Point]:
    geometry_type = geometry.get("type") or geometry.get("geometry_type")
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        raise ValueError(f"Geometry has no coordinates: {geometry}")
    if geometry_type == "Point":
        return [_point(coordinates)]
    if geometry_type in ("MultiPoint", "LineString"):
        return _points(coordinates)
    if geometry_type == "Polygon":
        ring = coordinates[0] if coordinates and isinstance(coordinates[0], list) else coordinates
        return _points(ring)
    return list(_flatten_points(coordinates))


def centroid(points: Iterable[Point]) -> Point:
    point_list = list(points)
    if not point_list:
        raise ValueError("Cannot compute centroid of an empty point list")
    return (
        sum(point[0] for point in point_list) / len(point_list),
        sum(point[1] for point in point_list) / len(point_list),
    )


def _point(value: Any) -> Point:
    if not isinstance(value, list | tuple) or len(value) < 2:
        raise ValueError(f"Invalid point coordinates: {value}")
    return float(value[0]), float(value[1])


def _points(values: Any) -> list[Point]:
    if not isinstance(values, list):
        raise ValueError(f"Invalid point list: {values}")
    return [_point(value) for value in values]


def _flatten_points(value: Any) -> Iterable[Point]:
    if isinstance(value, list | tuple):
        if len(value) >= 2 and all(isinstance(item, int | float) for item in value[:2]):
            yield _point(value)
        else:
            for item in value:
                yield from _flatten_points(item)

