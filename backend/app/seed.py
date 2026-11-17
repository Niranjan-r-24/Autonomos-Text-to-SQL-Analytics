"""
Database seeding module with benchmark data for testing and analytics demonstrations.
Satisfies exact benchmark counts:
- 12 Customers
- 8 Products
- 30 Orders with varied statuses and dates
- Order items linking orders to products
- 10 Audit logs
"""
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.app.db import engine

def seed_benchmark_data(force: bool = False):
    """
    Populate database with the benchmark enterprise schema and dataset.
    """
    with engine.begin() as conn:
        # Check existing tables
        if engine.url.drivername.startswith("sqlite"):
            rows = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
            existing_tables = {r[0].lower() for r in rows}
        else:
            rows = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")).fetchall()
            existing_tables = {r[0].lower() for r in rows}

        required_tables = {"customers", "products", "orders", "order_items", "audit_logs"}
        if required_tables.issubset(existing_tables) and not force:
            count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
            audit_count = conn.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
            if count == 12 and audit_count == 10:
                return {
                    "status": "already_seeded",
                    "customers": 12,
                    "products": 8,
                    "orders": 30,
                    "order_items": 30,
                    "audit_logs": 10
                }

        # Drop existing benchmark tables in correct dependency order
        cascade = " CASCADE" if not engine.url.drivername.startswith("sqlite") else ""
        for tbl in ["order_items", "orders", "products", "customers", "audit_logs"]:
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl}{cascade};"))

        # 1. Customers Table (12 rows)
        conn.execute(text("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                country TEXT NOT NULL,
                signup_date DATE NOT NULL
            );
        """))

        customers_data = [
            (1, "Alice Morgan", "alice.morgan@apexcorp.com", "USA", "2023-01-15"),
            (2, "Bob Vance", "bob.vance@vancerefrig.com", "USA", "2023-02-20"),
            (3, "Carlos Santana", "carlos.s@iberiaglobal.es", "Spain", "2023-03-11"),
            (4, "Deepa Sharma", "deepa.sharma@tatanet.in", "India", "2023-04-05"),
            (5, "Elena Rostova", "elena.r@nordik.se", "Sweden", "2023-05-18"),
            (6, "Frank Wright", "frank.w@architects.uk", "UK", "2023-06-22"),
            (7, "Grace Hopper", "grace.h@cyberlabs.us", "USA", "2023-07-09"),
            (8, "Hans Gruber", "hans.g@nakatomi.de", "Germany", "2023-08-30"),
            (9, "Ingrid Bergman", "ingrid@filmarts.se", "Sweden", "2023-09-14"),
            (10, "Jin Woo", "jin.woo@seoultech.kr", "South Korea", "2023-10-02"),
            (11, "Kavita Rao", "kavita.rao@bengalurulabs.in", "India", "2023-11-19"),
            (12, "Liam O'Connor", "liam.oc@dublindata.ie", "Ireland", "2023-12-01"),
        ]
        for row in customers_data:
            conn.execute(
                text("INSERT INTO customers (id, name, email, country, signup_date) VALUES (:id, :name, :email, :country, :signup_date)"),
                {"id": row[0], "name": row[1], "email": row[2], "country": row[3], "signup_date": row[4]}
            )

        # 2. Products Table (8 rows)
        conn.execute(text("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            );
        """))

        products_data = [
            (1, "Enterprise Cloud Suite", "Software", 1200.0, 50),
            (2, "AI Analytics Pro", "Software", 850.0, 80),
            (3, "Database Optimizer", "Software", 450.0, 100),
            (4, "Security Shield Appliance", "Hardware", 2500.0, 20),
            (5, "Developer Workstation", "Hardware", 3200.0, 15),
            (6, "Cloud Backup Vault", "Service", 300.0, 200),
            (7, "Dedicated Support Tier", "Service", 600.0, 90),
            (8, "IoT Gateway Controller", "Hardware", 750.0, 60),
        ]
        for row in products_data:
            conn.execute(
                text("INSERT INTO products (id, name, category, price, stock) VALUES (:id, :name, :category, :price, :stock)"),
                {"id": row[0], "name": row[1], "category": row[2], "price": row[3], "stock": row[4]}
            )

        # 3. Orders Table (30 rows)
        conn.execute(text("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date DATE NOT NULL,
                status TEXT NOT NULL,
                total_amount REAL NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
        """))

        orders_data = [
            (1, 1, "2024-01-10", "completed", 3200.0),
            (2, 2, "2024-01-14", "completed", 1200.0),
            (3, 3, "2024-01-20", "completed", 2500.0),
            (4, 4, "2024-02-02", "completed", 850.0),
            (5, 5, "2024-02-15", "completed", 6400.0),
            (6, 6, "2024-02-22", "shipped", 1500.0),
            (7, 7, "2024-03-05", "completed", 3200.0),
            (8, 8, "2024-03-12", "completed", 450.0),
            (9, 9, "2024-03-25", "cancelled", 1200.0),
            (10, 10, "2024-04-03", "completed", 2500.0),
            (11, 11, "2024-04-18", "shipped", 850.0),
            (12, 12, "2024-04-29", "completed", 9600.0),
            (13, 1, "2024-05-04", "completed", 600.0),
            (14, 2, "2024-05-17", "pending", 3200.0),
            (15, 3, "2024-05-28", "completed", 1200.0),
            (16, 4, "2024-06-08", "completed", 5000.0),
            (17, 5, "2024-06-19", "shipped", 750.0),
            (18, 6, "2024-06-30", "completed", 3200.0),
            (19, 7, "2024-07-04", "completed", 1700.0),
            (20, 8, "2024-07-15", "completed", 2500.0),
            (21, 9, "2024-07-26", "pending", 450.0),
            (22, 10, "2024-08-05", "completed", 3200.0),
            (23, 11, "2024-08-16", "completed", 600.0),
            (24, 12, "2024-08-28", "shipped", 1200.0),
            (25, 1, "2024-09-02", "completed", 6400.0),
            (26, 2, "2024-09-14", "completed", 2500.0),
            (27, 3, "2024-09-27", "cancelled", 850.0),
            (28, 4, "2024-10-06", "completed", 3200.0),
            (29, 5, "2024-10-18", "shipped", 1500.0),
            (30, 6, "2024-10-29", "pending", 600.0),
        ]
        for row in orders_data:
            conn.execute(
                text("INSERT INTO orders (id, customer_id, order_date, status, total_amount) VALUES (:id, :customer_id, :order_date, :status, :total_amount)"),
                {"id": row[0], "customer_id": row[1], "order_date": row[2], "status": row[3], "total_amount": row[4]}
            )

        # 4. Order Items Table
        conn.execute(text("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """))

        order_items_data = [
            (1, 1, 5, 1, 3200.0),
            (2, 2, 1, 1, 1200.0),
            (3, 3, 4, 1, 2500.0),
            (4, 4, 2, 1, 850.0),
            (5, 5, 5, 2, 3200.0),
            (6, 6, 8, 2, 750.0),
            (7, 7, 5, 1, 3200.0),
            (8, 8, 3, 1, 450.0),
            (9, 9, 1, 1, 1200.0),
            (10, 10, 4, 1, 2500.0),
            (11, 11, 2, 1, 850.0),
            (12, 12, 5, 3, 3200.0),
            (13, 13, 7, 1, 600.0),
            (14, 14, 5, 1, 3200.0),
            (15, 15, 1, 1, 1200.0),
            (16, 16, 4, 2, 2500.0),
            (17, 17, 8, 1, 750.0),
            (18, 18, 5, 1, 3200.0),
            (19, 19, 2, 2, 850.0),
            (20, 20, 4, 1, 2500.0),
            (21, 21, 3, 1, 450.0),
            (22, 22, 5, 1, 3200.0),
            (23, 23, 7, 1, 600.0),
            (24, 24, 1, 1, 1200.0),
            (25, 25, 5, 2, 3200.0),
            (26, 26, 4, 1, 2500.0),
            (27, 27, 2, 1, 850.0),
            (28, 28, 5, 1, 3200.0),
            (29, 29, 8, 2, 750.0),
            (30, 30, 7, 1, 600.0),
        ]
        for row in order_items_data:
            conn.execute(
                text("INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (:id, :order_id, :product_id, :quantity, :unit_price)"),
                {"id": row[0], "order_id": row[1], "product_id": row[2], "quantity": row[3], "unit_price": row[4]}
            )

        # 5. Audit Logs Table (10 rows)
        conn.execute(text("""
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY,
                action TEXT NOT NULL,
                user_id INTEGER,
                timestamp TIMESTAMP NOT NULL,
                details TEXT
            );
        """))

        audit_data = [
            (1, "LOGIN", 1, "2024-01-01 09:00:00", "User Alice logged in successfully"),
            (2, "UPDATE_PROFILE", 2, "2024-01-05 14:22:10", "Bob updated contact preferences"),
            (3, "PASSWORD_RESET", 3, "2024-01-12 11:15:00", "Password reset initiated via email"),
            (4, "ORDER_CREATED", 1, "2024-01-10 10:14:00", "Order #1 created"),
            (5, "PAYMENT_SUCCESS", 1, "2024-01-10 10:15:30", "Payment for order #1 settled"),
            (6, "EXPORT_REPORT", 7, "2024-02-14 16:45:12", "Monthly sales report exported"),
            (7, "API_KEY_ROTATED", 4, "2024-03-01 08:30:00", "Production API key rotated"),
            (8, "LOGIN_FAILED", 9, "2024-03-15 22:11:05", "Failed login attempt from IP 192.168.1.45"),
            (9, "SETTINGS_CHANGE", 10, "2024-04-10 13:00:00", "MFA enabled for account"),
            (10, "LOGOUT", 1, "2024-04-20 18:00:00", "Session expired cleanly"),
        ]
        for row in audit_data:
            conn.execute(
                text("INSERT INTO audit_logs (id, action, user_id, timestamp, details) VALUES (:id, :action, :user_id, :timestamp, :details)"),
                {"id": row[0], "action": row[1], "user_id": row[2], "timestamp": row[3], "details": row[4]}
            )

    return {
        "status": "seeded",
        "customers": 12,
        "products": 8,
        "orders": 30,
        "order_items": 30,
        "audit_logs": 10
    }

if __name__ == "__main__":
    result = seed_benchmark_data(force=True)
    print("Seed result:", result)
