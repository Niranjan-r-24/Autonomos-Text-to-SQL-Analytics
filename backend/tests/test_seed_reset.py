from sqlalchemy import create_engine, inspect, text

from backend.app.db import seed as seed_module


def test_seed_database_removes_stale_uploaded_tables(tmp_path, monkeypatch):
    """A re-seed is a reset, so old uploaded/test tables must not survive it."""
    test_engine = create_engine(f"sqlite:///{tmp_path / 'analytics.db'}")
    monkeypatch.setattr(seed_module, "engine", test_engine)

    with test_engine.begin() as conn:
        conn.execute(text("CREATE TABLE stale_upload (id INTEGER PRIMARY KEY)"))

    seed_module.seed_database()

    table_names = set(inspect(test_engine).get_table_names())
    assert "stale_upload" not in table_names
    assert {
        "customers", "products", "orders", "order_items", "payments",
        "support_tickets", "audit_logs", "employees", "sales",
    }.issubset(table_names)
