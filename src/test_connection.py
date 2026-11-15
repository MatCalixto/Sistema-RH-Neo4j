"""Explicit connection smoke test."""
from src.config import create_driver

if __name__ == "__main__":
    with create_driver() as driver:
        driver.verify_connectivity()
        print("Neo4j: OK")
