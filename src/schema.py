"""Schema compatível com Neo4j 5.15+, sem APOC ou GDS."""
from .config import EMBEDDING_DIMENSIONS


def ensure_schema(session):
    for label, prop in [("Employee", "employee_id"), ("Department", "name"),
                        ("JobRole", "name"), ("Role", "name"),
                        ("EducationField", "name"), ("WorkConcept", "name"),
                        ("Document", "title")]:
        session.run(f"CREATE CONSTRAINT {label.lower()}_{prop}_unique IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE").consume()
    session.run("""
        CREATE FULLTEXT INDEX document_fulltext IF NOT EXISTS
        FOR (d:Document) ON EACH [d.title, d.content]
        OPTIONS {indexConfig: {`fulltext.analyzer`: 'portuguese'}}
    """).consume()
    session.run(f"""
        CREATE VECTOR INDEX document_vector IF NOT EXISTS
        FOR (d:Document) ON (d.embedding)
        OPTIONS {{indexConfig: {{`vector.dimensions`: {EMBEDDING_DIMENSIONS},
                                  `vector.similarity_function`: 'cosine'}}}}
    """).consume()
    session.run("CALL db.awaitIndexes(120)").consume()
