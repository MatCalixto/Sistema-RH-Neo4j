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
    assert len(app.get("iframe")) == 1
    # O resultado não desaparece quando o Streamlit executa a tela novamente.
    app.run()
    assert len(app.get("iframe")) == 1


def test_overview_graph_persists_on_rerun():
    import networkx as nx
    graph = nx.DiGraph()
    graph.add_node("4:db:1", name="Área", labels=["Department"])
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=60).run()
    app.session_state["overview_graph"] = graph
    app.run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "1"
    assert len(app.get("iframe")) == 1
    app.run()
    assert len(app.get("iframe")) == 1
