from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest


nx = pytest.importorskip("networkx")
ox = pytest.importorskip("osmnx")

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = (
    ROOT
    / "backend"
    / "fog"
    / "planner"
    / "ros2ws"
    / "src"
    / "path_planning_lib"
)
sys.path.insert(0, str(PACKAGE_ROOT))

from path_planning_lib.graph import EdgeSnapIndex, add_virtual_endpoint_nodes  # noqa: E402
from path_planning_lib.mapf import AStar  # noqa: E402
from path_planning_lib.models import Buddy  # noqa: E402


def _bidirectional_edge_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:4326"
    graph.add_node(1, x=4.0, y=50.0)
    graph.add_node(2, x=4.001, y=50.0)
    graph.add_edge(1, 2, key=0, length=71.475, risk=False, road_kind="test")
    graph.add_edge(2, 1, key=0, length=71.475, risk=False, road_kind="test")
    return graph


def test_virtual_endpoint_splits_both_directions_without_mutating_base_graph() -> None:
    graph = _bidirectional_edge_graph()
    projected = ox.project_graph(graph)
    snap = EdgeSnapIndex(graph, projected).snap([4.0004, 50.0001])

    query_graph, resolved = add_virtual_endpoint_nodes(graph, [snap])
    virtual = resolved[0]["node"]

    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 2
    assert graph.has_edge(1, 2, 0)
    assert virtual not in graph
    assert query_graph.has_edge(1, virtual, 0)
    assert query_graph.has_edge(virtual, 2, 0)
    assert query_graph.has_edge(2, virtual, 0)
    assert query_graph.has_edge(virtual, 1, 0)
    assert query_graph.edges[1, virtual, 0]["road_kind"] == "test"
    assert math.isclose(
        query_graph.edges[1, virtual, 0]["length"]
        + query_graph.edges[virtual, 2, 0]["length"],
        graph.edges[1, 2, 0]["length"],
        rel_tol=1e-9,
    )


def test_two_query_points_on_same_edge_route_directly_between_virtual_nodes() -> None:
    graph = _bidirectional_edge_graph()
    index = EdgeSnapIndex(graph, ox.project_graph(graph))
    start_snap = index.snap([4.0002, 50.0001])
    destination_snap = index.snap([4.0007, 50.0001])
    query_graph, resolved = add_virtual_endpoint_nodes(graph, [start_snap, destination_snap])
    agent = Buddy("agent", localization=[4.0002, 50.0001], nominal_speed=1.0)

    route, _cost = AStar(
        query_graph,
        agent,
        [[4.0007, 50.0001]],
        start_node=resolved[0]["node"],
        destination_node=resolved[1]["node"],
    ).search()

    assert [state.get_node() for state in route] == [resolved[0]["node"], resolved[1]["node"]]
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 2


def test_edge_snap_index_ignores_a_nearer_risk_edge() -> None:
    graph = _bidirectional_edge_graph()
    graph.edges[1, 2, 0]["risk"] = True
    graph.edges[2, 1, 0]["risk"] = True
    graph.add_node(3, x=4.0, y=50.0003)
    graph.add_node(4, x=4.001, y=50.0003)
    graph.add_edge(3, 4, key=0, length=71.475, risk=False)
    graph.add_edge(4, 3, key=0, length=71.475, risk=False)

    snap = EdgeSnapIndex(graph, ox.project_graph(graph)).snap([4.0005, 50.00001])

    assert set(snap["edge"][:2]) == {3, 4}

