"""Hybrid search CLI: python -m src.test_hybrid_search [question]."""
import argparse
from src.config import create_driver, load_encoder
from src.search import hybrid_search

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", default="Como evitar a sobrecarga de trabalho?")
    args = parser.parse_args()
    with create_driver() as driver:
        for document in hybrid_search(driver, load_encoder(), args.question):
            print(document)
