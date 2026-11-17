"""
Automated acceptance tests for dataset routing and active table identity:
1. Upload a CSV with columns `item,total`; select it; ask "Top 5 highest total";
   generated SQL must query only the uploaded table, include ORDER BY total DESC LIMIT 5,
   return Laptop and 1200, and contain no audit_logs.
2. Select another table immediately afterward; the next request must use only the new table,
   never stale state.
3. Verify missing tableName returns a clear 400 error and does not execute any query.
4. Verify generated SQL referencing a non-selected table is blocked with visible error.
5. Verify no request falls back to audit_logs.
6. Verify backend errors are returned as structured error messages, never as data tables.
7. Verify /documents and /api/documents routes succeed with 200.
"""
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
        Selecting test_sql_orders and asking 'Top 5 highest total' executes against
        test_sql_orders, returns 'Laptop' and 1200, and SQL contains no audit_logs.
        """
        csv_content = (
            b"id,item,total\n"
            b"1,Laptop,1200\n"
            b"2,Mechanical Keyboard,150\n"
            b"3,Wireless Mouse,80\n"
            b"4,4K Monitor,450\n"
            b"5,USB-C Hub,60\n"
            b"6,Noise Cancelling Headphones,300\n"
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

        # NL-to-SQL query sending canonical tableName and question
        query_res = client.post(
            "/api/query",
            json={
                "question": "Top 5 highest total",
                "tableName": table_name,
                "schema": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "item", "type": "TEXT"},
                    {"name": "total", "type": "REAL"}
                ],
                "provider": "fallback"
            }
        )
        assert query_res.status_code == 200
        data = query_res.json()
        assert data["success"] is True
        sql = data["sql"]

        # Generated SQL must query only the uploaded table and never audit_logs
        assert "test_sql_orders" in sql
        assert "audit_logs" not in sql
        assert "sales" not in sql
        assert "products" not in sql
        assert "customers" not in sql

        # Generated SQL must include ORDER BY total DESC LIMIT 5
        sql_normalized = sql.replace('"', '').replace("`", "").lower()
        assert "order by total desc limit 5" in sql_normalized

        # Results must return Laptop and 1200 as #1 row
        assert data["row_count"] == 5
        assert len(data["rows"]) == 5
        assert "total" in data["columns"]
        assert "item" in data["columns"]
        assert data["rows"][0]["total"] == 1200
        assert data["rows"][0]["item"] == "Laptop"

    def test_02_select_another_table_immediately_uses_only_new_table(self):
        """
        Acceptance test 2:
        Select another table immediately afterward; the next request must use
        only the new table, never stale state.
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

        # Ask question tailored to second CSV immediately
        query_res = client.post(
            "/api/query",
            json={
                "question": "Top 3 highest stock qty",
                "tableName": table_name,
                "provider": "fallback"
            }
        )
        assert query_res.status_code == 200
        data = query_res.json()
        assert data["success"] is True
        sql = data["sql"]

        # SQL and results must query only the second CSV, no stale state from test_sql_orders
        assert "warehouse_inventory" in sql
        assert "test_sql_orders" not in sql
        assert "audit_logs" not in sql

        sql_normalized = sql.replace('"', '').replace("`", "").lower()
        assert "order by stock_qty desc limit 3" in sql_normalized
        assert data["row_count"] == 3
        assert "stock_qty" in data["columns"]
        assert data["rows"][0]["stock_qty"] == 1200
        assert data["rows"][0]["sku"] == "SKU-B2"

    def test_03_missing_tablename_returns_400_error(self):
        """
        Acceptance test 3:
        Test missing tableName returns a clear 400 error and does not execute any query.
        """
        res = client.post(
            "/api/query",
            json={"question": "Top 5 highest total", "provider": "fallback"}
        )
        assert res.status_code == 400
        data = res.json()
        assert "detail" in data
        assert data["detail"]["error"] == "Missing tableName"
        assert "A canonical tableName must be specified" in data["detail"]["message"]
        assert "available_tables" in data["detail"]

    def test_04_generated_sql_referencing_non_selected_table_is_blocked(self, monkeypatch):
        """
        Acceptance test 4:
        Test generated SQL referencing a non-selected table is blocked.
        Returns a visible error with the requested and referenced table names.
        """
        pipeline = TextToSqlPipeline(provider="gemini", api_key="dummy-key")
        # Simulate generator producing SQL referencing customers when active table is test_sql_orders
        monkeypatch.setattr(
            pipeline.generator,
            "generate",
            lambda *_args, **_kwargs: ('SELECT * FROM "customers" LIMIT 5;', "Query customers", "Gemini 1.5 Flash"),
        )

        res = pipeline.run("Top 5 customers", active_table="test_sql_orders")
        assert res["success"] is False
        assert "Execution blocked" in res["error"] or "outside the requested table" in res["error"]
        assert res["requested_table"] == "test_sql_orders"
        assert "customers" in res["referenced_tables"]

    def test_05_ambiguous_queries_never_fall_back_to_audit_logs(self):
        """
        Acceptance test 5:
        Verify no request falls back to audit_logs, even with ambiguous queries on an active table.
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
                json={"question": q, "tableName": "test_sql_orders", "provider": "fallback"}
            )
            assert res.status_code == 200
            data = res.json()
            sql = (data.get("sql") or "").lower()
            assert "audit_logs" not in sql, f"Query '{q}' fell back to audit_logs!"
            for col in ["user_id", "ip_address", "action"]:
                assert col not in data.get("columns", [])

    def test_06_structured_errors_not_data_tables(self):
        """
        Acceptance test 6:
        Verify backend errors are returned as structured error responses, never as a data table.
        """
        # 1. Non-existent active table request -> 404 structured error
        res_404 = client.post(
            "/api/query",
            json={"question": "Top 5 highest total", "tableName": "nonexistent_table_xyz", "provider": "fallback"}
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
        res_schema_404 = client.get("/api/schema?tableName=nonexistent_table_xyz")
        assert res_schema_404.status_code == 404

        # 3. Direct SQL execution violating active table -> 400
        res_exec_bad = client.post(
            "/api/execute-sql",
            json={"sql": "SELECT * FROM products LIMIT 5;", "tableName": "test_sql_orders"}
        )
        assert res_exec_bad.status_code == 400
        detail_exec = res_exec_bad.json()["detail"]
        assert "must reference the active table" in detail_exec["message"]
        assert detail_exec["requested_table"] == "test_sql_orders"

    def test_07_documents_route_returns_200(self):
        """
        Acceptance test 7:
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

    def test_08_rapid_alternating_queries_preserve_table_identity(self):
        """
        Acceptance test 8:
        Verify rapid table switching between datasets maintains strict table identity.
        """
        table_1 = "test_sql_orders"
        table_2 = "warehouse_inventory"

        for _ in range(3):
            res1 = client.post(
                "/api/query",
                json={"question": "Top 2 highest total", "tableName": table_1, "provider": "fallback"}
            )
            assert res1.status_code == 200
            assert "test_sql_orders" in res1.json()["sql"]
            assert "warehouse_inventory" not in res1.json()["sql"]

            res2 = client.post(
                "/api/query",
                json={"question": "Top 2 highest stock qty", "tableName": table_2, "provider": "fallback"}
            )
            assert res2.status_code == 200
            assert "warehouse_inventory" in res2.json()["sql"]
            assert "test_sql_orders" not in res2.json()["sql"]

    def test_09_upload_payments_csv_and_query_highest_amount_and_browse(self):
        """
        Acceptance test 9:
        Upload payments.csv and verify that queries like 'Top 5 highest amount'
        and 'Show first 10 rows from payments' strictly target payments,
        never fall back to audit_logs or multi-table sales joins, and return DatasetContext.
        """
        payments_csv = (
            b"payment_id,order_id,amount,payment_method,payment_status\n"
            b"PAY-001,101,150.50,Credit Card,Completed\n"
            b"PAY-002,102,999.99,Bank Wire,Completed\n"
            b"PAY-003,103,45.00,PayPal,Completed\n"
            b"PAY-004,104,1250.00,Credit Card,Completed\n"
            b"PAY-005,105,320.75,Debit Card,Pending\n"
            b"PAY-006,106,75.25,Apple Pay,Completed\n"
        )

        upload_res = client.post(
            "/api/upload",
            files={"file": ("payments.csv", payments_csv, "text/csv")}
        )
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        assert upload_data["success"] is True
        assert upload_data["tableName"] == "payments"
        assert upload_data["sourceFileName"] == "payments.csv"
        assert upload_data["rowCount"] == 6
        assert "datasetContext" in upload_data
        assert upload_data["datasetContext"]["tableName"] == "payments"

        # 1. Ask 'Top 5 highest amount'
        query_res = client.post(
            "/api/query",
            json={
                "question": "Top 5 highest amount",
                "tableName": "payments",
                "datasetContext": upload_data["datasetContext"],
                "provider": "fallback"
            }
        )
        assert query_res.status_code == 200
        data = query_res.json()
        assert data["success"] is True
        sql = data["sql"]

        assert "payments" in sql
        assert "audit_logs" not in sql
        assert "sales" not in sql
        assert "order_items" not in sql

        sql_normalized = sql.replace('"', '').replace("`", "").lower()
        assert "order by amount desc limit 5" in sql_normalized
        assert data["row_count"] == 5
        assert data["rows"][0]["amount"] == 1250.00
        assert data["rows"][1]["amount"] == 999.99

        # 2. Ask 'Show first 10 rows from payments'
        browse_res = client.post(
            "/api/query",
            json={
                "question": "Show first 10 rows from payments",
                "tableName": "payments",
                "datasetContext": upload_data["datasetContext"],
                "provider": "fallback"
            }
        )
        assert browse_res.status_code == 200
        b_data = browse_res.json()
        assert b_data["success"] is True
        b_sql = b_data["sql"]
        assert "payments" in b_sql
        assert "audit_logs" not in b_sql

    def test_10_dataset_context_payload_in_query_and_execute_sql(self):
        """
        Acceptance test 10:
        Verify datasetContext object is accepted directly by /api/query and /api/execute-sql.
        """
        ctx = {
            "tableName": "payments",
            "sourceFileName": "payments.csv",
            "columns": [
                {"name": "payment_id", "type": "TEXT"},
                {"name": "amount", "type": "REAL"}
            ],
            "rowCount": 6,
            "datasetId": "payments"
        }

        # Query using datasetContext
        q_res = client.post(
            "/api/query",
            json={
                "question": "Top 3 highest amount",
                "datasetContext": ctx,
                "provider": "fallback"
            }
        )
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert "payments" in q_data["sql"]
        assert "audit_logs" not in q_data["sql"]

        # Execute safe SQL using datasetContext
        exec_res = client.post(
            "/api/execute-sql",
            json={
                "sql": 'SELECT "payment_id", "amount" FROM "payments" ORDER BY "amount" DESC LIMIT 3;',
                "datasetContext": ctx
            }
        )
        assert exec_res.status_code == 200
        exec_data = exec_res.json()
        assert exec_data["success"] is True
        assert exec_data["row_count"] == 3

    def test_11_no_csv_query_ever_reads_audit_logs_under_any_circumstance(self):
        """
        Acceptance test 11:
        Verify no CSV query ever reads audit_logs even with tricky questions
        mentioning logs, actions, audits, or failed events when a CSV table is selected.
        """
        tricky_queries = [
            "Show log of payments",
            "Failed transaction events",
            "Audit status of payments",
            "Payment action history",
            "Security status of transactions"
        ]

        for q in tricky_queries:
            res = client.post(
                "/api/query",
                json={
                    "question": q,
                    "tableName": "payments",
                    "provider": "fallback"
                }
            )
            assert res.status_code == 200
            data = res.json()
            sql = (data.get("sql") or "").lower()
            assert "audit_logs" not in sql, f"Tricky query '{q}' leaked audit_logs into SQL: {sql}"
            for audit_col in ["ip_address", "timestamp", "user_id"]:
                assert audit_col not in data.get("columns", [])

    def test_12_fail_if_audit_logs_appears_when_table_is_test_sql_orders(self):
        """
        Acceptance test 12 (Production Regression Guard):
        Fail if 'audit_logs' appears in SQL when tableName is 'test_sql_orders'.
        Also verifies the backend execution guard blocks and throws an error if
        SQL references audit_logs or anything other than test_sql_orders.
        """
        csv_content = (
            b"id,item,total\n"
            b"1,Laptop,1200\n"
            b"2,Mechanical Keyboard,150\n"
            b"3,Wireless Mouse,80\n"
            b"4,4K Monitor,450\n"
            b"5,USB-C Hub,60\n"
            b"6,Noise Cancelling Headphones,300\n"
            b"7,Desk Mat,30\n"
        )
        upload_res = client.post(
            "/api/upload",
            files={"file": ("test_sql_orders.csv", csv_content, "text/csv")}
        )
        assert upload_res.status_code == 200

        # Test query across standard and tricky questions
        test_queries = [
            "Top 5 highest total",
            "Show first 5 rows",
            "What is the total sum",
            "Audit log of failed items",
            "Show logs and actions"
        ]

        for q in test_queries:
            res = client.post(
                "/api/query",
                json={
                    "question": q,
                    "tableName": "test_sql_orders",
                    "active_table": "test_sql_orders",
                    "table_name": "test_sql_orders",
                    "provider": "fallback"
                }
            )
            assert res.status_code == 200
            data = res.json()
            sql = (data.get("sql") or "").lower()
            # Must FAIL if audit_logs appears anywhere in SQL when tableName is test_sql_orders
            assert "audit_logs" not in sql, f"CRITICAL FAILURE: audit_logs appeared in SQL when tableName was test_sql_orders: {sql}"
            if data.get("success"):
                assert "test_sql_orders" in sql
                for row in data.get("rows", []):
                    assert "ip_address" not in row
                    assert "action" not in row

        # Direct verification: If generator attempts to produce audit_logs for test_sql_orders,
        # the backend guard MUST throw ValueError and block database execution
        pipeline = TextToSqlPipeline(provider="fallback")
        with pytest.raises(ValueError) as excinfo:
            pipeline.corrector.heal_and_execute(
                initial_sql='SELECT * FROM "audit_logs" LIMIT 10;',
                user_question="Top 5 highest total",
                schema_info=get_db_schema_info(),
                execute_fn=lambda sql: {"success": True, "rows": [], "columns": []},
                target_table="test_sql_orders"
            )
        assert "Execution Guard Error" in str(excinfo.value)
        assert "audit_logs" in str(excinfo.value)
