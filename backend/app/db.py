"""
Database connection and session management module.
Compatible with SQLite (local development) and PostgreSQL (production).
"""
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import DATABASE_URL, MAX_QUERY_LIMIT

# Engine configuration
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_engine():
    return engine

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def serialize_row_value(val: Any) -> Any:
    """Normalize row values into standard JSON-serializable types."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (bytes, bytearray)):
        return val.decode("utf-8", errors="replace")
    return val

def execute_raw_sql(sql: str, params: Dict[str, Any] = None) -> Tuple[List[str], List[Dict[str, Any]], float]:
    """
    Execute read-only SQL and return (columns, rows, execution_time_ms).
    Safely serializes rows into JSON-compatible values.
    """
    start_time = time.perf_counter()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys()) if result.returns_rows else []
        rows = [
            {k: serialize_row_value(v) for k, v in dict(row._mapping).items()}
            for row in result.fetchall()
        ] if result.returns_rows else []
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return columns, rows, duration_ms
