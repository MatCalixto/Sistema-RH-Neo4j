
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from test_spacy import extrair_relacoes

# --------------------------------------------------
# 1. CONFIGURAÇÕES
# --------------------------------------------------

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([URI, USERNAME, PASSWORD]):
    raise ValueError("Verifique as configurações do arquivo .env")

driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

ARQUIVO_CSV = Path("data/WA_Fn-UseC_-HR-Employee-Attrition.csv")
PASTA_DOCUMENTOS = Path("documents")

MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"

TAMANHO_LOTE = 100

# --------------------------------------------------
# 2. MAPEAMENTO DAS COLUNAS DOS FUNCIONÁRIOS
# --------------------------------------------------

colunas_funcionario = {
    "EmployeeNumber": "employee_id",
    "Age": "age",
    "Gender": "gender",
    "Attrition": "attrition",
    "BusinessTravel": "business_travel",
    "DistanceFromHome": "distance_from_home",
    "Education": "education",
    "EnvironmentSatisfaction": "environment_satisfaction",
    "HourlyRate": "hourly_rate",
    "JobInvolvement": "job_involvement",
    "JobLevel": "job_level",
    "JobSatisfaction": "job_satisfaction",
    "MaritalStatus": "marital_status",
    "MonthlyIncome": "monthly_income",
    "NumCompaniesWorked": "companies_worked",
    "OverTime": "over_time",
    "PercentSalaryHike": "salary_hike",
    "PerformanceRating": "performance_rating",
    "RelationshipSatisfaction": "relationship_satisfaction",
    "StockOptionLevel": "stock_option_level",
    "TotalWorkingYears": "total_working_years",
    "TrainingTimesLastYear": "training_times_last_year",
    "WorkLifeBalance": "work_life_balance",
    "YearsAtCompany": "years_at_company",
    "YearsInCurrentRole": "years_in_current_role",
    "YearsSinceLastPromotion": "years_since_last_promotion",
    "YearsWithCurrManager": "years_with_current_manager"
}

# --------------------------------------------------
# 3. IMPORTAÇÃO DOS FUNCIONÁRIOS EM LOTES
# --------------------------------------------------

def salvar_lote_funcionarios(tx, funcionarios):

    query = """
    UNWIND $funcionarios AS funcionario

    MERGE (e:Employee {employee_id: funcionario.employee_id})
    SET e += funcionario.propriedades

    MERGE (d:Department {name: funcionario.department})
    MERGE (j:JobRole {name: funcionario.job_role})
    MERGE (ef:EducationField {name: funcionario.education_field})

    MERGE (e)-[:WORKS_IN]->(d)
    MERGE (e)-[:HAS_ROLE]->(j)
    MERGE (e)-[:EDUCATED_IN]->(ef)

    RETURN count(e) AS total
    """

    resultado = tx.run(query, funcionarios=funcionarios)
    return resultado.single()["total"]


def preparar_funcionarios(df):

    funcionarios = []

    for _, linha in df.iterrows():

        propriedades = {
            novo_nome: (
                None if pd.isna(linha[coluna])
                else linha[coluna].item()
                if hasattr(linha[coluna], "item")
                else linha[coluna]
            )
            for coluna, novo_nome in colunas_funcionario.items()
        }

        funcionarios.append({
            "employee_id": int(linha["EmployeeNumber"]),
            "propriedades": propriedades,
            "department": linha["Department"],
            "job_role": linha["JobRole"],
            "education_field": linha["EducationField"]
        })

    return funcionarios


# --------------------------------------------------
# 4. IMPORTAÇÃO DOS DOCUMENTOS E EMBEDDINGS
# --------------------------------------------------

def salvar_documento(tx, documento):

    query = """
    MERGE (d:Document {title: $title})

    SET d.content = $content,
        d.embedding = $embedding

    RETURN d.title AS title
    """

    resultado = tx.run(query, **documento)
    return resultado.single()


