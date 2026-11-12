
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

# Carrega o mesmo modelo usado para gerar o embedding do documento
model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

# Pergunta que queremos pesquisar
question = "Como evitar que os funcionários fiquem sobrecarregados?"

# Transforma a pergunta em um vetor de 384 dimensões
question_embedding = model.encode(question).tolist()

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

# Pesquisa o documento mais semelhante à pergunta
with driver.session() as session:
    result = session.run(
        """
        CALL db.index.vector.queryNodes(
            'document_vector',
            1,
            $embedding
        )
        YIELD node, score
        RETURN node.title AS title,
               node.content AS content,
               score
        """,
        embedding=question_embedding
    )

    for record in result:
        print("Documento encontrado:", record["title"])
        print("Conteúdo:", record["content"])
        print("Similaridade:", record["score"])

driver.close()
