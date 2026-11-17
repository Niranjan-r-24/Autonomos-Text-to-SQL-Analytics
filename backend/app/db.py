"""
Database connection and session management module.
Compatible with SQLite (local development) and PostgreSQL (production).
"""
import time
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

def execute_raw_sql(sql: str, params: Dict[str, Any] = None) -> Tuple[List[str], List[Dict[str, Any]], float]:
    """
    Execute read-only SQL and return (columns, rows, execution_time_ms).
    """
    start_time = time.perf_counter()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys()) if result.returns_rows else []
        rows = [dict(row._mapping) for row in result.fetchall()] if result.returns_rows else []
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return columns, rows, duration_ms
