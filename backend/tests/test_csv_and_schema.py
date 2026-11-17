"""
Automated tests for CSV dataset upload, type inference, dynamic table creation,
and schema inspection.
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_schema_inspection(client):
    """Verify schema inspection returns all active tables and columns."""
    res = client.get("/api/schema")
    assert res.status_code == 200
    data = res.json()
    assert "customers" in data["table_names"]
    assert "products" in data["table_names"]
    assert "orders" in data["table_names"]
    assert "order_items" in data["table_names"]
    assert "audit_logs" in data["table_names"]

    cust_table = data["tables"]["customers"]
    col_names = [c["name"] for c in cust_table["columns"]]
    assert "name" in col_names
    assert "email" in col_names
    assert "country" in col_names
    assert cust_table["row_count"] == 12

def test_csv_upload_and_schema_refresh(client):
    """Test uploading a CSV dataset, dynamic table creation, and immediate schema refresh."""
    csv_data = (
        "region,sales_rep,quarterly_quota,achieved_amount\n"
        "North,Sarah Connor,150000,165200.50\n"
        "South,John Matrix,120000,119800.00\n"
        "East,Ellen Ripley,180000,210400.75\n"
        "West,Kyle Reese,140000,135000.00\n"
    ).encode("utf-8")

    res = client.post(
        "/api/upload-csv",
        files={"file": ("sales_performance.csv", csv_data, "text/csv")},
        data={"table_name": "sales_performance"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["dataset"]["table_name"] == "sales_performance"
    assert data["dataset"]["row_count"] == 4

    # Verify column types were inferred appropriately
    col_dict = {c["name"]: c["type"] for c in data["dataset"]["columns"]}
    assert col_dict["region"] == "TEXT"
    assert col_dict["quarterly_quota"] == "INTEGER"
    assert col_dict["achieved_amount"] == "REAL"

    # Verify fresh schema includes sales_performance
    schema_res = client.get("/api/schema")
    assert "sales_performance" in schema_res.json()["table_names"]

    # Verify query on newly uploaded dataset
    q_res = client.post("/api/query", json={"question": "Show all sales_performance"})
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["row_count"] == 4
    assert "sales_performance" in q_data["sql"].lower()

def test_empty_results_handling(client):
    """Verify graceful handling when query returns 0 rows."""
    res = client.post(
        "/api/execute-sql",
        json={"sql": "SELECT * FROM customers WHERE country = 'Antarctica';"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["row_count"] == 0
    assert len(data["rows"]) == 0
    assert "0 results" in data["answer"].lower() or "0" in data["answer"]
