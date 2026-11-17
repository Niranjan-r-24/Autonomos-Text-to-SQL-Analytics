"""
End-to-end production persistence and dataset isolation test suite.
Validates that:
1. Uploaded datasets and metadata are committed to the shared persistent database (`datasets` table).
2. A separate client / new browser session immediately lists and queries the uploaded dataset.
3. Natural-language Text-to-SQL specifically targets the requested dataset and never falls back to `audit_logs`.
4. Querying unavailable tables is rejected with HTTP 422 structured error.
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def generate_payments_csv() -> bytes:
    """Generate 30 rows of payments data with payment_id, order_id, payment_method, payment_status, amount."""
    lines = ["payment_id,order_id,payment_method,payment_status,amount"]
    methods = ["credit_card", "paypal", "wire_transfer", "apple_pay", "stripe"]
    statuses = ["completed", "completed", "completed", "pending", "refunded"]
    
    for i in range(1, 31):
        order_id = 1000 + i
        method = methods[(i - 1) % len(methods)]
        status = statuses[(i - 1) % len(statuses)]
        amount = round(49.99 + (i * 15.50), 2)
        lines.append(f"{i},{order_id},{method},{status},{amount}")
    
    return "\n".join(lines).encode("utf-8")

def test_production_payments_e2e_persistence():
    """
    Production E2E Test:
    - Upload payments.csv (30 rows, 5 columns) in Session 1.
    - Make a separate request in a new browser session (Session 2) to list tables.
    - Assert 'payments' appears in table list and persistent datasets registry.
    - Query 'Show all payments'.
    - Assert SQL references only 'payments'.
    - Assert results contain payment_id, order_id, payment_method, payment_status, amount.
    - Assert SQL never contains 'audit_logs'.
    - Assert unavailable dataset table queries are rejected with 422.
    """
    # ----------------- Session 1: Upload payments.csv -----------------
    session1 = TestClient(app)
    csv_bytes = generate_payments_csv()

    upload_res = session1.post(
        "/api/upload",
        files={"file": ("payments.csv", csv_bytes, "text/csv")},
        data={"table_name": "payments"}
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    assert upload_data["tableName"] == "payments"
    assert upload_data["row_count"] == 30
    assert "datasetId" in upload_data
    dataset_id = upload_data["datasetId"]

    # ----------------- Session 2: New Browser Session / Client -----------------
    session2 = TestClient(app)

    # 1. Verify datasets endpoint returns persistent metadata
    datasets_res = session2.get("/api/datasets")
    assert datasets_res.status_code == 200
    datasets_list = datasets_res.json()["datasets"]
    payments_ds = next((d for d in datasets_list if d["table_name"] == "payments"), None)
    assert payments_ds is not None, "payments table MUST be present in persistent datasets registry"
    assert payments_ds["row_count"] == 30
    assert "payments.csv" in payments_ds["source_file_name"]

    # 2. Verify schema endpoint lists payments table
    schema_res = session2.get("/api/schema?refresh=true")
    assert schema_res.status_code == 200
    schema_data = schema_res.json()
    assert "payments" in schema_data["table_names"], "payments MUST be in schema.table_names"
    assert "payments" in schema_data["tables"], "payments MUST be in schema.tables"
    payments_table = schema_data["tables"]["payments"]
    assert payments_table["row_count"] == 30

    col_names = [c["name"].lower() for c in payments_table["columns"]]
    for req_col in ["payment_id", "order_id", "payment_method", "payment_status", "amount"]:
        assert req_col in col_names, f"Expected column '{req_col}' in payments table schema"

    # 3. Query: "Show all payments"
    query_res = session2.post("/api/query", json={
        "question": "Show all payments",
        "tableName": "payments",
        "datasetId": dataset_id
    })
    assert query_res.status_code == 200, f"Query failed: {query_res.text}"
    query_data = query_res.json()
    assert query_data["status"] == "success"

    sql = query_data["sql"].lower()
    # Assert SQL references ONLY payments
    assert "payments" in sql, "Generated SQL must reference 'payments'"
    assert "audit_logs" not in sql, "Generated SQL must NEVER reference 'audit_logs'"
    assert query_data["row_count"] == 30

    # Assert returned rows contain all 5 required columns
    first_row = query_data["rows"][0]
    row_keys = [k.lower() for k in first_row.keys()]
    for req_col in ["payment_id", "order_id", "payment_method", "payment_status", "amount"]:
        assert req_col in row_keys, f"Row missing required column '{req_col}'"
    assert first_row["payment_id"] == 1
    assert first_row["order_id"] == 1001

    # 4. Query without explicit tableName: Intent must still resolve to 'payments'
    implicit_query_res = session2.post("/api/query", json={
        "question": "Show all payments"
    })
    assert implicit_query_res.status_code == 200
    imp_data = implicit_query_res.json()
    assert imp_data["status"] == "success"
    assert "payments" in imp_data["sql"].lower()
    assert "audit_logs" not in imp_data["sql"].lower()

    # 5. Unavailable dataset table must be rejected with 422
    unavail_res = session2.post("/api/query", json={
        "question": "Show all unlinked_ledger",
        "tableName": "unlinked_ledger"
    })
    assert unavail_res.status_code == 422
    assert "Dataset table unlinked_ledger is unavailable; no query executed." in unavail_res.json()["detail"]
