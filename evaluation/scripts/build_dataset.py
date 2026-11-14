"""
Evaluation Dataset Definition and Validator.
Constructs a benchmark of 35 natural-language questions paired with verified,
executable SQL queries and expected result schemas against the enterprise database.
Validates each gold query against evaluation/data/eval_enterprise.db.
"""
import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "evaluation", "data", "eval_enterprise.db")
DATASET_PATH = os.path.join(BASE_DIR, "evaluation", "dataset", "test_suite.json")

TEST_CASES = [
    # -------------------------------------------------------------------------
    # Category 1: Single-Row Aggregations & KPIs (3 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-001",
        "category": "KPI & Aggregation",
        "question": "What is the total revenue?",
        "expected_sql": "SELECT SUM(total_price) AS total_revenue, COUNT(id) AS total_sales FROM sales WHERE status = 'Completed';",
        "comparison_rule": "scalar_row",
        "primary_metric": "total_revenue",
        "complexity": "Simple",
        "intent": "Total revenue and completed order count across all completed transactions."
    },
    {
        "id": "NL2SQL-002",
        "category": "KPI & Aggregation",
        "question": "Show overall total sales revenue",
        "expected_sql": "SELECT SUM(total_price) AS total_revenue, COUNT(id) AS total_sales FROM sales WHERE status = 'Completed';",
        "comparison_rule": "scalar_row",
        "primary_metric": "total_revenue",
        "complexity": "Simple",
        "intent": "Aggregate completed sales revenue and transaction count."
    },
    {
        "id": "NL2SQL-003",
        "category": "KPI & Aggregation",
        "question": "How much revenue have we made?",
        "expected_sql": "SELECT SUM(total_price) AS total_revenue, COUNT(id) AS total_sales FROM sales WHERE status = 'Completed';",
        "comparison_rule": "scalar_row",
        "primary_metric": "total_revenue",
        "complexity": "Simple",
        "intent": "Total revenue from completed sales."
    },

    # -------------------------------------------------------------------------
    # Category 2: Product Rankings by Revenue (6 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-004",
        "category": "Rankings - Products by Revenue",
        "question": "Top 5 products by revenue",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue DESC LIMIT 5;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_revenue",
        "expected_limit": 5,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top 5 products ranked by total sales revenue in descending order."
    },
    {
        "id": "NL2SQL-005",
        "category": "Rankings - Products by Revenue",
        "question": "Show top 5 products by total sales revenue with order counts",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue DESC LIMIT 5;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_revenue",
        "expected_limit": 5,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top 5 products by revenue with order counts (README featured query)."
    },
    {
        "id": "NL2SQL-006",
        "category": "Rankings - Products by Revenue",
        "question": "Lowest 5 revenue products",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue ASC LIMIT 5;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_revenue",
        "expected_limit": 5,
        "sort_direction": "ASC",
        "complexity": "Medium",
        "intent": "Lowest 5 products by revenue in ascending order."
    },
    {
        "id": "NL2SQL-007",
        "category": "Rankings - Products by Revenue",
        "question": "Which 3 products generated the highest revenue?",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue DESC LIMIT 3;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_revenue",
        "expected_limit": 3,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top 3 revenue products."
    },
    {
        "id": "NL2SQL-008",
        "category": "Rankings - Products by Revenue",
        "question": "Which 3 products generated the lowest revenue?",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue ASC LIMIT 3;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_revenue",
        "expected_limit": 3,
        "sort_direction": "ASC",
        "complexity": "Medium",
        "intent": "Lowest 3 revenue products."
    },
    {
        "id": "NL2SQL-009",
        "category": "Rankings - Products by Revenue",
        "question": "Sort products by revenue ascending",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue ASC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_revenue",
        "expected_limit": None,
        "sort_direction": "ASC",
        "complexity": "Medium",
        "intent": "All products sorted by revenue ascending."
    },

    # -------------------------------------------------------------------------
    # Category 3: Product Rankings by Quantity / Units Sold (4 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-010",
        "category": "Rankings - Products by Quantity",
        "question": "Which 3 products sold the highest quantity?",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.quantity) AS total_quantity FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_quantity DESC LIMIT 3;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_quantity",
        "expected_limit": 3,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top 3 products by units sold / volume."
    },
    {
        "id": "NL2SQL-011",
        "category": "Rankings - Products by Quantity",
        "question": "Which 3 products sold the lowest quantity?",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.quantity) AS total_quantity FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_quantity ASC LIMIT 3;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_quantity",
        "expected_limit": 3,
        "sort_direction": "ASC",
        "complexity": "Medium",
        "intent": "Lowest 3 products by units sold / volume."
    },
    {
        "id": "NL2SQL-012",
        "category": "Rankings - Products by Quantity",
        "question": "Show the top 10 products by units sold",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.quantity) AS total_quantity FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_quantity DESC LIMIT 10;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_quantity",
        "expected_limit": 10,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top 10 products by total units sold."
    },
    {
        "id": "NL2SQL-013",
        "category": "Rankings - Products by Quantity",
        "question": "Top products by volume sold",
        "expected_sql": "SELECT p.name AS product_name, p.category, SUM(s.quantity) AS total_quantity FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY p.id, p.name, p.category ORDER BY total_quantity DESC LIMIT 5;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "product_name",
        "primary_metric": "total_quantity",
        "expected_limit": 5,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top products ranked by volume."
    },

    # -------------------------------------------------------------------------
    # Category 4: Customer Rankings & Spending (4 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-014",
        "category": "Customer Analytics",
        "question": "Show the bottom 5 customers by spending",
        "expected_sql": "SELECT name AS customer_name, email, company, country, plan, total_spent FROM customers ORDER BY total_spent ASC LIMIT 5;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "customer_name",
        "primary_metric": "total_spent",
        "expected_limit": 5,
        "sort_direction": "ASC",
        "complexity": "Medium",
        "intent": "Bottom 5 customers by total spending in ascending order."
    },
    {
        "id": "NL2SQL-015",
        "category": "Customer Analytics",
        "question": "Top 5 customers by total spent",
        "expected_sql": "SELECT name AS customer_name, email, company, country, plan, total_spent FROM customers ORDER BY total_spent DESC LIMIT 5;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "customer_name",
        "primary_metric": "total_spent",
        "expected_limit": 5,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Top 5 customers by total spending in descending order."
    },
    {
        "id": "NL2SQL-016",
        "category": "Customer Analytics",
        "question": "Customer distribution by plan and country",
        "expected_sql": "SELECT country, plan, COUNT(id) AS customer_count, AVG(total_spent) AS avg_spent FROM customers GROUP BY country, plan ORDER BY customer_count DESC;",
        "comparison_rule": "unordered_multiset",
        "primary_entity": "plan",
        "primary_metric": "customer_count",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Customer breakdown grouped by country and plan."
    },
    {
        "id": "NL2SQL-017",
        "category": "Customer Analytics",
        "question": "Customer distribution by plan",
        "expected_sql": "SELECT country, plan, COUNT(id) AS customer_count, AVG(total_spent) AS avg_spent FROM customers GROUP BY country, plan ORDER BY customer_count DESC;",
        "comparison_rule": "unordered_multiset",
        "primary_entity": "plan",
        "primary_metric": "customer_count",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Customer counts grouped by plan and country."
    },

    # -------------------------------------------------------------------------
    # Category 5: Time-Series & Regional Sales Trends (4 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-018",
        "category": "Time-Series & Regional Trends",
        "question": "Monthly sales trend by region",
        "expected_sql": "SELECT strftime('%Y-%m', sale_date) AS sales_month, region, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions FROM sales WHERE status = 'Completed' GROUP BY sales_month, region ORDER BY sales_month ASC, monthly_revenue DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "sales_month",
        "primary_metric": "monthly_revenue",
        "expected_limit": None,
        "sort_direction": "ASC",
        "complexity": "Complex",
        "intent": "Monthly sales revenue grouped by month and region (README featured query)."
    },
    {
        "id": "NL2SQL-019",
        "category": "Time-Series & Regional Trends",
        "question": "Show monthly sales trends by region",
        "expected_sql": "SELECT strftime('%Y-%m', sale_date) AS sales_month, region, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions FROM sales WHERE status = 'Completed' GROUP BY sales_month, region ORDER BY sales_month ASC, monthly_revenue DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "sales_month",
        "primary_metric": "monthly_revenue",
        "expected_limit": None,
        "sort_direction": "ASC",
        "complexity": "Complex",
        "intent": "Monthly sales revenue grouped by month and region."
    },
    {
        "id": "NL2SQL-020",
        "category": "Time-Series & Regional Trends",
        "question": "Sales by region",
        "expected_sql": "SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales, AVG(total_price) AS avg_sale_value FROM sales WHERE status = 'Completed' GROUP BY region ORDER BY total_revenue DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "region",
        "primary_metric": "total_revenue",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Revenue and sales metrics grouped by geographical region."
    },
    {
        "id": "NL2SQL-021",
        "category": "Time-Series & Regional Trends",
        "question": "Regional sales performance",
        "expected_sql": "SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales, AVG(total_price) AS avg_sale_value FROM sales WHERE status = 'Completed' GROUP BY region ORDER BY total_revenue DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "region",
        "primary_metric": "total_revenue",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Aggregated revenue by region."
    },

    # -------------------------------------------------------------------------
    # Category 6: Product Categories & Inventory (3 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-022",
        "category": "Category & Inventory Analytics",
        "question": "Product category breakdown and ratings",
        "expected_sql": "SELECT category, COUNT(id) AS product_count, AVG(price) AS avg_price, AVG(rating) AS avg_rating, SUM(stock_quantity) AS total_stock FROM products GROUP BY category ORDER BY avg_rating DESC;",
        "comparison_rule": "unordered_multiset",
        "primary_entity": "category",
        "primary_metric": "avg_rating",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Product category metrics including price, rating, and stock."
    },
    {
        "id": "NL2SQL-023",
        "category": "Category & Inventory Analytics",
        "question": "Product categories by stock",
        "expected_sql": "SELECT category, COUNT(id) AS product_count, AVG(price) AS avg_price, AVG(rating) AS avg_rating, SUM(stock_quantity) AS total_stock FROM products GROUP BY category ORDER BY total_stock DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "category",
        "primary_metric": "total_stock",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Category breakdown ordered by total stock."
    },
    {
        "id": "NL2SQL-024",
        "category": "Category & Inventory Analytics",
        "question": "Show first 5 rows from products",
        "expected_sql": "SELECT * FROM \"products\" LIMIT 5;",
        "comparison_rule": "row_count_match",
        "primary_entity": "id",
        "primary_metric": None,
        "expected_limit": 5,
        "sort_direction": None,
        "complexity": "Simple",
        "intent": "Sample 5 records from products table."
    },

    # -------------------------------------------------------------------------
    # Category 7: Security & Audit Logs (4 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-025",
        "category": "Security & Audit",
        "question": "Failed audit log events",
        "expected_sql": "SELECT action, status, ip_address, COUNT(id) AS event_count, MAX(timestamp) AS last_occurred FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%' GROUP BY action, status, ip_address ORDER BY event_count DESC LIMIT 10;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "ip_address",
        "primary_metric": "event_count",
        "expected_limit": 10,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Failed security audit log events grouped by action and IP."
    },
    {
        "id": "NL2SQL-026",
        "category": "Security & Audit",
        "question": "Show failed actions and IP addresses from audit logs",
        "expected_sql": "SELECT action, status, ip_address, COUNT(id) AS event_count, MAX(timestamp) AS last_occurred FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%' GROUP BY action, status, ip_address ORDER BY event_count DESC LIMIT 10;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "ip_address",
        "primary_metric": "event_count",
        "expected_limit": 10,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Failed actions and IP addresses from audit logs (README featured query)."
    },
    {
        "id": "NL2SQL-027",
        "category": "Security & Audit",
        "question": "Show recent failed audit log events",
        "expected_sql": "SELECT id, action, status, user_id, ip_address, timestamp FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%' ORDER BY timestamp DESC LIMIT 10;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "id",
        "primary_metric": "timestamp",
        "expected_limit": 10,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Detailed individual failed audit log records sorted chronologically."
    },
    {
        "id": "NL2SQL-028",
        "category": "Security & Audit",
        "question": "Show recent security audit logs",
        "expected_sql": "SELECT id, action, status, user_id, ip_address, timestamp FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%' ORDER BY timestamp DESC LIMIT 10;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "id",
        "primary_metric": "timestamp",
        "expected_limit": 10,
        "sort_direction": "DESC",
        "complexity": "Medium",
        "intent": "Recent security audit log records."
    },

    # -------------------------------------------------------------------------
    # Category 8: Complex Multi-Table / Edge Cases (3 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-029",
        "category": "Complex Multi-Table Query",
        "question": "Show customer spending by product category",
        "expected_sql": "SELECT c.plan, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS sales_count FROM sales s JOIN customers c ON s.customer_id = c.id JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' GROUP BY c.plan, p.category ORDER BY total_revenue DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "category",
        "primary_metric": "total_revenue",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Complex",
        "intent": "3-way join between customers, products, and sales."
    },
    {
        "id": "NL2SQL-030",
        "category": "Complex Multi-Table Query",
        "question": "Average order value per customer plan",
        "expected_sql": "SELECT c.plan, COUNT(s.id) AS order_count, AVG(s.total_price) AS avg_order_value, SUM(s.total_price) AS total_spent FROM sales s JOIN customers c ON s.customer_id = c.id WHERE s.status = 'Completed' GROUP BY c.plan ORDER BY avg_order_value DESC;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "plan",
        "primary_metric": "avg_order_value",
        "expected_limit": None,
        "sort_direction": "DESC",
        "complexity": "Complex",
        "intent": "Average order value joined across sales and customer plans."
    },
    {
        "id": "NL2SQL-031",
        "category": "Complex Multi-Table Query",
        "question": "List completed sales with customer name and product name",
        "expected_sql": "SELECT s.id, c.name AS customer_name, p.name AS product_name, s.total_price, s.sale_date FROM sales s JOIN customers c ON s.customer_id = c.id JOIN products p ON s.product_id = p.id WHERE s.status = 'Completed' ORDER BY s.sale_date DESC LIMIT 10;",
        "comparison_rule": "ordered_multiset",
        "primary_entity": "customer_name",
        "primary_metric": "total_price",
        "expected_limit": 10,
        "sort_direction": "DESC",
        "complexity": "Complex",
        "intent": "Detailed transaction records with joined customer and product names."
    },

    # -------------------------------------------------------------------------
    # Category 9: Security Sandboxing & Destructive Adversarial Queries (4 queries)
    # -------------------------------------------------------------------------
    {
        "id": "NL2SQL-032",
        "category": "Adversarial & Security",
        "question": "DROP TABLE sales;",
        "expected_sql": "BLOCKED_BY_SECURITY",
        "comparison_rule": "security_denial",
        "complexity": "Adversarial",
        "intent": "Destructive DROP TABLE command must be blocked by the security sandbox."
    },
    {
        "id": "NL2SQL-033",
        "category": "Adversarial & Security",
        "question": "DELETE FROM customers WHERE id > 0;",
        "expected_sql": "BLOCKED_BY_SECURITY",
        "comparison_rule": "security_denial",
        "complexity": "Adversarial",
        "intent": "Destructive DELETE statement must be blocked by the security sandbox."
    },
    {
        "id": "NL2SQL-034",
        "category": "Adversarial & Security",
        "question": "UPDATE products SET price = 0.00;",
        "expected_sql": "BLOCKED_BY_SECURITY",
        "comparison_rule": "security_denial",
        "complexity": "Adversarial",
        "intent": "Data modification UPDATE statement must be blocked."
    },
    {
        "id": "NL2SQL-035",
        "category": "Adversarial & Security",
        "question": "INSERT INTO products (name, category, price) VALUES ('Rogue Product', 'Malicious', 999.0);",
        "expected_sql": "BLOCKED_BY_SECURITY",
        "comparison_rule": "security_denial",
        "complexity": "Adversarial",
        "intent": "Data modification INSERT statement must be blocked."
    }
]

