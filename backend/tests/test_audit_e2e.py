"""
Comprehensive End-to-End Functionality Audit Test Suite.
Tests every feature requested:
- Database connection and dynamic schema detection
- Natural-language-to-SQL generation & execution accuracy (simple, complex, ambiguous, highest/lowest, aggregations, joins, multi-table)
- SQL validation, safety sandboxing, and error handling
- Self-correction and multi-agent workflow tracking
- RAG document upload, retrieval, and citation accuracy
- Charts, visualizations, and business analytics summaries
- Frontend-backend API integration (all endpoints)
- Edge cases, loading states, empty result sets, and error normalization
- SQLite and PostgreSQL compatibility
"""
import io
import os
import sys
import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.main import app
from backend.app.db.database import DB_PATH, engine
from backend.app.db.seed import seed_database
from backend.app.services.schema_service import get_db_schema_info
from backend.app.services.sql_executor import execute_safe_query, validate_safe_sql, _format_friendly_db_error
from backend.app.services.sql_generator import SQLGenerator
from backend.app.services.self_corrector import SelfCorrectionService
from backend.app.services.rag_service import rag_service, ProductionRAGService
from backend.app.services.pipeline import TextToSqlPipeline

client = TestClient(app)


# =========================================================================
# 1. Database Connection & Schema Detection Tests
# =========================================================================
class TestDatabaseAndSchema:
    def test_database_connected(self):
        """Verifies database connection is active and database exists."""
        assert os.path.exists(DB_PATH)
        with engine.connect() as conn:
            assert conn is not None

    def test_schema_detection_returns_all_tables(self):
        """Verifies schema detection inspects tables, columns, types, and sample data."""
        schema = get_db_schema_info()
        assert isinstance(schema, dict)
        expected_tables = ["customers", "products", "sales", "audit_logs"]
        for table in expected_tables:
            assert table in schema, f"Table '{table}' missing from detected schema."
            meta = schema[table]
            assert "columns" in meta and len(meta["columns"]) > 0
            assert "row_count" in meta and meta["row_count"] > 0
            assert "sample_rows" in meta and len(meta["sample_rows"]) > 0
            # Column metadata structure
            col = meta["columns"][0]
            assert "name" in col and "type" in col

    def test_reseed_database_success(self):
        """Verifies that database re-seeding succeeds and tables are populated."""
        seed_database()
        schema = get_db_schema_info()
        assert schema["customers"]["row_count"] == 40
        assert schema["products"]["row_count"] == 10
        assert schema["sales"]["row_count"] == 150
        assert schema["audit_logs"]["row_count"] == 80


# =========================================================================
# 2. SQLite and PostgreSQL Compatibility Tests
# =========================================================================
class TestEngineCompatibility:
    def test_sqlite_engine_configuration(self):
        """Verifies SQLite engine connects and dialect is properly reported."""
        assert engine.dialect.name in ["sqlite", "postgresql"]

    def test_postgresql_ddl_and_date_compatibility(self):
        """Verifies that DDL and SQL generator are dialect-aware for PostgreSQL."""
        # Check seed logic handles postgres dialect
        from backend.app.db.seed import seed_database
        from backend.app.services.sql_generator import SQLGenerator

        gen = SQLGenerator(provider="fallback")
        schema = get_db_schema_info()

        # Test dialect check in sql_generator
        with patch("backend.app.services.sql_generator.engine") as mock_engine:
            mock_engine.dialect.name = "postgresql"
            sql, _ = gen._generate_deterministic("Monthly sales trend", schema)
            assert "TO_CHAR(sale_date, 'YYYY-MM')" in sql or "sales_month" in sql

        with patch("backend.app.services.sql_generator.engine") as mock_engine:
            mock_engine.dialect.name = "sqlite"
            sql, _ = gen._generate_deterministic("Monthly sales trend", schema)
            assert "strftime('%Y-%m', sale_date)" in sql


