
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Carrega as informações do arquivo .env
load_dotenv()

# Recupera as credenciais
URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

# Verifica se as credenciais foram encontradas
if not all([URI, USERNAME, PASSWORD]):
    raise ValueError("Verifique as configurações do arquivo .env")

# Cria a conexão e testa o acesso
with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
    driver.verify_connectivity()

    with driver.session() as session:
        resultado = session.run("RETURN 1 AS teste").single()

        print("Conexão estabelecida com sucesso!")
        print("Resultado do teste:", resultado["teste"])
