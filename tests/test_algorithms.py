import networkx as nx
import pytest
from src.algorithms import pagerank, louvain, shortest_path


def test_pagerank_cycle_symmetry_and_normalization():
    graph = nx.DiGraph([(str(i), str((i+1) % 3)) for i in range(3)])
    rows = pagerank(graph)
    assert all(row["score"] == pytest.approx(1/3) for row in rows)
    assert sum(row["score"] for row in rows) == pytest.approx(1)


def test_pagerank_sink_and_isolated_node():
    graph = nx.DiGraph([("a", "b")])
    graph.add_node("c")
    scores = {r["id"]: r["score"] for r in pagerank(graph)}
    assert scores["b"] > scores["a"] == scores["c"]
    assert sum(scores.values()) == pytest.approx(1)
    # Solução analítica: x = (1 - alpha) / 3 + alpha * (x + y) / 3;
    # y = x * (1 + alpha), 2x + y = 1.
    assert scores["a"] == pytest.approx(1 / 3.85)


def test_louvain_separates_disconnected_cliques():
    graph = nx.disjoint_union(nx.complete_graph(5), nx.complete_graph(5)).to_directed()
    graph = nx.relabel_nodes(graph, str)
    rows = louvain(graph)
    groups = {}
    for row in rows:
        groups.setdefault(row["comunidade"], set()).add(row["id"])
    assert list(groups.values()) == [set(map(str, range(5))), set(map(str, range(5, 10)))]
    assert rows == louvain(graph)


def test_empty_and_edgeless_graphs():
    assert pagerank(nx.DiGraph()) == []
    assert louvain(nx.DiGraph()) == []
    graph = nx.DiGraph()
    graph.add_nodes_from(["a", "b"])
    assert len({r["comunidade"] for r in louvain(graph)}) == 2


def test_shortest_path_direction_missing_and_identity():
    graph = nx.DiGraph()
    graph.add_edge("a", "b", type="WORKS_IN")
    graph.add_edge("c", "b", type="WORKS_IN")
    result = shortest_path(graph, "a", "c")
    assert result["saltos"] == 2
    assert [e["sentido_original"] for e in result["arestas"]] == [True, False]
    assert not shortest_path(graph, "a", "c", directed=True)["encontrado"]
    assert shortest_path(graph, "a", "a")["saltos"] == 0
    with pytest.raises(ValueError):
        shortest_path(graph, "missing", "a")