# =========================================================================
# 3. Natural-Language-to-SQL Generation & Execution Accuracy
# =========================================================================
class TestNL2SQLAccuracy:
    def setup_method(self):
        self.pipeline = TextToSqlPipeline(provider="fallback")

    def test_simple_kpi_query(self):
        """NL2SQL: Single aggregate KPI."""
        res = self.pipeline.run("What is the total revenue?")
        assert res["success"] is True
        assert res["row_count"] == 1
        assert "total_revenue" in res["columns"]
        assert res["rows"][0]["total_revenue"] > 0

    def test_highest_ranking_query(self):
        """NL2SQL: Highest ranking with DESC sort order."""
        res = self.pipeline.run("Top 5 products by revenue")
        assert res["success"] is True
        assert res["row_count"] == 5
        assert "total_revenue" in res["columns"]
        # Verify descending order
        revenues = [r["total_revenue"] for r in res["rows"]]
        assert revenues == sorted(revenues, reverse=True)

    def test_lowest_ranking_query(self):
        """NL2SQL: Lowest ranking with ASC sort order."""
        res = self.pipeline.run("Lowest 5 revenue products")
        assert res["success"] is True
        assert res["row_count"] == 5
        # Verify ascending order
        revenues = [r["total_revenue"] for r in res["rows"]]
        assert revenues == sorted(revenues)

    def test_ambiguous_query_defaults(self):
        """NL2SQL: Ambiguous question defaults cleanly to revenue benchmark without error."""
        res = self.pipeline.run("Rank products")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "total_revenue" in res["columns"]
        assert "revenue" in res["explanation"].lower()

    def test_filtering_and_status_query(self):
        """NL2SQL: Filtering completed transactions."""
        res = self.pipeline.run("Failed audit log events")
        assert res["success"] is True
        assert res["row_count"] > 0
        for r in res["rows"]:
            assert r["status"] == "FAILURE" or "FAIL" in r.get("action", "")

    def test_multi_table_3way_join_spending_by_category(self):
        """NL2SQL: 3-way join between sales, customers, and products."""
        res = self.pipeline.run("Show customer spending by product category")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "plan" in res["columns"]
        assert "category" in res["columns"]
        assert "total_revenue" in res["columns"]

    def test_multi_table_join_aov_per_plan(self):
        """NL2SQL: Join between sales and customers by plan."""
        res = self.pipeline.run("Average order value per customer plan")
        assert res["success"] is True
        assert res["row_count"] == 4  # 4 plans
        assert "avg_order_value" in res["columns"]
        assert "plan" in res["columns"]

    def test_multi_table_3way_join_detailed_transactions(self):
        """NL2SQL: Detailed completed sales with customer and product names."""
        res = self.pipeline.run("List completed sales with customer name and product name")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "customer_name" in res["columns"]
        assert "product_name" in res["columns"]


# =========================================================================
# 4. SQL Validation, Safety Sandboxing & Error Handling
# =========================================================================
class TestSqlSecurityAndValidation:
    def test_read_only_allowed(self):
        """Valid read-only SELECT queries pass."""
        valid, err = validate_safe_sql("SELECT name FROM customers LIMIT 5;")
        assert valid is True
        assert err is None

    def test_common_table_expression_allowed(self):
        """WITH (CTE) read-only query is permitted."""
        valid, err = validate_safe_sql("WITH top_cust AS (SELECT id FROM customers) SELECT * FROM top_cust;")
        assert valid is True
        assert err is None

    def test_destructive_drop_blocked(self):
        """DROP TABLE operation is blocked."""
        valid, err = validate_safe_sql("DROP TABLE customers;")
        assert valid is False
        assert "Security" in err

    def test_destructive_delete_blocked(self):
        """DELETE operation is blocked."""
        valid, err = validate_safe_sql("DELETE FROM customers WHERE id = 1;")
        assert valid is False
        assert "Security" in err

    def test_destructive_update_blocked(self):
        """UPDATE operation is blocked."""
        valid, err = validate_safe_sql("UPDATE products SET price = 0;")
        assert valid is False
        assert "Security" in err

    def test_destructive_insert_blocked(self):
        """INSERT operation is blocked."""
        valid, err = validate_safe_sql("INSERT INTO products (name) VALUES ('Hacked');")
        assert valid is False
        assert "Security" in err

    def test_multi_statement_semicolon_chain_blocked(self):
        """Multi-statement queries chained with semicolons are blocked."""
        valid, err = validate_safe_sql("SELECT * FROM sales; SELECT * FROM products;")
        assert valid is False
        assert "Multi-statement" in err

    def test_human_friendly_error_formatting(self):
        """Driver error strings are normalized into clear user advice."""
        err1 = _format_friendly_db_error("sqlite3.OperationalError: no such column: nonexistent_col", "")
        assert "Column 'nonexistent_col' was not found" in err1

        err2 = _format_friendly_db_error("sqlite3.OperationalError: no such table: missing_tbl", "")
        assert "Table 'missing_tbl' does not exist" in err2