def preparar_documentos(modelo):

    if not PASTA_DOCUMENTOS.exists():
        raise FileNotFoundError("Pasta documents não encontrada.")

    arquivos = sorted(PASTA_DOCUMENTOS.glob("*.txt"))

    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo .txt encontrado.")

    documentos = []

    for arquivo in arquivos:

        conteudo = arquivo.read_text(encoding="utf-8")

        embedding = modelo.encode(
            conteudo,
            normalize_embeddings=True
        ).tolist()

        documentos.append({
            "title": arquivo.name,
            "content": conteudo,
            "embedding": embedding
        })

    return documentos


# --------------------------------------------------
# 5. IMPORTAÇÃO DAS RELAÇÕES EXTRAÍDAS
# --------------------------------------------------

def salvar_relacao(tx, relacao):

    # Lista de tipos e labels permitidos.
    tipos_permitidos = ["ACOMPANHA", "AVALIA"]
    origens_permitidas = ["Department", "Role"]

    tipo = relacao["relacao"]
    origem_tipo = relacao["origem_tipo"]

    if tipo not in tipos_permitidos:
        raise ValueError(f"Tipo de relação inválido: {tipo}")

    if origem_tipo not in origens_permitidas:
        raise ValueError(f"Tipo de origem inválido: {origem_tipo}")

    # Os nomes são escolhidos somente pelas listas permitidas.
    query = f"""
    MERGE (origem:{origem_tipo} {{name: $origem}})
    MERGE (destino:WorkConcept {{name: $destino}})
    MERGE (doc:Document {{title: $documento}})

    MERGE (origem)-[r:{tipo} {{
        documento: $documento,
        evidencia: $evidencia
    }}]->(destino)

    MERGE (doc)-[:MENTIONS]->(destino)

    RETURN origem.name AS origem,
           type(r) AS relacao,
           destino.name AS destino,
           doc.title AS documento
    """

    resultado = tx.run(
        query,
        origem=relacao["origem"],
        destino=relacao["destino"],
        documento=relacao["documento"],
        evidencia=relacao["evidencia"]
    )

    return resultado.single()


# --------------------------------------------------
# 6. EXECUÇÃO PRINCIPAL
# --------------------------------------------------

try:

    driver.verify_connectivity()
    print("Conexão com Neo4j estabelecida!")

    # Garante unicidade dos documentos.
    with driver.session() as session:

        session.run("""
        CREATE CONSTRAINT document_title_unique IF NOT EXISTS
        FOR (d:Document)
        REQUIRE d.title IS UNIQUE
        """)

    # Carrega o modelo de embeddings.
    print("\nCarregando modelo de embeddings...")

    modelo = SentenceTransformer(MODELO_EMBEDDING)

    # Lê e prepara os documentos.
    documentos = preparar_documentos(modelo)

    # Lê e prepara os funcionários.
    df = pd.read_csv(ARQUIVO_CSV)
    funcionarios = preparar_funcionarios(df)

    # Extrai as relações dos documentos.
    relacoes = extrair_relacoes()

    print(f"\nDocumentos encontrados: {len(documentos)}")
    print(f"Funcionários preparados: {len(funcionarios)}")
    print(f"Relações extraídas: {len(relacoes)}")

    with driver.session() as session:

        # Importa os documentos.
        print("\nImportando documentos...")

        for documento in documentos:
            resultado = session.execute_write(
                salvar_documento,
                documento
            )
            print(f"Documento salvo: {resultado['title']}")

        print("\nImportando relações...")

        for relacao in relacoes:
            resultado = session.execute_write(
                salvar_relacao,
                relacao
            )
            print(resultado)

        print("\nImportando funcionários...")
        total_salvos = 0

        for inicio in range(0, len(funcionarios), TAMANHO_LOTE):
            lote = funcionarios[inicio:inicio + TAMANHO_LOTE]
            total = session.execute_write(
                salvar_lote_funcionarios,
                lote
            )

            total_salvos += total

            print(
                f"Lote processado: "
                f"{total_salvos}/{len(funcionarios)}"
            )

        print("\nIMPORTAÇÃO CONCLUÍDA!")
        print(f"Funcionários processados: {total_salvos}")
        print(f"Documentos processados: {len(documentos)}")
        print(f"Relações processadas: {len(relacoes)}")

finally:
    driver.close()
