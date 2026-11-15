"""Compatibility entry point: python -m src.test_spacy."""
from src.extraction import extrair_relacoes, extract_text, load_nlp

if __name__ == "__main__":
    for relation in extrair_relacoes():
        print(relation)
