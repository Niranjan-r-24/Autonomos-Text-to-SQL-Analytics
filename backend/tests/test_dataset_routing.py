"""
Automated acceptance tests for dataset routing and active table identity:
1. Upload a CSV with columns `item,total`; select it; ask "Top 5 highest total";
   generated SQL must query only the uploaded table and include ORDER BY total DESC LIMIT 5.
2. Upload/select a second CSV with a different schema; ask a question;
   SQL and results must use only the second CSV.
3. Verify no request falls back to audit_logs.
4. Verify backend errors are returned as structured error messages, never as data tables.
5. Upload-to-query table identity and rapid table switching.
6. Verify /documents and /api/documents routes succeed with 200.
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.pipeline import TextToSqlPipeline
from backend.app.services.schema_service import get_db_schema_info
from backend.app.db.seed import seed_database

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    seed_database()
    get_db_schema_info(force_refresh=True)
    yield


class TestDatasetRouting:
    def test_01_upload_csv_and_query_top_5_highest_total(self):
        """
        Acceptance test 1:
        Upload a CSV with columns item,total; select it; ask 'Top 5 highest total';
        generated SQL must query only the uploaded table and include ORDER BY total DESC LIMIT 5.
        """
        csv_content = (
            b"id,item,total\n"
            b"1,Mechanical Keyboard,150\n"
            b"2,Wireless Mouse,80\n"
            b"3,4K Monitor,450\n"
            b"4,USB-C Hub,60\n"
            b"5,Noise Cancelling Headphones,300\n"
            b"6,Ergonomic Chair,550\n"
            b"7,Desk Mat,30\n"
        )

        upload_res = client.post(
            "/api/upload",
            files={"file": ("test_sql_orders.csv", csv_content, "text/csv")}
        )
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert upload_data["success"] is True
        table_name = upload_data.get("tableName") or upload_data.get("table_name")
        assert table_name == "test_sql_orders"

        # Schema request including canonical table
        schema_res = client.get(f"/api/schema?active_table={table_name}")
        assert schema_res.status_code == 200
        assert schema_res.json()["tableName"] == "test_sql_orders"
        assert "test_sql_orders" in schema_res.json()["schema"]

        # NL-to-SQL query
        query_res = client.post(
            "/api/query",
            json={
                "query": "Top 5 highest total",
                "active_table": table_name,
                "provider": "fallback"
            }
        )
        assert query_res.status_code == 200
        data = query_res.json()
        assert data["success"] is True
        sql = data["sql"]

        # Generated SQL must query only the uploaded table
        assert "test_sql_orders" in sql
        assert "audit_logs" not in sql
        assert "sales" not in sql
        assert "products" not in sql
        assert "customers" not in sql

        # Generated SQL must include ORDER BY total DESC LIMIT 5
        sql_normalized = sql.replace('"', '').replace("`", "").lower()
        assert "order by total desc limit 5" in sql_normalized

        # Results must contain data from test_sql_orders
        assert data["row_count"] == 5
        assert len(data["rows"]) == 5
        assert "total" in data["columns"]
        assert "item" in data["columns"]
        # Highest total should be 550 (Ergonomic Chair)
        assert data["rows"][0]["total"] == 550
        assert data["rows"][0]["item"] == "Ergonomic Chair"

    def test_02_upload_second_csv_with_different_schema(self):
        """
        Acceptance test 2:
        Upload/select a second CSV with a different schema; ask a question;
        SQL and results must use only the second CSV.
        """
        second_csv = (
            b"sku,stock_qty,location\n"
            b"SKU-A1,500,Warehouse North\n"
            b"SKU-B2,1200,Warehouse South\n"
            b"SKU-C3,300,Warehouse East\n"
            b"SKU-D4,850,Warehouse West\n"
        )

        upload_res = client.post(
            "/api/upload",
            files={"file": ("warehouse_inventory.csv", second_csv, "text/csv")}
        )
        assert upload_res.status_code == 200
        table_name = upload_res.json().get("tableName") or upload_res.json().get("table_name")
        assert table_name == "warehouse_inventory"

        # Ask question tailored to second CSV
        query_res = client.post(
            "/api/query",
            json={
                "query": "Top 3 highest stock qty",
                "active_table": table_name,
                "provider": "fallback"
            }
        )
        assert query_res.status_code == 200
        data = query_res.json()
        assert data["success"] is True
        sql = data["sql"]

        # SQL must query only the second CSV
        assert "warehouse_inventory" in sql
        assert "test_sql_orders" not in sql
        assert "audit_logs" not in sql

        sql_normalized = sql.replace('"', '').replace("`", "").lower()
        assert "order by stock_qty desc limit 3" in sql_normalized
        assert data["row_count"] == 3
        assert "stock_qty" in data["columns"]
        assert data["rows"][0]["stock_qty"] == 1200
        assert data["rows"][0]["sku"] == "SKU-B2"

    def test_03_rapid_table_switching_preserves_table_identity(self):
        """
        Acceptance test 5:
        Verify rapid table switching between datasets maintains strict table identity
        and never leaks or cross-contaminates schemas.
        """
        table_1 = "test_sql_orders"
        table_2 = "warehouse_inventory"

        # Rapid alternating requests
        for _ in range(3):
            # Query table 1
            res1 = client.post(
                "/api/query",
                json={"query": "Top 2 highest total", "active_table": table_1, "provider": "fallback"}
            )
            assert res1.status_code == 200
            assert "test_sql_orders" in res1.json()["sql"]
            assert "warehouse_inventory" not in res1.json()["sql"]
            assert "total" in res1.json()["columns"]

            # Query table 2
            res2 = client.post(
                "/api/query",
                json={"query": "Top 2 highest stock qty", "active_table": table_2, "provider": "fallback"}
            )
            assert res2.status_code == 200
            assert "warehouse_inventory" in res2.json()["sql"]
            assert "test_sql_orders" not in res2.json()["sql"]
            assert "stock_qty" in res2.json()["columns"]

    def test_04_no_request_falls_back_to_audit_logs(self):
        """
        Acceptance test 3:
        Verify no business question falls back to audit_logs, even with ambiguous queries.
        """
        ambiguous_queries = [
            "Top 5 highest score",
            "Show records with maximum value",
            "List items by performance",
            "What is the average metric?",
        ]

        for q in ambiguous_queries:
            res = client.post(
                "/api/query",
                json={"query": q, "provider": "fallback"}
            )
            if res.status_code == 200:
                data = res.json()
                sql = (data.get("sql") or "").lower()
                assert "audit_logs" not in sql, f"Query '{q}' fell back to audit_logs!"
                # Audit log columns should never be returned
                for col in ["user_id", "ip_address", "action"]:
                    assert col not in data.get("columns", [])

    def test_05_structured_errors_not_data_tables(self):
        """
        Acceptance test 4:
        Verify backend errors are returned as structured error responses, never as a data table.
        """
        # 1. Non-existent active table request -> 404 structured error
        res_404 = client.post(
            "/api/query",
            json={"query": "Top 5 highest total", "active_table": "nonexistent_table_xyz", "provider": "fallback"}
        )
        assert res_404.status_code == 404
        data_404 = res_404.json()
        assert "detail" in data_404
        detail = data_404["detail"]
        assert "requested_table" in detail
        assert detail["requested_table"] == "nonexistent_table_xyz"
        assert "available_tables" in detail
        assert isinstance(detail["available_tables"], list)

        # 2. Schema check for non-existent table -> 404
        res_schema_404 = client.get("/api/schema?active_table=nonexistent_table_xyz")
        assert res_schema_404.status_code == 404

        # 3. Direct SQL execution violating active table -> 400
        res_exec_bad = client.post(
            "/api/execute-sql",
            json={"sql": "SELECT * FROM products LIMIT 5;", "active_table": "test_sql_orders"}
        )
        assert res_exec_bad.status_code == 400
        detail_exec = res_exec_bad.json()["detail"]
        assert "must reference the active table" in detail_exec["message"]
        assert detail_exec["requested_table"] == "test_sql_orders"

    def test_06_documents_route_returns_200(self):
        """
        Acceptance test:
        Verify /documents and /api/documents routes return HTTP 200.
        """
        r1 = client.get("/documents")
        assert r1.status_code == 200
        assert r1.json()["success"] is True
        assert "documents" in r1.json()

        r2 = client.get("/api/documents")
        assert r2.status_code == 200
        assert r2.json()["success"] is True
        assert "documents" in r2.json()

    def test_07_llm_schema_isolation_rejects_unpermitted_table(self, monkeypatch):
        """
        Acceptance test:
        Verify that LLM prompt is constructed with selected table schema only,
        and any LLM hallucination targeting another table (such as audit_logs) is rejected.
        """
        pipeline = TextToSqlPipeline(provider="gemini", api_key="dummy-key")
        # Simulate LLM hallucinating audit_logs when active_table is test_sql_orders
        monkeypatch.setattr(
            pipeline.generator,
            "_generate_with_llm",
            lambda *_args, **_kwargs: ('SELECT * FROM "audit_logs" LIMIT 10;', "Wrong table"),
        )

        schema = get_db_schema_info()
        sql, explanation, generated_by = pipeline.generator.generate(
            "Top 5 highest total", schema, active_table="test_sql_orders"
        )
        # Hallucination must be rejected and replaced by deterministic query for test_sql_orders
        assert generated_by == "Deterministic Analytics Engine"
        assert "test_sql_orders" in sql
        assert "audit_logs" not in sql
