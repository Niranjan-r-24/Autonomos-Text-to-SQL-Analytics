import os
import sys
import random
from datetime import datetime, timedelta

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
try:
    from backend.app.db.database import DATABASE_URL, engine
except ImportError:
    from app.db.database import DATABASE_URL, engine

def seed_database():
    """
    Creates and seeds enterprise analytics database with rich sample data:
    - customers
    - products
    - sales
    - audit_logs
    """
    print("[SEED] Seeding Enterprise Analytics Database...")

    with engine.connect() as conn:
        # Drop existing tables if re-seeding
        conn.execute(text("DROP TABLE IF EXISTS sales;"))
        conn.execute(text("DROP TABLE IF EXISTS audit_logs;"))
        conn.execute(text("DROP TABLE IF EXISTS customers;"))
        conn.execute(text("DROP TABLE IF EXISTS products;"))
        conn.commit()

        # 1. Create customers table
        conn.execute(text("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                company VARCHAR(100),
                country VARCHAR(50) NOT NULL,
                plan VARCHAR(20) DEFAULT 'Standard',
                total_spent DECIMAL(10, 2) DEFAULT 0.00,
                created_at DATETIME NOT NULL
            );
        """))

        # 2. Create products table
        conn.execute(text("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                stock_quantity INTEGER DEFAULT 100,
                rating DECIMAL(3, 2) DEFAULT 4.5
            );
        """))

        # 3. Create sales table
        conn.execute(text("""
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                sale_date DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'Completed',
                region VARCHAR(50) NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """))

        # 4. Create audit_logs table
        conn.execute(text("""
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                ip_address VARCHAR(45) NOT NULL,
                timestamp DATETIME NOT NULL
            );
        """))

        conn.commit()

        # Seed Products
        products_data = [
            ("Apex Cloud AI Platform", "Enterprise Software", 4999.00, 150, 4.9),
            ("Quantum Analytics Suite", "Enterprise Software", 2999.00, 200, 4.8),
            ("CyberShield Pro Security", "Security", 1499.00, 500, 4.7),
            ("DataPipe ETL Orchestrator", "Developer Tools", 899.00, 350, 4.6),
            ("Neural Search API", "AI & ML", 1299.00, 400, 4.85),
            ("Vortex Database Cluster", "Infrastructure", 3499.00, 100, 4.95),
            ("Echo Real-Time Monitor", "DevOps", 699.00, 600, 4.4),
            ("HyperScale Storage Node", "Infrastructure", 1999.00, 250, 4.65),
            ("SmartEdge IoT Gateway", "Hardware & Cloud", 1199.00, 180, 4.3),
            ("OmniChannel CRM Connector", "Integrations", 799.00, 450, 4.5)
        ]

        for prod in products_data:
            conn.execute(
                text("INSERT INTO products (name, category, price, stock_quantity, rating) VALUES (:n, :c, :p, :s, :r)"),
                {"n": prod[0], "c": prod[1], "p": prod[2], "s": prod[3], "r": prod[4]}
            )

        # Seed Customers
        companies = ["Acme Corp", "TechWave Inc", "GlobalLogistics", "Apex Systems", "Starlight Health", 
                     "Nexus Financial", "CyberDyn Solutions", "Optima Retail", "BioGen Labs", "Titan Aerospace",
                     "Vanguard Energy", "Horizon Media", "OmniTech Global", "Alpha Motors", "Synergy Telecom"]
        countries = ["United States", "United Kingdom", "Germany", "Canada", "Australia", "Japan", "France", "Singapore"]
        plans = ["Enterprise", "Professional", "Standard", "Starter"]

        customers_data = []
        now = datetime.now()
        for i in range(1, 41):
            comp = random.choice(companies)
            country = random.choice(countries)
            plan = random.choice(plans)
            created_days_ago = random.randint(30, 365)
            created_at = now - timedelta(days=created_days_ago)
            name = f"User {i} ({comp})"
            email = f"contact_{i}@{comp.lower().replace(' ', '')}.com"
            customers_data.append((name, email, comp, country, plan, 0.0, created_at.strftime("%Y-%m-%d %H:%M:%S")))

        for cust in customers_data:
            conn.execute(
                text("INSERT INTO customers (name, email, company, country, plan, total_spent, created_at) VALUES (:n, :e, :c, :co, :p, :t, :cr)"),
                {"n": cust[0], "e": cust[1], "c": cust[2], "co": cust[3], "p": cust[4], "t": cust[5], "cr": cust[6]}
            )

        # Seed Sales Transactions
        regions = ["North America", "Europe", "Asia-Pacific", "Latin America"]
        statuses = ["Completed", "Completed", "Completed", "Completed", "Pending", "Refunded"]

        sales_records = []
        customer_totals = {}

        for i in range(1, 151):
            cust_id = random.randint(1, 40)
            prod_id = random.randint(1, 10)
            prod_price = products_data[prod_id - 1][2]
            quantity = random.randint(1, 5)
            total_price = prod_price * quantity
            days_ago = random.randint(1, 180)
            sale_date = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            status = random.choice(statuses)
            region = random.choice(regions)

            sales_records.append((cust_id, prod_id, quantity, total_price, sale_date.strftime("%Y-%m-%d %H:%M:%S"), status, region))

            if status == "Completed":
                customer_totals[cust_id] = customer_totals.get(cust_id, 0.0) + total_price

        for sale in sales_records:
            conn.execute(
                text("INSERT INTO sales (customer_id, product_id, quantity, total_price, sale_date, status, region) VALUES (:c, :p, :q, :t, :d, :s, :r)"),
                {"c": sale[0], "p": sale[1], "q": sale[2], "t": sale[3], "d": sale[4], "s": sale[5], "r": sale[6]}
            )

        # Update customer total_spent
        for cid, spent in customer_totals.items():
            conn.execute(
                text("UPDATE customers SET total_spent = :s WHERE id = :i"),
                {"s": round(spent, 2), "i": cid}
            )

        # Seed Audit Logs
        actions = ["USER_LOGIN", "EXPORT_REPORT", "QUERY_EXECUTION", "API_KEY_ROTATION", "SCHEMA_UPDATE", "FAILED_AUTH"]
        log_statuses = ["SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS", "FAILURE"]
        ips = ["192.168.1.45", "10.0.4.12", "172.16.0.88", "192.168.2.110"]

        for i in range(1, 81):
            user_id = random.randint(1, 40)
            action = random.choice(actions)
            l_status = "FAILURE" if action == "FAILED_AUTH" else random.choice(log_statuses)
            ip = random.choice(ips)
            log_time = now - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 1440))

            conn.execute(
                text("INSERT INTO audit_logs (user_id, action, status, ip_address, timestamp) VALUES (:u, :a, :s, :ip, :t)"),
                {"u": user_id, "a": action, "s": l_status, "ip": ip, "t": log_time.strftime("%Y-%m-%d %H:%M:%S")}
            )

        conn.commit()
        print("[SEED] Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
