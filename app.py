"""Interface local: streamlit run app.py."""
import streamlit as st
import graphviz
from src.config import create_driver, load_encoder
from src.extraction import extract_documents, extract_text
from src.import_graph import importar
from src.search import hybrid_search
from src.graph_queries import QUERIES, multi_hop
from src.algorithms import load_graph, pagerank, louvain, shortest_path

st.set_page_config(page_title="HR Intelligence", page_icon="🕸️", layout="wide")
st.title("HR Intelligence")
st.caption("Políticas, pessoas e conexões • demonstração acadêmica com dados fictícios")


@st.cache_resource
def database():
    driver = create_driver()
    try:
        driver.verify_connectivity()
    except Exception:
        driver.close()
        raise
    return driver


@st.cache_resource
def encoder():
    return load_encoder()


def graph_view(graph, nodes=None, limit=100):
    chosen = list(graph if nodes is None else nodes)
    if len(chosen) > limit:
        st.caption(f"Visualização limitada a {limit} nós; os algoritmos usam o grafo completo.")
    chosen = chosen[:limit]
    dot = graphviz.Digraph()
    dot.attr(rankdir="LR")
    for node in chosen:
        attrs = graph.nodes[node]
        dot.node(node, graphviz.escape(str(attrs.get("name", node))),
                 tooltip=", ".join(attrs.get("labels", [])))
    for a, b, attrs in graph.subgraph(chosen).edges(data=True):
        dot.edge(a, b, graphviz.escape(attrs.get("type", "")))
    st.graphviz_chart(dot)


page = st.sidebar.radio("Explorar", ["Visão geral", "Entidades e relações", "Busca híbrida",
                                      "Múltiplos saltos", "Algoritmos"])
st.sidebar.caption("Neo4j configurado pelo arquivo .env")

try:
    if page == "Entidades e relações":
        st.subheader("Extração com evidências")
        st.caption("Vocabulário de RH + dependências sintáticas em português. Relações: ACOMPANHA e AVALIA.")
        text = st.text_area("Teste um texto", "O setor de Human Resources acompanha as horas extras.")
        if st.button("Extrair texto"):
            with st.spinner("Analisando português…"):
                result = extract_text(text)
            st.write("Entidades")
            st.dataframe(result["entidades"], use_container_width=True)
            st.write("Relações")
            st.dataframe(result["relacoes"], use_container_width=True)
            if not result["relacoes"]:
                st.info("Nenhuma relação afirmativa reconhecida pelo vocabulário atual.")
        if st.button("Analisar documentos locais"):
            with st.spinner("Analisando documentos…"):
                results = extract_documents()
            for name, result in results.items():
                with st.expander(name, expanded=True):
                    st.dataframe(result["entidades"], use_container_width=True)
                    st.dataframe(result["relacoes"], use_container_width=True)
    elif page == "Visão geral":
        st.write("Importe o CSV e as políticas para conectar funcionários, áreas, cargos e conceitos.")
        if st.button("Importar / atualizar dados", type="primary"):
            with st.spinner("Extraindo, gerando embeddings e importando…"):
                report = importar(database(), encoder())
            st.success("Importação concluída.")
            st.json(report)
        if st.button("Carregar resumo e grafo"):
            graph = load_graph(database())
            a, b = st.columns(2)
            a.metric("Nós", len(graph))
            b.metric("Conexões", graph.number_of_edges())
            if not graph:
                st.info("O grafo está vazio. Importe os dados primeiro.")
            else:
                graph_view(graph)
    elif page == "Busca híbrida":
        st.subheader("Encontre políticas por significado e palavras")
        with st.form("search"):
            question = st.text_input("Pergunta", "Como evitar a sobrecarga de trabalho?")
            limit = st.slider("Resultados", 1, 20, 5)
            submitted = st.form_submit_button("Pesquisar", type="primary")
        if submitted:
            with st.spinner("Buscando…"):
                results = hybrid_search(database(), encoder(), question, limit)
            if not results:
                st.info("Nenhum documento encontrado. Verifique a importação.")
            for row in results:
                with st.expander(row["title"], expanded=True):
                    st.write(row["content"])
                    st.caption(f"RRF: {row['hybrid_score']:.6f} | posição vetorial: {row['vector_rank']} | posição textual: {row['lexical_rank']}")
            st.caption("A pontuação RRF combina posições; não representa probabilidade ou confiança.")
    elif page == "Múltiplos saltos":
        st.subheader("Percorra conexões do RH")
        name = st.selectbox("Consulta", list(QUERIES))
        employee = st.number_input("Número do funcionário", min_value=1, value=1, step=1)
        limit = st.slider("Limite de linhas", 10, 500, 100)
        with st.expander("Ver consulta Cypher"):
            st.code(QUERIES[name], language="cypher")
        if st.button("Consultar"):
            rows = multi_hop(database(), name, employee, limit)
            if rows:
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("Nenhum caminho encontrado para esses parâmetros.")
    else:
        st.subheader("Algoritmos no grafo")
        st.caption("PageRank segue as direções. Louvain usa conexões sem direção e semente 42. Cada par de nós tem peso 1.")
        if st.button("Carregar / atualizar grafo"):
            st.session_state.graph = load_graph(database())
        graph = st.session_state.get("graph")
        if graph is None:
            st.info("Carregue o grafo para iniciar.")
        elif not graph:
            st.info("Grafo vazio. Importe os dados na visão geral.")
        else:
            method = st.selectbox("Algoritmo", ["PageRank", "Louvain", "Caminho mais curto"])
            if method == "PageRank":
                alpha = st.slider("Fator de amortecimento", 0.05, 0.95, 0.85)
                if st.button("Calcular PageRank"):
                    st.dataframe(pagerank(graph, alpha), use_container_width=True)
            elif method == "Louvain":
                resolution = st.slider("Resolução", 0.1, 3.0, 1.0)
                if st.button("Detectar comunidades"):
                    rows = louvain(graph, resolution)
                    st.metric("Comunidades", len({r["comunidade"] for r in rows}))
                    st.dataframe(rows, use_container_width=True)
            else:
                nodes = sorted(graph, key=lambda n: (str(graph.nodes[n].get("name")), n))
                def label(node):
                    return f"{graph.nodes[node]['name']} ({', '.join(graph.nodes[node]['labels'])}) [{node}]"
                source = st.selectbox("Origem", nodes, format_func=label)
                target = st.selectbox("Destino", nodes, index=min(1, len(nodes) - 1), format_func=label)
                directed = st.checkbox("Respeitar direção das relações")
                if st.button("Encontrar caminho"):
                    result = shortest_path(graph, source, target, directed)
                    if result["encontrado"]:
                        st.metric("Saltos", result["saltos"])
                        st.dataframe(result["nos"], use_container_width=True)
                        st.dataframe(result["arestas"], use_container_width=True)
                        graph_view(graph, [n["id"] for n in result["nos"]])
                    else:
                        st.info("Não há caminho entre esses nós na direção escolhida.")
except Exception as exc:
    # Evita mostrar credenciais, URI e detalhes da infraestrutura no navegador.
    if isinstance(exc, (ValueError, FileNotFoundError)):
        st.error(str(exc))
    else:
        st.error("Não foi possível concluir. Verifique conexão, dependências, modelo e importação.")
        st.caption(f"Tipo do erro: {type(exc).__name__}")
