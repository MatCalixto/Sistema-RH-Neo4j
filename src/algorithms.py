"""Análise em memória dos nós/arestas do Neo4j, sem truncar o grafo."""
import networkx as nx
from .config import session_options

LABELS = ["Employee", "Department", "JobRole", "Role", "EducationField", "WorkConcept", "Document"]
RELATIONS = ["WORKS_IN", "HAS_ROLE", "EDUCATED_IN", "MENTIONS", "ACOMPANHA", "AVALIA"]


def load_graph(driver):
    graph = nx.DiGraph()
    with driver.session(**session_options()) as session:
        # Uma única transação mantém a projeção consistente.
        def read(tx):
            nodes = tx.run("""
                MATCH (n) WHERE any(label IN labels(n) WHERE label IN $labels)
                RETURN elementId(n) AS id, labels(n) AS labels,
                       coalesce(n.name, n.title, toString(n.employee_id)) AS name
            """, labels=LABELS).data()
            edges = tx.run("""
                MATCH (a)-[r]->(b) WHERE type(r) IN $types
                RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS type
            """, types=RELATIONS).data()
            return nodes, edges
        nodes, edges = session.execute_read(read)
    for row in nodes:
        graph.add_node(row["id"], name=row["name"], labels=row["labels"])
    for row in edges:
        if row["source"] in graph and row["target"] in graph:
            # Evidências repetidas não aumentam artificialmente o peso.
            graph.add_edge(row["source"], row["target"], type=row["type"])
    return graph


def pagerank(graph, alpha=0.85, tolerance=1e-10, max_iterations=500):
    """Power iteration com redistribuição uniforme dos nós sem saída."""
    if not 0 < alpha < 1 or tolerance <= 0 or max_iterations < 1:
        raise ValueError("Parâmetros de PageRank inválidos.")
    if not graph:
        return []
    count = len(graph)
    scores = dict.fromkeys(graph, 1 / count)
    for _ in range(max_iterations):
        dangling = sum(scores[n] for n in graph if graph.out_degree(n) == 0)
        updated = dict.fromkeys(graph, (1 - alpha) / count + alpha * dangling / count)
        for node in graph:
            degree = graph.out_degree(node)
            if degree:
                for target in graph.successors(node):
                    updated[target] += alpha * scores[node] / degree
        if sum(abs(updated[n] - scores[n]) for n in graph) < tolerance:
            return [{"id": n, "nome": graph.nodes[n].get("name", n), "score": score}
                    for n, score in sorted(updated.items(), key=lambda item: (-item[1], item[0]))]
        scores = updated
    raise RuntimeError("PageRank não convergiu; aumente max_iterations.")


def louvain(graph, resolution=1.0, seed=42):
    if resolution <= 0:
        raise ValueError("A resolução deve ser positiva.")
    if not graph:
        return []
    undirected = graph.to_undirected()
    communities = (nx.community.louvain_communities(undirected, resolution=resolution, seed=seed)
                   if undirected.number_of_edges() else [{n} for n in graph])
    communities = sorted(communities, key=lambda group: (-len(group), sorted(group)))
    return [{"id": node, "nome": graph.nodes[node].get("name", node), "comunidade": i}
            for i, members in enumerate(communities) for node in sorted(members)]


def shortest_path(graph, source, target, directed=False):
    if source not in graph or target not in graph:
        raise ValueError("Selecione nós existentes no grafo.")
    projection = graph if directed else graph.to_undirected()
    try:
        path = nx.shortest_path(projection, source, target)
    except nx.NetworkXNoPath:
        return {"encontrado": False, "saltos": None, "nos": [], "arestas": []}
    edges = []
    for a, b in zip(path, path[1:]):
        forward = graph.has_edge(a, b)
        edges.append({"origem": a, "destino": b,
                      "tipo": graph.edges[a, b].get("type") if forward
                      else graph.edges[b, a].get("type"), "sentido_original": forward})
    return {"encontrado": True, "saltos": len(path) - 1,
            "nos": [{"id": n, **graph.nodes[n]} for n in path], "arestas": edges}
