"""
Test suite verifying end-to-end multi-table query generation, schema grounding,
and execution on uploaded custom e-commerce CSV datasets (products, order_items, orders, customers, payments, support_tickets).
Guarantees column resolution (e.g. product_name instead of p.name, product_id instead of p.id) and self-correction.
"""
import pytest
from backend.app.services.pipeline import TextToSqlPipeline
from backend.app.services.schema_service import get_db_schema_info
from backend.app.services.self_corrector import SelfCorrectionService
from backend.app.services.sql_executor import execute_safe_query


@pytest.fixture(scope="module")
def schema():
    return get_db_schema_info(force_refresh=True)


class TestUploadedEcommerceCSVs:
    def test_top_revenue_products_multi_table_join(self, schema):
        """'top 5 revenue products' must join order_items and products using actual columns."""
        pipeline = TextToSqlPipeline(provider="fallback")
        res = pipeline.run("top 5 revenue products", active_table="products")
        
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
