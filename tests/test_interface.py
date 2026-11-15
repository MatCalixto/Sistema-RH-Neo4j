"""Smoke tests da interface sem iniciar servidor ou depender do banco."""
import pytest
from pathlib import Path
pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


def test_initial_screen_and_navigation():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=60).run()
    assert not app.exception
    for page in ["Entidades e relações", "Busca híbrida", "Múltiplos saltos", "Algoritmos"]:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception
        assert not app.error


def test_algorithm_controls_with_local_graph():
    import networkx as nx
    graph = nx.DiGraph()
    graph.add_node("a", name="Pessoa", labels=["Employee"])
    graph.add_node("b", name="Área", labels=["Department"])
    graph.add_edge("a", "b", type="WORKS_IN")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=60).run()
    app.session_state["graph"] = graph
    app.sidebar.radio[0].set_value("Algoritmos").run()
    app.button[1].click().run()
    assert not app.error and not app.exception and len(app.dataframe) == 1
    app.selectbox[0].set_value("Louvain").run()
    app.button[1].click().run()
    assert not app.error and not app.exception and len(app.dataframe) == 1
    app.selectbox[0].set_value("Caminho mais curto").run()
    app.button[1].click().run()
    assert not app.error and not app.exception
    assert app.metric[0].value == "1"
