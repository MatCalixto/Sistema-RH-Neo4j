"""Validação opt-in da base Neo4j já importada, sem escrita."""
import os
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("RUN_NEO4J_TESTS") != "1", reason="Defina RUN_NEO4J_TESTS=1 para usar Neo4j.")]


@pytest.fixture(scope="module")
def driver():
    from src.config import create_driver
    with create_driver() as driver:
        driver.verify_connectivity()
        yield driver


def test_indexes_online(driver):
    from src.config import session_options
    with driver.session(**session_options()) as session:
        rows = session.run("SHOW INDEXES YIELD name, state RETURN name, state").data()
    indexes = {row["name"]: row["state"] for row in rows}
    assert indexes["document_vector"] == indexes["document_fulltext"] == "ONLINE"


def test_multi_hop_queries(driver):
    from src.graph_queries import QUERIES, multi_hop
    for name in QUERIES:
        assert isinstance(multi_hop(driver, name), list)


def test_graph_algorithms(driver):
    from src.algorithms import load_graph, pagerank, louvain
    graph = load_graph(driver)
    assert len(graph) > 0, "Importe os dados antes dos testes."
    assert len(pagerank(graph)) == len(graph)
    assert len(louvain(graph)) == len(graph)


def test_hybrid_search_real_embeddings(driver):
    from src.config import load_encoder
    from src.search import hybrid_search
    rows = hybrid_search(driver, load_encoder(), "horas extras")
    assert rows
    assert any(row["vector_rank"] and row["lexical_rank"] for row in rows)
    assert len({r["id"] for r in rows}) == len(rows)
