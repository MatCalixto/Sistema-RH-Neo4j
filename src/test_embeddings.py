"""Preview embeddings without modifying the database."""
from src.config import load_encoder
from src.import_graph import preparar_documentos

if __name__ == "__main__":
    for document in preparar_documentos(load_encoder()):
        print(document["title"], len(document["embedding"]))
