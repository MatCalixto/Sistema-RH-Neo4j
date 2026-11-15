"""Consultas de dois a quatro saltos com parâmetros e limites."""
from .config import session_options

QUERIES = {
    "Políticas do funcionário": """
        MATCH (e:Employee {employee_id: $employee_id})-[:WORKS_IN]->(dep:Department)
        MATCH (dep)-[r:ACOMPANHA|AVALIA]->(c:WorkConcept)<-[:MENTIONS]-(d:Document)
        RETURN DISTINCT e.employee_id AS funcionario, dep.name AS departamento,
               type(r) AS acao, c.name AS conceito, d.title AS documento,
               r.evidencia AS evidencia
        ORDER BY documento, conceito LIMIT $limit
    """,
    "Colegas por departamento e cargo": """
        MATCH (e:Employee {employee_id: $employee_id})-[:WORKS_IN]->(d:Department)
              <-[:WORKS_IN]-(peer:Employee)-[:HAS_ROLE]->(j:JobRole)
        WHERE peer <> e
        RETURN peer.employee_id AS funcionario, d.name AS departamento,
               j.name AS cargo, peer.attrition AS desligamento
        ORDER BY funcionario LIMIT $limit
    """,
    "Áreas ligadas ao mesmo conceito": """
        MATCH (a:Department)-[:ACOMPANHA|AVALIA]->(c:WorkConcept)
              <-[:ACOMPANHA|AVALIA]-(b:Department)
        WHERE a.name < b.name
        RETURN DISTINCT a.name AS area_1, c.name AS conceito, b.name AS area_2
        ORDER BY conceito, area_1, area_2 LIMIT $limit
    """,
    "Cargos alcançados pelas políticas": """
        MATCH (doc:Document)-[:MENTIONS]->(c:WorkConcept)
              <-[:ACOMPANHA|AVALIA]-(d:Department)
              <-[:WORKS_IN]-(e:Employee)-[:HAS_ROLE]->(j:JobRole)
        RETURN doc.title AS documento, c.name AS conceito, d.name AS departamento,
               j.name AS cargo, count(DISTINCT e) AS funcionarios
        ORDER BY funcionarios DESC, documento, conceito, departamento, cargo LIMIT $limit
    """,
}


def multi_hop(driver, name, employee_id=1, limit=100):
    if name not in QUERIES or not 1 <= limit <= 1000:
        raise ValueError("Consulta ou limite inválido.")
    with driver.session(**session_options()) as session:
        return session.run(QUERIES[name], employee_id=int(employee_id), limit=limit).data()
