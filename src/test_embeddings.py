
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

title = "Política de horas extras"
content = (
    "Funcionários podem realizar horas extras conforme "
    "as necessidades da empresa. A organização recomenda "
    "equilíbrio entre trabalho e vida pessoal."
)

embedding = model.encode(content).tolist()

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

with driver.session() as session:
    session.run(
        """
        CREATE (d:Document {
            title: $title,
            content: $content,
            embedding: $embedding
        })
        """,
        title=title,
        content=content,
        embedding=embedding
    )

driver.close()

print("Documento e embedding armazenados no Neo4j!")
