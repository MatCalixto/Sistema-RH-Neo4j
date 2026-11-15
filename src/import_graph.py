"""Importação idempotente: python -m src.import_graph."""
import math
import pandas as pd
from .config import CSV_FILE, DOCUMENTS, EMBEDDING_DIMENSIONS, create_driver, load_encoder, session_options
from .extraction import extract_documents
from .schema import ensure_schema

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



def preparar_documentos(modelo):
    files = sorted(DOCUMENTS.glob("*.txt"))
    if not files:
        raise FileNotFoundError("Nenhum documento .txt encontrado.")
    documents = []
    for file in files:
        content = file.read_text(encoding="utf-8")
        embedding = modelo.encode(content, normalize_embeddings=True).tolist()
        if len(embedding) != EMBEDDING_DIMENSIONS or not all(math.isfinite(x) for x in embedding):
            raise ValueError("Embedding inválido ou dimensão incompatível.")
        documents.append({"title": file.name, "content": content, "embedding": embedding})
    return documents


def salvar_lote_funcionarios(tx, funcionarios):
    return tx.run("""
        UNWIND $funcionarios AS f
        MERGE (e:Employee {employee_id: f.employee_id}) SET e += f.propriedades
        WITH e, f
        OPTIONAL MATCH (e)-[old:WORKS_IN|HAS_ROLE|EDUCATED_IN]->()
        DELETE old
        WITH DISTINCT e, f
        MERGE (d:Department {name: f.department})
        MERGE (j:JobRole {name: f.job_role})
        MERGE (ef:EducationField {name: f.education_field})
        MERGE (e)-[:WORKS_IN]->(d)
        MERGE (e)-[:HAS_ROLE]->(j)
        MERGE (e)-[:EDUCATED_IN]->(ef)
        RETURN count(e) AS total
    """, funcionarios=funcionarios).single()["total"]


def salvar_relacao(tx, relacao):
    kind, label = relacao["relacao"], relacao["origem_tipo"]
    if kind not in {"ACOMPANHA", "AVALIA"} or label not in {"Department", "Role"}:
        raise ValueError("Tipo de entidade ou relação inválido.")
    tx.run(f"""
        MERGE (o:{label} {{name: $origem}})
        MERGE (c:WorkConcept {{name: $destino}})
        MATCH (d:Document {{title: $documento}})
        MERGE (o)-[r:{kind} {{documento: $documento, evidencia: $evidencia}}]->(c)
        SET r.extracted_by = 'hr_extractor_v1'
        MERGE (d)-[:MENTIONS]->(o)
        MERGE (d)-[:MENTIONS]->(c)
    """, **relacao).consume()


def salvar_documento(tx, documento, extraction):
    tx.run("""
        MERGE (d:Document {title: $title})
        SET d.content = $content, d.embedding = $embedding
        WITH d OPTIONAL MATCH (d)-[m:MENTIONS]->() DELETE m
    """, **documento).consume()
    # Substitui apenas relações extraídas desta fonte, na mesma transação.
    tx.run("""
        MATCH ()-[r:ACOMPANHA|AVALIA]->()
        WHERE r.documento = $title DELETE r
    """, title=documento["title"]).consume()
    for entity in extraction["entidades"]:
        label = entity["tipo"]
        if label not in {"Department", "Role", "WorkConcept"}:
            raise ValueError("Tipo de entidade inválido.")
        tx.run(f"""
            MATCH (d:Document {{title: $title}})
            MERGE (n:{label} {{name: $name}})
            MERGE (d)-[:MENTIONS]->(n)
        """, title=documento["title"], name=entity["nome"]).consume()
    for relation in extraction["relacoes"]:
        salvar_relacao(tx, relation)


def importar(driver=None, modelo=None):
    # Valida e prepara todas as entradas antes de alterar o banco.
    df = pd.read_csv(CSV_FILE)
    required = set(colunas_funcionario) | {"Department", "JobRole", "EducationField"}
    if required - set(df.columns):
        raise ValueError(f"Colunas ausentes: {sorted(required - set(df.columns))}")
    if df[list(required)].isna().any().any() or df.EmployeeNumber.duplicated().any():
        raise ValueError("CSV com campos ausentes ou identificadores duplicados.")
    funcionarios = preparar_funcionarios(df)
    extraction = extract_documents()
    documents = preparar_documentos(modelo if modelo is not None else load_encoder())
    own_driver = driver is None
    driver = driver if driver is not None else create_driver()
    try:
        driver.verify_connectivity()
        with driver.session(**session_options()) as session:
            ensure_schema(session)
            for start in range(0, len(funcionarios), 100):
                session.execute_write(salvar_lote_funcionarios, funcionarios[start:start + 100])
            for document in documents:
                session.execute_write(salvar_documento, document, extraction[document["title"]])
        return {"funcionarios": len(funcionarios), "documentos": len(documents),
                "entidades": sum(len(x["entidades"]) for x in extraction.values()),
                "relacoes": sum(len(x["relacoes"]) for x in extraction.values())}
    finally:
        if own_driver:
            driver.close()


if __name__ == "__main__":
    print(importar())
