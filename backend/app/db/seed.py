"""
Enterprise Database Seeding Service.
Seeds the database with canonical e-commerce datasets:
- customers (12 real records from sample_data/customers.csv)
- products (8 real records from sample_data/products.csv)
- orders (30 real records from sample_data/orders.csv)
- order_items (55 real records from sample_data/order_items.csv)
- payments (30 real records from sample_data/payments.csv)
- support_tickets (8 real records from sample_data/support_tickets.csv)
- audit_logs (80 realistic security/audit records)
- employees (16 realistic staff records)
- sales (150+ completed transactions)
"""
import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from backend.app.db.database import DATABASE_URL, engine
except ImportError:
    from app.db.database import DATABASE_URL, engine


def seed_database():
    """
    Creates and seeds enterprise analytics database with canonical e-commerce data:
    12 customers, 8 products, 30 orders, 55 order_items, 30 payments, 8 support_tickets,
    80 audit_logs, 16 employees, and 150+ sales.
    """
    print("[SEED] Seeding Enterprise Analytics Database with canonical e-commerce data...")

    is_postgres = (engine.dialect.name == "postgresql")
    pk_col = "id SERIAL PRIMARY KEY" if is_postgres else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    dt_type = "TIMESTAMP" if is_postgres else "DATETIME"
    cascade = " CASCADE" if is_postgres else ""

    sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")

    # 1. Load CSVs from sample_data
    cust_file = os.path.join(sample_dir, "customers.csv")
    prod_file = os.path.join(sample_dir, "products.csv")
    orders_file = os.path.join(sample_dir, "orders.csv")
    items_file = os.path.join(sample_dir, "order_items.csv")
    payments_file = os.path.join(sample_dir, "payments.csv")
    tickets_file = os.path.join(sample_dir, "support_tickets.csv")

    cust_df = pd.read_csv(cust_file)
    prod_df = pd.read_csv(prod_file)
    orders_df = pd.read_csv(orders_file)
    items_df = pd.read_csv(items_file)
    payments_df = pd.read_csv(payments_file)
    tickets_df = pd.read_csv(tickets_file)

    # Compute customer total_spent from order_items
    merged_orders = items_df.merge(orders_df, on="order_id")
    spent_by_cust = merged_orders.groupby("customer_id")["line_total"].sum().to_dict()

    # Add dual-compatible columns to customers
    cust_df["id"] = cust_df["customer_id"]
    cust_df["name"] = cust_df["customer_name"]
    cust_df["email"] = [f"{str(n).lower().replace(' ', '')}@example.com" for n in cust_df["customer_name"]]
    cust_df["company"] = ["Apex Enterprises", "TechWave", "Global Logistics", "Quantum Corp", 
                           "Starlight Labs", "Nexus Fin", "CyberDyn", "Optima Retail", 
                           "BioGen", "Titan Aero", "Vanguard", "Horizon Media"][:len(cust_df)]
    cust_df["country"] = ["India"] * len(cust_df)
    cust_df["plan"] = ["Enterprise", "Professional", "Standard", "Standard",
                       "Professional", "Enterprise", "Standard", "Starter",
                       "Professional", "Enterprise", "Standard", "Starter"][:len(cust_df)]
    cust_df["total_spent"] = cust_df["customer_id"].map(lambda cid: float(spent_by_cust.get(cid, 0.0)))
    cust_df["created_at"] = cust_df["signup_date"]

    # Add dual-compatible columns to products
    prod_df["id"] = prod_df["product_id"]
    prod_df["name"] = prod_df["product_name"]
    prod_df["price"] = prod_df["unit_price"]
    prod_df["stock_quantity"] = prod_df["stock_qty"]
    prod_df["rating"] = [4.8, 4.9, 4.6, 4.7, 4.5, 4.85, 4.4, 4.65][:len(prod_df)]

    # Standardize support_tickets columns
    expected_ticket_cols = ["ticket_id", "customer_id", "order_id", "issue", "priority", "status", "created_at"]
    if len(tickets_df.columns) == len(expected_ticket_cols):
        tickets_df.columns = expected_ticket_cols

    with engine.begin() as conn:
        # A reset must return the database to the documented sample schema.
        # Previously only canonical tables were dropped, so uploaded/test tables
        # survived each re-seed and leaked into the production schema explorer
        # and Text-to-SQL context indefinitely.
        if is_postgres:
            table_rows = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )).fetchall()
        else:
            table_rows = conn.execute(text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )).fetchall()

        # Drop every application table, including stale uploaded datasets. This
        # is deliberate: /api/seed is exposed as a reset, not an incremental
        # seed operation.
        for (table_name,) in table_rows:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"{cascade};'))

        # Write e-commerce tables
        cust_df.to_sql("customers", con=conn, if_exists="replace", index=False)
        prod_df.to_sql("products", con=conn, if_exists="replace", index=False)
        orders_df.to_sql("orders", con=conn, if_exists="replace", index=False)
        items_df.to_sql("order_items", con=conn, if_exists="replace", index=False)
        payments_df.to_sql("payments", con=conn, if_exists="replace", index=False)
        tickets_df.to_sql("support_tickets", con=conn, if_exists="replace", index=False)

        # Create and seed employees
        conn.execute(text(f"""
            CREATE TABLE employees (
                {pk_col},
                name VARCHAR(100) NOT NULL,
                department VARCHAR(50) NOT NULL,
                salary DECIMAL(10, 2) NOT NULL,
                hire_date {dt_type} NOT NULL
            );
        """))
        employees_data = [
            ("Sarah Connor", "Engineering", 145000.00, "2021-03-15"),
            ("James Miller", "Engineering", 132000.00, "2022-06-01"),
            ("Elena Rostova", "Engineering", 158000.00, "2020-01-10"),
            ("Michael Chang", "Engineering", 125000.00, "2023-02-20"),
            ("David Kim", "Product", 135000.00, "2021-09-12"),
            ("Priya Patel", "Product", 142000.00, "2022-04-18"),
            ("Marcus Vance", "Marketing", 95000.00, "2021-11-05"),
            ("Chloe Bennett", "Marketing", 88000.00, "2023-08-14"),
            ("Sophia Taylor", "Marketing", 102000.00, "2020-05-22"),
            ("Lucas Rossi", "Sales", 110000.00, "2021-07-19"),
            ("Olivia Martin", "Sales", 118000.00, "2022-10-03"),
            ("Liam Johnson", "Sales", 96000.00, "2023-03-29"),
            ("Noah Davis", "Finance", 128000.00, "2020-11-16"),
            ("Emma Wilson", "Finance", 134000.00, "2022-01-24"),
            ("Alexander Wright", "HR", 92000.00, "2021-04-08"),
            ("Grace Hall", "HR", 89000.00, "2023-05-15")
        ]
        for emp in employees_data:
            conn.execute(
                text("INSERT INTO employees (name, department, salary, hire_date) VALUES (:n, :d, :s, :h)"),
                {"n": emp[0], "d": emp[1], "s": emp[2], "h": emp[3]}
            )

        # Create and seed audit_logs (80 realistic records)
        conn.execute(text(f"""
            CREATE TABLE audit_logs (
                {pk_col},
                user_id INTEGER,
                action VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                ip_address VARCHAR(45) NOT NULL,
                timestamp {dt_type} NOT NULL
            );
        """))
        actions = ["USER_LOGIN", "EXPORT_REPORT", "QUERY_EXECUTION", "API_KEY_ROTATION", "SCHEMA_UPDATE", "FAILED_AUTH"]
        log_statuses = ["SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS", "FAILURE"]
        ips = ["192.168.1.45", "10.0.4.12", "172.16.0.88", "192.168.2.110"]
        now = datetime.now()

        for i in range(1, 81):
            user_id = random.randint(1, 12)
            action = random.choice(actions)
            l_status = "FAILURE" if action == "FAILED_AUTH" else random.choice(log_statuses)
            ip = random.choice(ips)
            log_time = now - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 1440))
            conn.execute(
                text("INSERT INTO audit_logs (user_id, action, status, ip_address, timestamp) VALUES (:u, :a, :s, :ip, :t)"),
                {"u": user_id, "a": action, "s": l_status, "ip": ip, "t": log_time.strftime("%Y-%m-%d %H:%M:%S")}
            )

        # Create and seed sales (160 completed transactions for backward compatibility)
        conn.execute(text(f"""
            CREATE TABLE sales (
                {pk_col},
                customer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                sale_date {dt_type} NOT NULL,
                status VARCHAR(20) DEFAULT 'Completed',
                region VARCHAR(50) NOT NULL
            );
        """))
        regions = ["North America", "Europe", "Asia-Pacific", "Latin America"]
        prod_prices = dict(zip(prod_df["product_id"], prod_df["unit_price"]))
        for i in range(1, 161):
            cid = random.randint(1, 12)
            pid = random.choice(list(prod_prices.keys()))
            qty = random.randint(1, 5)
            price = prod_prices[pid] * qty
            days_ago = random.randint(5, 500)
            s_date = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            reg = random.choice(regions)
            conn.execute(
                text("INSERT INTO sales (customer_id, product_id, quantity, total_price, sale_date, status, region) VALUES (:c, :p, :q, :t, :d, 'Completed', :r)"),
                {"c": cid, "p": pid, "q": qty, "t": price, "d": s_date.strftime("%Y-%m-%d %H:%M:%S"), "r": reg}
            )

        print("[SEED] Successfully seeded: customers (12), products (8), orders (30), order_items (55), payments (30), support_tickets (8), audit_logs (80), employees (16), sales (160).")

    try:
        from backend.app.services.schema_service import clear_schema_cache
        clear_schema_cache()
    except Exception:
        try:
            from app.services.schema_service import clear_schema_cache
            clear_schema_cache()
        except Exception:
            pass


if __name__ == "__main__":
    seed_database()
