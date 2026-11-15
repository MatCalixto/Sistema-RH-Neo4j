"""Semantic candidates and their original vector scores."""
from src.config import create_driver, load_encoder
from src.search import hybrid_search

if __name__ == "__main__":
    with create_driver() as driver:
        rows = hybrid_search(driver, load_encoder(), "Como evitar a sobrecarga de trabalho?")
        for row in sorted((r for r in rows if r["vector_rank"] is not None),
                          key=lambda r: r["vector_rank"]):
            print(row["title"], row["vector_score"])
