import pytest

from app.services import structural_graph


def test_fallback_graph_accepts_node_id_attribute_without_collision() -> None:
    fallback_graph_cls = getattr(structural_graph, "_FallbackGraph", None)
    if fallback_graph_cls is None:
        pytest.skip("networkx available; fallback graph not active")

    graph = fallback_graph_cls()
    graph.add_node("exit_1", node_id="exit_1", node_type="exit", x=10.0, y=20.0)

    assert "exit_1" in graph.nodes
    assert graph.nodes["exit_1"]["node_id"] == "exit_1"
    assert "exit_1" in graph.adjacency


def test_fallback_graph_accepts_edge_attributes_named_from_and_to() -> None:
    fallback_graph_cls = getattr(structural_graph, "_FallbackGraph", None)
    if fallback_graph_cls is None:
        pytest.skip("networkx available; fallback graph not active")

    graph = fallback_graph_cls()
    graph.add_node("room_1")
    graph.add_node("exit_1")
    graph.add_edge(
        "room_1",
        "exit_1",
        edge_id="edge_room_1_exit_1",
        from_node="room_1",
        to_node="exit_1",
        width=2.0,
    )

    assert "exit_1" in graph.adjacency["room_1"]
    assert "room_1" in graph.adjacency["exit_1"]
