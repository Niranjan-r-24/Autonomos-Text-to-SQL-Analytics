"""
Automated tests for SQL safety and execution guardrails.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_safe_select_allowed(client):
    """Safe read-only SELECT queries should execute without issue."""
    res = client.post("/api/execute-sql", json={"sql": "SELECT id, name FROM customers LIMIT 5;"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["row_count"] == 5

def test_safe_cte_allowed(client):
    """Common Table Expressions (WITH ... SELECT) should be allowed."""
    cte_sql = """
    WITH high_orders AS (
        SELECT customer_id, SUM(total_amount) as spent
        FROM orders
        GROUP BY customer_id
    )
    SELECT * FROM high_orders ORDER BY spent DESC LIMIT 3;
    """
    res = client.post("/api/execute-sql", json={"sql": cte_sql})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["row_count"] == 3

@pytest.mark.parametrize("bad_sql", [
    "DROP TABLE customers;",
    "DELETE FROM orders WHERE id = 1;",
    "UPDATE products SET price = 0;",
    "INSERT INTO customers (id, name, email, country, signup_date) VALUES (99, 'Hacker', 'h@h.com', 'US', '2024-01-01');",
    "ALTER TABLE customers ADD COLUMN secret TEXT;",
    "TRUNCATE TABLE orders;",
    "CREATE TABLE backdoor (id INT);",
])
def test_destructive_operations_blocked(client, bad_sql):
    """Destructive SQL mutations must be blocked before execution."""
    res = client.post("/api/execute-sql", json={"sql": bad_sql})
    assert res.status_code == 400
    assert "blocked" in res.json()["detail"].lower() or "prohibited" in res.json()["detail"].lower() or "only read-only" in res.json()["detail"].lower()

def test_multi_statement_injection_blocked(client):
    """Multi-statement queries separated by semicolons must be blocked."""
    injection_sql = "SELECT * FROM customers; DROP TABLE orders;"
    res = client.post("/api/execute-sql", json={"sql": injection_sql})
    assert res.status_code == 400
    assert "multi-statement" in res.json()["detail"].lower()

def test_nonexistent_table_reference_blocked(client):
    """Manual SQL referencing a non-existent table must be rejected with clean error."""
    res = client.post("/api/execute-sql", json={"sql": "SELECT * FROM non_existent_financial_data;"})
    assert res.status_code == 400
    assert "does not exist in active database schema" in res.json()["detail"]
