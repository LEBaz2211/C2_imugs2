import heapq
import math

from pyproj import CRS, Transformer
from shapely.affinity import rotate
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.ops import transform, unary_union
from scipy.spatial import distance_matrix
from gurobipy import Model, GRB, quicksum


DEFAULT_RISK_CLEARANCE_M = 0.5
DEFAULT_BOUNDARY_INSET_M = 0.5


def lawnmower_coverage_path(
    coordinates,
    swath_width_m,
    risk_polygons=None,
    risk_clearance_m=DEFAULT_RISK_CLEARANCE_M,
):
    """Return a continuous boustrophedon path covering a WGS84 polygon.

    The vehicle centre stays inside the polygon. Parallel passes are oriented
    along the polygon's longest minimum-rectangle axis and spaced no farther
    apart than ``swath_width_m``. Concave boundaries and holes are handled by
    joining disjoint pass fragments through a visibility path that also stays
    inside the polygon.
    """
    width = float(swath_width_m)
    if not math.isfinite(width) or width <= 0:
        raise ValueError("Coverage swath width must be a positive finite number of metres")

    clearance = float(risk_clearance_m)
    if not math.isfinite(clearance) or clearance < 0:
        raise ValueError("Risk clearance must be a non-negative finite number of metres")

    polygon = _polygon_from_coordinates(coordinates)
    projected, to_wgs84, to_local = _project_polygon_to_local_utm(polygon)
    sweep_angle = _longest_rectangle_edge_angle(projected)
    safe_polygon, _excluded_risk_count = _subtract_risk_polygons(
        projected,
        risk_polygons or [],
        to_local,
        clearance,
    )
    origin = (projected.centroid.x, projected.centroid.y)
    aligned = rotate(safe_polygon, -sweep_angle, origin=origin)

    min_x, min_y, max_x, max_y = aligned.bounds
    cross_track_extent = max_y - min_y
    boundary_inset = min(DEFAULT_BOUNDARY_INSET_M, cross_track_extent / 2.0)
    usable_extent = max(0.0, cross_track_extent - 2.0 * boundary_inset)
    if usable_extent == 0:
        lane_y_values = [aligned.centroid.y]
    else:
        lane_count = max(2, math.ceil(usable_extent / width) + 1)
        lane_spacing = usable_extent / (lane_count - 1)
        lane_y_values = [
            min_y + boundary_inset + lane_spacing * index
            for index in range(lane_count)
        ]

    lane_fragments = []
    # Start directly with the work lanes. Explicit outer and hole perimeter
    # tours substantially retrace the same area and introduce long connector
    # diagonals before the useful sweep begins. The boundary-inset first and
    # final lanes still place the whole safe area within one swath of a pass.
    margin = max(max_x - min_x, width, 1.0)
    for lane_y in lane_y_values:
        cutter = LineString([(min_x - margin, lane_y), (max_x + margin, lane_y)])
        fragments = _line_fragments(aligned.intersection(cutter))
        fragments.sort(key=lambda line: line.bounds[0])
        lane_fragments.extend(fragments)

    path = _order_lane_fragments(lane_fragments, aligned)

    if len(path) < 2:
        raise ValueError("Coverage polygon did not produce a usable lawnmower path")

    result = []
    for x_coord, y_coord in path:
        unrotated = rotate(Point(x_coord, y_coord), sweep_angle, origin=origin)
        lon, lat = to_wgs84.transform(unrotated.x, unrotated.y)
        point = [round(float(lon), 10), round(float(lat), 10)]
        if not result or point != result[-1]:
            result.append(point)
    return result


def _polygon_from_coordinates(coordinates):
    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        raise ValueError("Coverage Polygon coordinates must contain at least one ring")

    first = coordinates[0]
    if first and isinstance(first[0], (int, float)):
        rings = [coordinates]
    else:
        rings = coordinates

    polygon = Polygon(rings[0], holes=rings[1:] or None)
    if polygon.is_empty or polygon.area == 0:
        raise ValueError("Coverage Polygon is empty")
    if not polygon.is_valid:
        repaired = polygon.buffer(0)
        if not isinstance(repaired, Polygon) or repaired.is_empty:
            raise ValueError("Coverage Polygon is invalid and could not be repaired")
        polygon = repaired
    return polygon


