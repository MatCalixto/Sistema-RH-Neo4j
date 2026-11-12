
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

# Carrega o modelo de embeddings
model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

# Pergunta do usuário
question = "Como evitar que os funcionários fiquem sobrecarregados?"

# Termos utilizados na busca textual
fulltext_query = "horas extras"

# Transforma a pergunta em vetor
question_embedding = model.encode(question).tolist()

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

with driver.session() as session:

    # 1. Busca vetorial
    vector_result = session.run(
        """
        CALL db.index.vector.queryNodes(
            'document_vector',
            5,
            $embedding
        )
        YIELD node, score
        RETURN elementId(node) AS id,
               node.title AS title,
               node.content AS content
        """,
        embedding=question_embedding
    )

    vector_documents = list(vector_result)

    # 2. Busca Fulltext
    
    fulltext_result = session.run(
        """
        CALL db.index.fulltext.queryNodes(
            'document_fulltext',
            $search_text
        )
        YIELD node, score
        RETURN elementId(node) AS id,
            node.title AS title,
            node.content AS content
        """,
        search_text=fulltext_query
    )


    fulltext_documents = list(fulltext_result)

    # 3. Combinação dos resultados
    combined = {}

    for rank, doc in enumerate(vector_documents, start=1):
        combined[doc["id"]] = {
            "title": doc["title"],
            "content": doc["content"],
            "hybrid_score": 1 / (60 + rank)
        }

    for rank, doc in enumerate(fulltext_documents, start=1):
        doc_id = doc["id"]

        if doc_id not in combined:
            combined[doc_id] = {
                "title": doc["title"],
                "content": doc["content"],
                "hybrid_score": 0
            }

        combined[doc_id]["hybrid_score"] += 1 / (60 + rank)

    # 4. Ordena os documentos pela pontuação híbrida
    ranked_documents = sorted(
        combined.values(),
        key=lambda doc: doc["hybrid_score"],
        reverse=True
    )

    print("\n===== RESULTADOS DA BUSCA HÍBRIDA =====")

    for doc in ranked_documents:
        print("\nDocumento:", doc["title"])
        print("Conteúdo:", doc["content"])
        print("Pontuação híbrida:", doc["hybrid_score"])

driver.close()
