import json
import networkx as nx
from src.algorithms import shortest_path
from src.graph_view import graph_payload, graph_html


def graph_fixture():
    graph = nx.DiGraph()
    for node, name, label in [("4:db:1", "1", "Employee"),
                              ("4:db:2", "Pesquisa", "Department"),
                              ("4:db:3", "3", "Employee")]:
        graph.add_node(node, name=name, labels=[label])
    graph.add_edge("4:db:1", "4:db:2", type="WORKS_IN")
    graph.add_edge("4:db:3", "4:db:2", type="WORKS_IN")
    return graph


def test_neo4j_identifiers_preserved_in_edges():
    graph = graph_fixture()
    payload = graph_payload(graph)
    assert len(payload["nodes"]) == 3
    assert {(e["from"], e["to"]) for e in payload["edges"]} == set(graph.edges)
    assert payload["nodes"][0]["label"] == "Funcionário 1"
    assert not payload["pathMode"]


def test_path_edges_keep_direction_without_induced_shortcuts():
    graph = graph_fixture()
    path = shortest_path(graph, "4:db:1", "4:db:3")
    # Uma relação adicional entre os nós não pertence ao caminho calculado.
    graph.add_edge("4:db:1", "4:db:3", type="MENTIONS")
    payload = graph_payload(graph, path)
    assert [n["id"] for n in payload["nodes"]] == ["4:db:1", "4:db:2", "4:db:3"]
    assert len(payload["edges"]) == 2
    assert payload["edges"][1]["from"] == "4:db:3"
    assert payload["edges"][1]["to"] == "4:db:2"
    assert payload["edges"][1]["reversed"]


def test_html_embeds_library_offline_and_escapes_untrusted_text():
    graph = graph_fixture()
    graph.nodes["4:db:1"]["name"] = '</script><img src=x onerror="alert(1)">'
    html = graph_html(graph)
    encoded = html.split('id="graph-data">', 1)[1].split("</script>", 1)[0]
    assert "<img" not in encoded
    assert json.loads(encoded)["nodes"][0]["name"] == graph.nodes["4:db:1"]["name"]
    assert '<script src=' not in html
    assert "/* GRAPH_" not in html


def test_single_node_path_and_empty_graph():
    graph = graph_fixture()
    payload = graph_payload(graph, shortest_path(graph, "4:db:1", "4:db:1"))
    assert len(payload["nodes"]) == 1 and payload["edges"] == []
    assert graph_payload(nx.DiGraph())["nodes"] == []
