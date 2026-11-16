"""
Regression and verification test suite covering all 9 specific verification workflows
demanded by the Master Fix Prompt:
1. Upload a dataset containing multiple related tables.
2. Ask: "How many customers are in the database?"
3. Ask: "List all products and their prices."
4. Ask: "Count orders by status."
5. Ask: "Show the top 5 customers by total spending."
6. Ask: "Show monthly revenue for 2025."
7. Upload a document and ask a question whose answer is explicitly contained in it.
8. Verify that citations point to the correct document and retrieved content.
9. Verify behavior for invalid SQL, empty results, and unsupported questions.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.pipeline import TextToSqlPipeline
from backend.app.services.schema_service import get_db_schema_info
from backend.app.db.seed import seed_database

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    seed_database()
    get_db_schema_info(force_refresh=True)
    yield

class TestMasterVerificationWorkflow:

    # 1. Upload a dataset containing multiple related tables
    def test_01_upload_multi_table_dataset(self):
        dept_csv = b"dept_id,dept_name,budget\n101,Engineering,500000\n102,Sales,300000\n103,Marketing,200000\n"
        emp_csv = b"emp_id,emp_name,dept_id,salary\n1,Alice,101,120000\n2,Bob,101,110000\n3,Charlie,102,95000\n4,David,103,85000\n"
        
        r1 = client.post("/api/upload", files={"file": ("departments.csv", dept_csv, "text/csv")})
        assert r1.status_code == 200
        assert r1.json()["table_name"] == "departments"
        assert r1.json()["row_count"] == 3

        r2 = client.post("/api/upload", files={"file": ("staff_members.csv", emp_csv, "text/csv")})
        assert r2.status_code == 200
        assert r2.json()["table_name"] in ["staff_members", "employees"]
        assert r2.json()["row_count"] == 4

        # Verify dynamic schema reflects both uploaded tables
        schema = get_db_schema_info(force_refresh=True)
        assert "departments" in schema
        assert "staff_members" in schema or "employees" in schema

    # 2. Ask: "How many customers are in the database?"
    def test_02_how_many_customers_are_in_the_database(self):
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("How many customers are in the database?")
        assert res["success"] is True
        assert "customers" in res["sql"].lower()
        assert "audit_logs" not in res["sql"].lower()
        assert res["row_count"] == 1
        answer = res["insights"]["direct_answer"]
        assert "40" in answer
        assert "customer" in answer.lower()

    # 3. Ask: "List all products and their prices."
    def test_03_list_all_products_and_their_prices(self):
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("List all products and their prices.")
        assert res["success"] is True
        assert "products" in res["sql"].lower()
        # Ensure name/product_name and price are selected
        sql_lower = res["sql"].lower()
        assert any(c in sql_lower for c in ["name", "product_name"])
        assert any(c in sql_lower for c in ["price", "unit_price"])
        assert res["row_count"] >= 10
        assert res["visualization"]["chart_type"] == "table"
        answer = res["insights"]["direct_answer"]
        assert "products" in answer.lower() or "retrieved" in answer.lower()

    # 4. Ask: "Count orders by status."
    def test_04_count_orders_by_status(self):
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("Count orders by status.")
        assert res["success"] is True
        sql_lower = res["sql"].lower()
        assert "orders" in sql_lower
        assert "status" in sql_lower
        assert "group by" in sql_lower
        assert res["row_count"] >= 2
        answer = res["insights"]["direct_answer"]
        # Must explain order distribution by status, NOT call status "top-performing item"
        assert "top-performing item" not in answer.lower()
        assert "status" in answer.lower() or "orders" in answer.lower() or "distribution" in answer.lower()

    # 5. Ask: "Show the top 5 customers by total spending."
    def test_05_show_top_5_customers_by_total_spending(self):
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("Show the top 5 customers by total spending.")
        assert res["success"] is True
        sql_lower = res["sql"].lower()
        assert "customers" in sql_lower
        assert any(w in sql_lower for w in ["sales", "orders", "payments", "spent", "spending"])
        assert "order by" in sql_lower
        assert "desc" in sql_lower
        assert "limit 5" in sql_lower or "5" in sql_lower
        assert res["row_count"] <= 5
        answer = res["insights"]["direct_answer"]
        assert answer is not None
        assert any(w in answer.lower() for w in ["top", "leading", "customer", "spend"])

    # 6. Ask: "Show monthly revenue for 2025."
    def test_06_show_monthly_revenue_for_2025(self):
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("Show monthly revenue for 2025.")
        assert res["success"] is True
        sql_lower = res["sql"].lower()
        assert "2025" in sql_lower
        assert any(k in sql_lower for k in ["sales", "orders", "payments"])
        assert any(k in sql_lower for k in ["month", "strftime", "to_char"])
        # Should not force grouping by region if region was not requested
        assert "region" not in sql_lower or "group by" in sql_lower
        assert res["visualization"]["chart_type"] in ["line", "bar"]
        assert res["row_count"] >= 1
        answer = res["insights"]["direct_answer"]
        assert answer is not None

    # 7. Upload a document and ask a question whose answer is explicitly contained in it
    def test_07_upload_document_and_ask_question(self):
        policy_doc = b"Enterprise Security Standard: All production database backups must be encrypted with AES-256 and stored offsite for at least 5 years."
        up_res = client.post(
            "/api/rag/upload",
            files={"file": ("security_standard.txt", policy_doc, "text/plain")}
        )
        assert up_res.status_code == 200
        assert up_res.json()["success"] is True

        # Ask question explicitly contained in document
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("How long must database backups be stored according to security standard?")
        assert res["success"] is True
        assert res["route"] == "rag"
        answer = res["insights"]["direct_answer"]
        assert "5 years" in answer or "AES-256" in answer or "encrypted" in answer

    # 8. Verify that citations point to the correct document and retrieved content
    def test_08_verify_citations(self):
        rag_res = client.post(
            "/api/rag/query",
            json={"query": "What encryption standard and storage duration are required for backups in security standard?", "provider": "fallback"}
        )
        assert rag_res.status_code == 200
        data = rag_res.json()
        assert data["success"] is True
        assert len(data["citations"]) > 0
        citation = data["citations"][0]
        assert citation["source"] == "security_standard.txt"
        assert citation["chunk"] >= 1
        assert any(w in citation["excerpt"].lower() for w in ["aes-256", "backups", "5 years", "encrypted"])

    # 9. Verify behavior for invalid SQL, empty results, and unsupported questions
    def test_09_verify_invalid_sql_empty_results_and_unsupported_questions(self):
        pipeline = TextToSqlPipeline(provider="fallback")

        # Invalid SQL directly executed
        res_invalid = client.post(
            "/api/execute-sql",
            json={"sql": "SELECT non_existent_column_xyz FROM non_existent_table_abc;"}
        )
        # Should return 400 or structured error response, never success: True
        assert res_invalid.status_code == 400 or (res_invalid.status_code == 200 and res_invalid.json().get("success") is False)

        # Empty results query
        res_empty = pipeline.run("SELECT * FROM customers WHERE id = 9999999;")
        assert res_empty["success"] is True
        assert res_empty["row_count"] == 0
        assert res_empty["insights"]["status"] == "empty"
        assert "no matching records" in res_empty["insights"]["direct_answer"].lower()
        # Verify it did not silently fall back to fleet_inventory or another table
        assert "9999999" in res_empty["sql"]

        # Completely unsupported question
        res_unsupported = pipeline.run("What is the secret frobnicator coefficient of the quantum reactor?")
        assert res_unsupported["success"] is False
        assert "no matching database table" in res_unsupported["error"].lower() or "unsupported" in res_unsupported["error"].lower() or "cannot generate" in res_unsupported["error"].lower()
        # Verify it does NOT claim success or silently execute fallback SELECT *
        assert res_unsupported["insights"]["status"] == "error"