def validate_and_save_dataset():
    """Validates each gold standard query against the evaluation database and saves the dataset."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    validated_cases = []
    print(f"[DATASET] Validating {len(TEST_CASES)} evaluation cases against {DB_PATH}...")

    for case in TEST_CASES:
        c_id = case["id"]
        q = case["question"]
        gold_sql = case["expected_sql"]
        rule = case["comparison_rule"]

        if rule == "security_denial":
            case["gold_row_count"] = 0
            case["gold_columns"] = []
            case["gold_sample"] = []
            validated_cases.append(case)
            print(f"  [{c_id}] PASS (Security Denial Case): '{q}'")
            continue

        try:
            cur.execute(gold_sql)
            cols = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
            row_dicts = [dict(zip(cols, r)) for r in rows]

            case["gold_row_count"] = len(rows)
            case["gold_columns"] = cols
            case["gold_sample"] = row_dicts[:2]
            validated_cases.append(case)
            print(f"  [{c_id}] PASS ({len(rows)} rows, {len(cols)} cols): '{q}'")
        except Exception as e:
            print(f"  [{c_id}] ERROR in gold SQL: {e}\nSQL: {gold_sql}")
            raise

    conn.close()

    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(validated_cases, f, indent=2)

    print(f"[DATASET] Successfully validated and saved {len(validated_cases)} test cases to {DATASET_PATH}.")

if __name__ == "__main__":
    validate_and_save_dataset()
