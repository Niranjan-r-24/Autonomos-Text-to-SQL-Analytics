"""
Automated tests for required benchmark queries on real SQLite database.
Validates generated SQL and actual returned data.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.seed import seed_benchmark_data

@pytest.fixture(scope="module", autouse=True)
def setup_benchmark_database():
    """Ensure benchmark dataset is seeded and fresh."""
    seed_benchmark_data(force=True)

@pytest.fixture
def client():
    return TestClient(app)

def test_q1_customer_count(client):
    """Q1: How many customers are in the database? -> Exactly 12."""
    res = client.post("/api/query", json={"question": "How many customers are in the database?"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "customers" in data["sql"].lower()
    assert "audit_logs" not in data["sql"].lower()
    assert len(data["rows"]) == 1
    val = list(data["rows"][0].values())[0]
    assert val == 12

def test_q2_first_10_products(client):
    """Q2: Show the first 10 products. -> Exactly 8 rows (since there are 8 products)."""
    res = client.post("/api/query", json={"question": "Show the first 10 products."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "products" in data["sql"].lower()
    assert "audit_logs" not in data["sql"].lower()
    assert data["row_count"] == 8
    assert len(data["rows"]) == 8

def test_q3_show_all_orders(client):
    """Q3: Show all orders. -> Exactly 30 rows."""
    res = client.post("/api/query", json={"question": "Show all orders."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "orders" in data["sql"].lower()
    assert "audit_logs" not in data["sql"].lower()
    assert data["row_count"] == 30
    assert len(data["rows"]) == 30

def test_q4_count_orders_by_status(client):
    """Q4: Count orders by status. -> Correct grouped counts summing to 30."""
    res = client.post("/api/query", json={"question": "Count orders by status."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "orders" in data["sql"].lower()
    assert "group by" in data["sql"].lower()
    assert "status" in data["columns"]
    rows = data["rows"]
    total = sum(r["count"] for r in rows)
    assert total == 30
    status_map = {r["status"]: r["count"] for r in rows}
    assert "completed" in status_map
    assert "shipped" in status_map
    assert "pending" in status_map
    assert "cancelled" in status_map

def test_q5_highest_revenue_product(client):
    """Q5: Which product generated the highest revenue? -> Developer Workstation."""
    res = client.post("/api/query", json={"question": "Which product generated the highest revenue?"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "products" in data["sql"].lower()
    assert len(data["rows"]) == 1
    top_product = data["rows"][0]
    assert top_product["name"] == "Developer Workstation"
    assert top_product["total_revenue"] == 41600.0

def test_q6_show_monthly_revenue(client):
    """Q6: Show monthly revenue. -> Correct chronological aggregation."""
    res = client.post("/api/query", json={"question": "Show monthly revenue."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["rows"]) > 0
    months = [r["month"] for r in data["rows"]]
    # Verify chronological ordering
    assert months == sorted(months)
    assert "2024-01" in months

def test_q7_show_audit_logs_only_when_requested(client):
    """Q7: Show audit logs. -> audit_logs queried ONLY when requested."""
    res = client.post("/api/query", json={"question": "Show audit logs."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "audit_logs" in data["sql"].lower()
    assert data["row_count"] == 10

def test_q8_nonexistent_table_handling(client):
    """Q8: Ask about a nonexistent table. -> Clear error or clarification."""
    res = client.post("/api/query", json={"question": "Show all extraterrestrial_spaceships"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "error"
    assert "not found" in data["error"].lower() or "no matching table" in data["error"].lower()
