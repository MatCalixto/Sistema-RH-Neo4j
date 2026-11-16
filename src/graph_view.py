"""Grafo interativo local: IDs Neo4j são strings opacas, nunca portas DOT."""
import json
from pathlib import Path

ASSETS = Path(__file__).with_name("assets")
GROUPS = {
    "Department": {"label": "Departamentos", "color": "#38bdf8"},
    "JobRole": {"label": "Cargos", "color": "#a78bfa"},
    "EducationField": {"label": "Formações", "color": "#fbbf24"},
    "WorkConcept": {"label": "Conceitos", "color": "#34d399"},
    "Document": {"label": "Documentos", "color": "#fb923c"},
    "Role": {"label": "Papéis", "color": "#f472b6"},
    "Employee": {"label": "Funcionários", "color": "#94a3b8"},
    "Other": {"label": "Outros", "color": "#cbd5e1"},
}


def graph_payload(graph, path=None):
    """Preserva IDs e direções; um caminho contém só suas próprias arestas."""
    chosen = list(graph) if path is None else [node["id"] for node in path["nos"]]
    nodes = []
    for index, key in enumerate(chosen):
        attrs = graph.nodes[key]
        group = next((label for label in GROUPS if label in attrs.get("labels", [])), "Other")
        name = str(attrs.get("name", key))
        nodes.append({"id": str(key), "label": f"Funcionário {name}" if group == "Employee" else name,
                      "name": name, "group": group, "labels": attrs.get("labels", []),
                      "order": index})
    if path is None:
        edges = [{"id": f"edge-{index}", "from": str(a), "to": str(b),
                  "relation": attrs.get("type", "Relação")}
                 for index, (a, b, attrs) in enumerate(graph.edges(data=True))]
    else:
        edges = [{"id": f"path-{index}",
                  "from": str(edge["origem"] if edge["sentido_original"] else edge["destino"]),
                  "to": str(edge["destino"] if edge["sentido_original"] else edge["origem"]),
                  "relation": edge["tipo"], "reversed": not edge["sentido_original"]}
                 for index, edge in enumerate(path["arestas"])]
    return {"nodes": nodes, "edges": edges, "groups": GROUPS, "pathMode": path is not None}


def _assets():
    return {name: (ASSETS / name).read_text(encoding="utf-8") for name in
            ("vis-network.min.js", "graph.html", "graph.css", "graph.js")}


def graph_html(graph, path=None):
    assets = _assets()
    # JSON em script não pode encerrar o elemento HTML com nomes de nós.
    payload = json.dumps(graph_payload(graph, path), ensure_ascii=False).replace("<", "\\u003c")
    return (assets["graph.html"].replace("/* GRAPH_CSS */", assets["graph.css"])
            .replace("/* VIS_LIBRARY */", assets["vis-network.min.js"])
            .replace("/* GRAPH_DATA */", payload)
            .replace("/* GRAPH_JS */", assets["graph.js"]))


def graph_view(graph, path=None):
    import streamlit.components.v1 as components
    components.html(graph_html(graph, path), height=800, scrolling=False)
