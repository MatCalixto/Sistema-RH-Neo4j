"""Busca semântica + lexical com Reciprocal Rank Fusion (RRF)."""
import re
from .config import session_options


def reciprocal_rank_fusion(vector, lexical, limit=5, k=60):
    if limit < 1 or k < 1:
        raise ValueError("limit e k devem ser positivos.")
    combined = {}
    for channel, records in (("vector", vector), ("lexical", lexical)):
        seen = set()
        for rank, record in enumerate(records, 1):
            doc = dict(record)
            key = doc["id"]
            if key in seen:
                continue
            seen.add(key)
            result = combined.setdefault(key, {
                "id": key, "title": doc["title"], "content": doc["content"],
                "hybrid_score": 0.0, "vector_score": None, "lexical_score": None,
                "vector_rank": None, "lexical_rank": None,
            })
            result["hybrid_score"] += 1 / (k + rank)
            result[f"{channel}_score"] = doc.get("score")
            result[f"{channel}_rank"] = rank
    return sorted(combined.values(),
                  key=lambda row: (-row["hybrid_score"], row["title"], row["id"]))[:limit]


def lexical_query(text):
    # Não interpreta operadores Lucene fornecidos pelo usuário.
    return " OR ".join('"' + token + '"' for token in re.findall(r"\w+", text))


def hybrid_search(driver, encoder, question, limit=5, candidates=20):
    if not question.strip() or not lexical_query(question):
        raise ValueError("Digite uma pergunta com palavras.")
    if not 1 <= limit <= 100 or not limit <= candidates <= 1000:
        raise ValueError("Use 1 <= limite <= candidatos <= 1000.")
    embedding = encoder.encode(question, normalize_embeddings=True).tolist()
    with driver.session(**session_options()) as session:
        vector = session.run("""
            CALL db.index.vector.queryNodes('document_vector', $limit, $embedding)
            YIELD node, score
            RETURN elementId(node) AS id, node.title AS title,
                   node.content AS content, score
            ORDER BY score DESC, title, id
        """, limit=candidates, embedding=embedding).data()
        lexical = session.run("""
            CALL db.index.fulltext.queryNodes('document_fulltext', $search_text,
                                             {limit: $limit})
            YIELD node, score
            RETURN elementId(node) AS id, node.title AS title,
                   node.content AS content, score
            ORDER BY score DESC, title, id
        """, search_text=lexical_query(question), limit=candidates).data()
    return reciprocal_rank_fusion(vector, lexical, limit)