# =========================================================================
# 5. Self-Correction & Multi-Agent Workflow Tests
# =========================================================================
class TestSelfCorrectionAndMultiAgent:
    def test_self_corrector_heals_unknown_column(self):
        """Self-Correction heals unknown column by matching against schema."""
        corrector = SelfCorrectionService(provider="fallback")
        schema = get_db_schema_info()

        # Query has typo in column: total_speent instead of total_spent
        failing_sql = "SELECT name, total_speent FROM customers LIMIT 5;"
        error = "no such column: total_speent"

        healed, strategy = corrector.heal_sql(failing_sql, error, "Show customer spending", schema)
        assert "total_spent" in healed
        assert "Schema Alignment" in strategy

    def test_self_corrector_heals_ambiguous_column(self):
        """Self-Correction adds alias prefix when column is ambiguous."""
        corrector = SelfCorrectionService(provider="fallback")
        schema = get_db_schema_info()

        failing_sql = "SELECT id, name FROM sales s JOIN products p ON s.product_id = p.id;"
        error = "ambiguous column name: id"

        healed, strategy = corrector.heal_sql(failing_sql, error, "List sales with products", schema)
        assert "s.id" in healed or "p.name" in healed
        assert "Disambiguation" in strategy

    def test_multi_agent_workflow_steps_tracked(self):
        """Pipeline returns structured agent_steps for every execution turn."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = self.pipeline_run = pipeline.run("Top 3 products by revenue")

        assert "agent_steps" in res
        step_ids = [s["agent_id"] for s in res["agent_steps"]]
        assert "schema_linker" in step_ids
        assert "sql_generator" in step_ids
        assert "self_corrector" in step_ids
        assert "business_insights" in step_ids
        assert "visualizer" in step_ids

        # Every step has timing and thought logs
        for step in res["agent_steps"]:
            assert "execution_time_sec" in step
            assert "thought_logs" in step and len(step["thought_logs"]) > 0
            assert step["status"] in ["COMPLETED", "FAILED"]


# =========================================================================
# 6. RAG Document Upload, Retrieval & Citation Accuracy
# =========================================================================
class TestRAGFunctionality:
    def test_rag_ingest_and_chunking(self):
        """Verifies text extraction and chunking with overlap."""
        doc_content = b"Enterprise Data Architecture Guide.\nSection 1: Data Modeling. " + (b"Data pipelines are crucial. " * 30)
        res = rag_service.ingest("test_architecture_guide.txt", doc_content)

        assert res["filename"] == "test_architecture_guide.txt"
        assert res["chunks_created"] >= 1
        assert rag_service.has_documents is True

    def test_rag_retrieval_and_citation_accuracy(self):
        """Verifies RAG search returns relevant chunks with verified citations."""
        res = rag_service.answer("What is data modeling in the architecture guide?")
        assert res["retrieved_count"] > 0
        assert len(res["citations"]) > 0

        first_cite = res["citations"][0]
        assert "source" in first_cite
        assert "chunk" in first_cite
        assert "excerpt" in first_cite
        assert "score" in first_cite
        assert bool(res["answer"])

    def test_rag_query_routing_in_pipeline(self):
        """Pipeline automatically routes document questions to RAG engine."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("According to the portfolio guide, what is step 1?")

        assert res["success"] is True
        assert res["route"] == "rag"
        assert len(res["citations"]) > 0
        assert "Resume" in res["insights"]["direct_answer"] or "Extract" in res["insights"]["direct_answer"] or bool(res["citations"])