def _project_polygon_to_local_utm(polygon):
    centroid = polygon.centroid
    if not (-80.0 <= centroid.y <= 84.0):
        raise ValueError("Coverage Polygon is outside the supported UTM latitude range")
    zone = min(60, max(1, int((centroid.x + 180.0) // 6.0) + 1))
    epsg = (32600 if centroid.y >= 0 else 32700) + zone
    local_crs = CRS.from_epsg(epsg)
    to_local = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True)
    return transform(to_local.transform, polygon), to_wgs84, to_local


def _subtract_risk_polygons(workspace, risk_polygons, to_local, clearance):
    """Cut buffered WGS84 risk polygons out of a projected workspace."""
    obstacles = []
    for risk_polygon in risk_polygons:
        if risk_polygon is None or risk_polygon.is_empty:
            continue
        projected_risk = transform(to_local.transform, risk_polygon)
        parts = (
            list(projected_risk.geoms)
            if isinstance(projected_risk, MultiPolygon)
            else [projected_risk]
        )
        for part in parts:
            if not isinstance(part, Polygon) or not part.intersects(workspace):
                continue
            obstacles.append(part.buffer(clearance, join_style=2))

    if not obstacles:
        return workspace, 0

    safe_area = workspace.difference(unary_union(obstacles))
    if not safe_area.is_valid:
        safe_area = safe_area.buffer(0)
    if safe_area.is_empty:
        raise ValueError("Risk zones leave no safe area to cover")
    if isinstance(safe_area, Polygon):
        return safe_area, len(obstacles)

    polygon_parts = []
    if isinstance(safe_area, (MultiPolygon, GeometryCollection)):
        polygon_parts = [part for part in safe_area.geoms if isinstance(part, Polygon) and not part.is_empty]
    if len(polygon_parts) == 1:
        return polygon_parts[0], len(obstacles)
    raise ValueError(
        "Risk zones split the coverage area into disconnected regions; "
        "a continuous in-geofence sweep is not possible"
    )


def _longest_rectangle_edge_angle(polygon):
    rectangle_points = list(polygon.minimum_rotated_rectangle.exterior.coords)
    longest_edge = max(
        zip(rectangle_points, rectangle_points[1:]),
        key=lambda pair: Point(pair[0]).distance(Point(pair[1])),
    )
    (start_x, start_y), (end_x, end_y) = longest_edge
    return math.degrees(math.atan2(end_y - start_y, end_x - start_x))


def _line_fragments(geometry):
    if isinstance(geometry, LineString):
        return [geometry] if geometry.length > 1e-6 else []
    if isinstance(geometry, (MultiLineString, GeometryCollection)):
        fragments = []
        for part in geometry.geoms:
            fragments.extend(_line_fragments(part))
        return fragments
    return []


def _order_lane_fragments(fragments, polygon):
    """Join every work lane using the nearest risk-safe endpoint.

    A strict row-by-row order crosses around the same obstacle once per split
    row. Choosing the nearest remaining fragment instead completes one side of
    a hole before crossing to the other, eliminating repeated obstacle edges
    and long connector diagonals while retaining every mowing segment.
    """
    remaining = [list(fragment.coords) for fragment in fragments]
    if not remaining:
        return []

    path = list(remaining.pop(0))
    while remaining:
        best = None
        for fragment_index, fragment_points in enumerate(remaining):
            for reverse in (False, True):
                oriented = (
                    list(reversed(fragment_points))
                    if reverse
                    else fragment_points
                )
                connector = _shortest_inside_path(path[-1], oriented[0], polygon)
                connector_length = sum(
                    math.dist(start, end)
                    for start, end in zip(connector, connector[1:])
                )
                candidate = (
                    connector_length,
                    fragment_index,
                    reverse,
                    oriented,
                    connector,
                )
                if best is None or candidate[:3] < best[:3]:
                    best = candidate

        _, fragment_index, _, oriented, connector = best
        remaining.pop(fragment_index)
        for point in connector[1:]:
            if point != path[-1]:
                path.append(point)
        for point in oriented:
            if point != path[-1]:
                path.append(point)
    return path


def _append_inside_path(path, points, polygon):
    points = [(float(x_coord), float(y_coord)) for x_coord, y_coord in points]
    if not points:
        return
    if path:
        connector = _shortest_inside_path(path[-1], points[0], polygon)
        for point in connector[1:]:
            if point != path[-1]:
                path.append(point)
    for point in points:
        if not path or point != path[-1]:
            path.append(point)


def _shortest_inside_path(start, destination, polygon):
    direct = LineString([start, destination])
    tolerant_polygon = polygon.buffer(1e-7)
    if tolerant_polygon.covers(direct):
        return [start, destination]

    vertices = [start, destination]
    for ring in [polygon.exterior, *polygon.interiors]:
        vertices.extend((float(x_coord), float(y_coord)) for x_coord, y_coord in list(ring.coords)[:-1])
    vertices = list(dict.fromkeys(vertices))

    adjacency = [[] for _ in vertices]
    for left in range(len(vertices)):
        for right in range(left + 1, len(vertices)):
            segment = LineString([vertices[left], vertices[right]])
            if tolerant_polygon.covers(segment):
                distance = segment.length
                adjacency[left].append((right, distance))
                adjacency[right].append((left, distance))

    destination_index = 1
    queue = [(0.0, 0)]
    distances = {0: 0.0}
    previous = {}
    while queue:
        current_distance, current = heapq.heappop(queue)
        if current == destination_index:
            break
        if current_distance != distances.get(current):
            continue
        for neighbor, edge_distance in adjacency[current]:
            candidate = current_distance + edge_distance
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = current
                heapq.heappush(queue, (candidate, neighbor))

    if destination_index not in distances:
        raise ValueError("Could not connect coverage passes without leaving the Polygon")

    indices = [destination_index]
    while indices[-1] != 0:
        indices.append(previous[indices[-1]])
    return [vertices[index] for index in reversed(indices)]

class MaximizeCoverage:
    def __init__(self, graph):
        """
        Initialize the MaximizeCoverage class with a graph.
        
        :param graph: A networkx graph containing nodes with x, y coordinates.
        """
        self.graph = graph

    def get_nodes_inside_geometry(self, geometry_type, coordinates):
        """
        Extracts graph nodes that fall inside a given Polygon or LineString.

        :param geometry_type: "Polygon" or "LineString"
        :param coordinates: The list of coordinate points defining the geometry.
        :return: List of node IDs that fall inside the geometry.
        """
        if geometry_type == "Polygon":
            # Flatten coordinates list if nested
            if isinstance(coordinates[0], list):
                coordinates = coordinates[0]  # Extract actual points

            polygon = Polygon(coordinates)

        elif geometry_type == "LineString":
            line = LineString(coordinates)

        else:
            raise ValueError(f"Unsupported geometry type: {geometry_type}")

        # Check which graph nodes fall inside the geometry
        inside_nodes = []
        for node_id in self.graph.nodes:
            node_x, node_y = self.graph.nodes[node_id]["x"], self.graph.nodes[node_id]["y"]
            node_point = Point(node_x, node_y)

            if geometry_type == "Polygon" and polygon.contains(node_point):
                inside_nodes.append(node_id)
            elif geometry_type == "LineString" and line.distance(node_point) < 1e-6:  # Threshold for inclusion
                inside_nodes.append(node_id)

        return inside_nodes

    def solve_mclp(self, candidate_nodes, K):
        """
        Solve the Maximum Covering Location Problem (MCLP) to determine optimal node placements.

        :param candidate_nodes: List of node IDs that can be used as potential coverage sites.
        :param K: Number of agents (coverage locations to select).
        :return: List of selected coordinates [(x1, y1), (x2, y2), ...].
        """
        if len(candidate_nodes) <= K:
            return [(self.graph.nodes[node]["x"], self.graph.nodes[node]["y"]) for node in candidate_nodes]

        # Extract node coordinates
        node_coords = [(self.graph.nodes[node]["x"], self.graph.nodes[node]["y"]) for node in candidate_nodes]
        num_nodes = len(node_coords)

        # Compute pairwise distances
        D = distance_matrix(node_coords, node_coords)

        # Set coverage radius (heuristic: average node distance)
        radius = D.mean()

        # Convert distance matrix into a binary coverage matrix (1 if within radius, 0 otherwise)
        coverage_matrix = (D <= radius).astype(int)

        # Create Gurobi Model
        m = Model()
        x = {j: m.addVar(vtype=GRB.BINARY, name=f"x{j}") for j in range(num_nodes)}
        y = {i: m.addVar(vtype=GRB.BINARY, name=f"y{i}") for i in range(num_nodes)}

        # Constraint: Select exactly K sites
        m.addConstr(quicksum(x[j] for j in range(num_nodes)) == K)

        # Constraint: Each node should be covered by at least one selected site
        for i in range(num_nodes):
            m.addConstr(quicksum(x[j] for j in range(num_nodes) if coverage_matrix[i, j]) >= y[i])

        # Objective: Maximize total coverage
        m.setObjective(quicksum(y[i] for i in range(num_nodes)), GRB.MAXIMIZE)
        m.setParam("OutputFlag", 0)
        m.optimize()

        # Extract solution
        selected_coords = [node_coords[j] for j in range(num_nodes) if x[j].x > 0.5]
        return selected_coords  # Now returns coordinates instead of node IDs


    # def coverage_algorithm(self, geometry_type, coordinates, K):
    #     """
    #     Compute K optimal coverage points inside the given geometry.

    #     :param geometry_type: "Polygon" or "LineString".
    #     :param coordinates: Coordinates defining the geometry.
    #     :param K: Number of coverage points to find.
    #     :return: List of selected node IDs.
    #     """
    #     candidate_nodes = self.get_nodes_inside_geometry(geometry_type, coordinates)
    #     if not candidate_nodes:
    #         return []  # No valid nodes found in the geometry

    #     return self.solve_mclp(candidate_nodes, K)
