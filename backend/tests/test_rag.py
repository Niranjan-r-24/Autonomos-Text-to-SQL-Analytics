"""
Automated tests for RAG document intelligence and strict independence from database querying.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_rag_upload_and_retrieval(client):
    """Test uploading document, extracting text, querying, and checking citations."""
    doc_text = (
        "Enterprise Data Governance Guidelines 2024.\n"
        "All analytical databases must maintain a strict 90-day retention log.\n"
        "Production access requires multi-factor authentication and quarterly review."
    ).encode("utf-8")

    res = client.post(
        "/api/rag/upload",
        files={"file": ("governance_policy.txt", doc_text, "text/plain")}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Query RAG
    q_res = client.post("/api/rag/query", json={"query": "What is the retention log requirement?"})
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["status"] == "success"
    assert "90-day" in q_data["answer"]
    assert len(q_data["citations"]) > 0
    assert q_data["citations"][0]["source"] == "governance_policy.txt"

def test_rag_database_independence(client):
    """Ensure RAG document uploads do NOT alter database tables or SQL selection."""
    schema_res = client.get("/api/schema")
    table_names = schema_res.json()["table_names"]
    
    # Document names must NOT be in table_names
    assert "governance_policy" not in table_names
    assert "governance_policy.txt" not in table_names

    # Natural-language SQL engine must still query structured database tables
    sql_res = client.post("/api/query", json={"question": "How many customers are in the database?"})
    assert sql_res.status_code == 200
    assert "customers" in sql_res.json()["sql"]
    assert "governance" not in sql_res.json()["sql"]