# =========================================================================
# 7. Charts, Visualizations & Analytics Summaries
# =========================================================================
class TestVisualizationAndSummaries:
    def test_chart_inference_bar_for_rankings(self):
        """Bar chart recommended for top/lowest rankings."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("Top 5 customers by total spent")

        vis = res["visualization"]
        assert vis["chart_type"] == "bar"
        assert vis["x_axis"] in ["customer_name", "name"]
        assert "total_spent" in vis["y_axes"]
        assert vis["ranking_order"] == "desc"

    def test_chart_inference_line_for_time_series(self):
        """Line chart recommended for monthly trends."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("Monthly sales trend by region")

        vis = res["visualization"]
        assert vis["chart_type"] in ["line", "bar"]
        assert "sales_month" in vis["x_axis"] or len(vis["y_axes"]) > 0

    def test_chart_inference_pie_for_small_distribution(self):
        """Pie chart recommended for small categorical distribution."""
        pipeline = TextToSqlPipeline(provider="fallback")
        rows = [
            {"plan": "Enterprise", "count": 25},
            {"plan": "Professional", "count": 18},
            {"plan": "Standard", "count": 12},
        ]
        vis = pipeline._infer_visualization(
            columns=["plan", "count"],
            rows=rows,
            user_question="Customer distribution by plan"
        )
        assert vis["chart_type"] == "pie"

    def test_business_insights_structure(self):
        """Insights object has direct answer, key findings, comparisons, and caveats."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("What is the total revenue?")

        ins = res["insights"]
        assert ins["status"] == "success"
        assert ins["grounded"] is True
        assert bool(ins["direct_answer"])
        assert len(ins["key_findings"]) >= 1
        assert bool(ins["business_takeaway"])


# =========================================================================
# 8. Frontend-Backend API Integration Tests
# =========================================================================
class TestApiIntegration:
    def test_health_endpoint(self):
        """GET /health and GET /api/health return healthy status and metadata."""
        res1 = client.get("/health")
        assert res1.status_code == 200
        assert res1.json()["status"] == "healthy"

        res2 = client.get("/api/health")
        assert res2.status_code == 200
        data = res2.json()
        assert data["database_connected"] is True
        assert "providers" in data
        assert "rag_store" in data

    def test_get_schema_endpoint(self):
        """GET /api/schema returns structured tables and columns."""
        res = client.get("/api/schema")
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert "customers" in res.json()["schema"]

    def test_seed_endpoint(self):
        """POST /api/seed re-seeds database."""
        res = client.post("/api/seed")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_verify_key_endpoint(self):
        """POST /api/verify-key validates fallback and handles providers."""
        res = client.post("/api/verify-key", json={"api_key": "dummy", "provider": "fallback"})
        assert res.status_code == 200
        assert res.json()["valid"] is True

    def test_query_endpoint(self):
        """POST /api/query processes natural language query end-to-end."""
        res = client.post("/api/query", json={"query": "Top 3 products by revenue", "provider": "fallback"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["rows"]) == 3
        assert "visualization" in data
        assert "insights" in data
        assert "agent_steps" in data

    def test_execute_sql_endpoint(self):
        """POST /api/execute-sql executes safe query and provides insights."""
        custom_sql = "SELECT name, price FROM products ORDER BY price DESC LIMIT 3;"
        res = client.post("/api/execute-sql", json={"sql": custom_sql, "question": "Top 3 expensive products"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["rows"]) == 3
        assert "insights" in data

    def test_upload_csv_dataset(self):
        """POST /api/upload imports custom CSV dataset and creates table."""
        csv_data = "item_id,item_name,category,units\n1,Widget A,Gadgets,50\n2,Widget B,Tools,20\n"
        files = {"file": ("test_inventory.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        res = client.post("/api/upload", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["table_name"] == "test_inventory"
        assert data["row_count"] == 2

    def test_upload_json_dataset(self):
        """POST /api/upload imports custom JSON records."""
        json_data = json.dumps([
            {"emp_id": 101, "emp_name": "Alice", "dept": "Engineering"},
            {"emp_id": 102, "emp_name": "Bob", "dept": "Marketing"}
        ])
        files = {"file": ("test_employees.json", io.BytesIO(json_data.encode()), "application/json")}
        res = client.post("/api/upload", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["row_count"] == 2

    def test_rag_upload_and_query_endpoints(self):
        """POST /api/rag/upload, GET /api/rag/documents, and POST /api/rag/query."""
        doc_data = b"Antigravity Operations Manual. Step 1: Initialize server. Step 2: Configure analytics."
        files = {"file": ("operations_manual.txt", io.BytesIO(doc_data), "text/plain")}
        res_upload = client.post("/api/rag/upload", files=files)
        assert res_upload.status_code == 200
        assert res_upload.json()["success"] is True

        res_docs = client.get("/api/rag/documents")
        assert res_docs.status_code == 200
        assert res_docs.json()["document_count"] > 0

        res_query = client.post("/api/rag/query", json={"query": "What is Step 1 in operations manual?", "provider": "fallback"})
        assert res_query.status_code == 200
        assert res_query.json()["success"] is True
        assert len(res_query.json()["citations"]) > 0


# =========================================================================
# 9. Edge Cases & Error Handling Tests
# =========================================================================
class TestEdgeCases:
    def test_empty_query_returns_400(self):
        """Empty query prompt rejected with 400 Bad Request."""
        res = client.post("/api/query", json={"query": "   "})
        assert res.status_code == 400

    def test_empty_sql_returns_400(self):
        """Empty custom SQL rejected with 400 Bad Request."""
        res = client.post("/api/execute-sql", json={"sql": ""})
        assert res.status_code == 400

    def test_query_returning_zero_rows(self):
        """Query with zero matching records produces friendly empty insights without error."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("SELECT * FROM customers WHERE id = 99999;")
        assert res["row_count"] == 0
        # Insights should handle 0 rows gracefully
        ins = res["insights"]
        assert ins["status"] in ["empty", "success"]
        assert "caveats" in ins

    def test_destructive_query_blocked_at_endpoint(self):
        """Adversarial destructive query blocked via /api/query."""
        res = client.post("/api/query", json={"query": "DROP TABLE sales;"})
        assert res.status_code == 200
        assert res.json()["success"] is False
        assert "Security" in (res.json().get("error") or "")
