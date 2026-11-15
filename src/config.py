"""Configuração compartilhada; importar módulos nunca abre conexões."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ROOT / "documents"
CSV_FILE = ROOT / "data/WA_Fn-UseC_-HR-Employee-Attrition.csv"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSIONS = 384


def create_driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    values = [os.getenv(key) for key in
              ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")]
    if not all(values):
        raise ValueError("Configure NEO4J_URI, NEO4J_USERNAME e NEO4J_PASSWORD no .env.")
    return GraphDatabase.driver(values[0], auth=tuple(values[1:]),
                                connection_timeout=15)


def session_options():
    database = os.getenv("NEO4J_DATABASE")
    return {"database": database} if database else {}


def load_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)
