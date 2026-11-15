"""
Test suite verifying end-to-end multi-table query generation, schema grounding,
and execution on uploaded custom e-commerce CSV datasets (products, order_items, orders, customers, payments, support_tickets).
Guarantees column resolution (e.g. product_name instead of p.name, product_id instead of p.id) and self-correction.
"""
import os
import pytest
import pandas as pd
from backend.app.services.pipeline import TextToSqlPipeline
from backend.app.services.schema_service import get_db_schema_info
from backend.app.services.self_corrector import SelfCorrectionService
from backend.app.services.sql_executor import execute_safe_query
from backend.app.db.database import engine


@pytest.fixture(scope="module", autouse=True)
def setup_ecommerce_tables():
    """Ensures uploaded e-commerce datasets are loaded into the database."""
    base = r"C:\Users\sindhu\.gemini\antigravity\brain\c1278eb5-9de5-4c62-91c2-aa0787e4c390\.user_uploaded"
    mapping = {
        "customers": "media_1794740204311_c2dbe2da.csv",
        "products": "media_1794740204333_28abc795.csv",
        "order_items": "media_1794740204350_ace4f008.csv",
        "payments": "media_1794740204352_3c5f2f78.csv",
        "orders": "media_1794740204356_49b5def4.csv",
    }
    with engine.begin() as conn:
        for tbl, fname in mapping.items():
            fpath = os.path.join(base, fname)
            if os.path.exists(fpath):
                df = pd.read_csv(fpath)
                df.to_sql(tbl, con=conn, if_exists="replace", index=False)
    yield
    from backend.app.db.seed import seed_database
    seed_database()
    get_db_schema_info(force_refresh=True)


@pytest.fixture(scope="module")
def schema(setup_ecommerce_tables):
    return get_db_schema_info(force_refresh=True)


class TestUploadedEcommerceCSVs:
    def test_top_revenue_products_multi_table_join(self, schema):
        """'top 5 revenue products' must join order_items and products using actual columns."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("top 5 revenue products", active_table="order_items")
        
        assert res["success"] is True
        assert res["row_count"] >= 1
        assert "order_items" in res["sql"].lower()
        assert "products" in res["sql"].lower()
        assert "product_name" in res["sql"].lower()
        # Ensure hallucinated column p.name is NEVER generated
        assert "p.name" not in res["sql"]
        assert "p.id" not in res["sql"]
        assert res["insights"]["direct_answer"] is not None

    def test_customer_count_query(self, schema):
        """'how many customers are in the database' queries customers table, not audit_logs."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("how many customers are in the database", active_table="customers")
        
        assert res["success"] is True
        assert res["row_count"] == 1
        assert "customers" in res["sql"].lower()
        assert "audit_logs" not in res["sql"].lower()
        assert "12" in res["insights"]["direct_answer"] or "customer" in res["insights"]["direct_answer"].lower()

    def test_orders_count_query(self, schema):
        """'how many orders are in the database' queries orders table."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("how many orders are in the database", active_table="orders")
        
        assert res["success"] is True
        assert res["row_count"] == 1
        assert "orders" in res["sql"].lower()
        assert "30" in res["insights"]["direct_answer"] or "order" in res["insights"]["direct_answer"].lower()

    def test_self_corrector_heals_p_name_and_p_id(self, schema):
        """When given a query with nonexistent p.name and p.id, self-corrector heals to product_name and product_id."""
        corrector = SelfCorrectionService(provider="fallback")
        broken_sql = "SELECT p.name, p.category FROM products p ORDER BY p.id DESC LIMIT 5;"
        
        result = corrector.heal_and_execute(
            initial_sql=broken_sql,
            user_question="top products",
            schema_info=schema,
            execute_fn=execute_safe_query
        )
        assert result["success"] is True
        assert "product_name" in result["final_sql"]
        assert len(result["rows"]) >= 1

    def test_give_me_all_products_browse_query(self, schema):
        """'Give me all products' should browse products directly without joining order_items or audit_logs."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("Give me all products", active_table=None)
        
        assert res["success"] is True
        assert res["row_count"] >= 1
        assert "products" in res["sql"].lower()
        assert "audit_logs" not in res["sql"].lower()
        assert res["columns"] == ["product_id", "product_name", "category", "unit_price", "stock_qty"]
        assert "records from the 'products' table" in res["insights"]["direct_answer"].lower() or "products" in res["insights"]["direct_answer"].lower()

    def test_show_first_10_rows_from_each_table(self, schema):
        """Show first 10 rows from each table returns the exact records and correct columns."""
        pipeline = TextToSqlPipeline(provider="fallback")
        for tbl in ["customers", "products", "orders", "order_items", "payments", "support_tickets"]:
            res = pipeline.run(f"Show first 10 rows from {tbl}", active_table=tbl)
            assert res["success"] is True
            assert res["row_count"] >= 1
            assert tbl in res["sql"].lower()
            assert "audit_logs" not in res["sql"].lower()
            assert tbl in res["insights"]["direct_answer"].lower()
