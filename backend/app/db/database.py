import os
import sqlite3
from typing import Dict, List, Any, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Default SQLite database path in backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "enterprise_analytics.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def execute_query(sql_query: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    Executes raw SQL query against database.
    Returns: (rows as list of dicts, column_names, error_message if failed)
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            if result.returns_rows:
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows, columns, ""
            else:
                conn.commit()
                return [], [], ""
    except Exception as e:
        return [], [], str(e)

def get_db_schema_info() -> Dict[str, Any]:
    """
    Inspects database and returns detailed schema metadata including tables, columns, types, and sample data.
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    schema_info = {}
    with engine.connect() as conn:
        for table in table_names:
            columns = inspector.get_columns(table)
            col_details = []
            for col in columns:
                col_details.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "primary_key": col.get("primary_key", 0) > 0
                })
            
            # Fetch sample rows (up to 3) for LLM context grounding
            sample_rows = []
            try:
                res = conn.execute(text(f"SELECT * FROM {table} LIMIT 3"))
                cols = list(res.keys())
                sample_rows = [dict(zip(cols, r)) for r in res.fetchall()]
            except Exception:
                pass

            schema_info[table] = {
                "columns": col_details,
                "sample_rows": sample_rows,
                "row_count": get_table_row_count(conn, table)
            }
            
    return schema_info

def get_table_row_count(conn, table_name: str) -> int:
    try:
        res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return res.scalar() or 0
    except Exception:
        return 0

def format_schema_for_llm(schema_info: Dict[str, Any]) -> str:
    """
    Formats DB schema metadata into a clean Markdown/SQL DDL format for agent prompts.
    """
    ddl_lines = []
    for table_name, meta in schema_info.items():
        ddl_lines.append(f"Table: {table_name} (Row count: {meta['row_count']})")
        ddl_lines.append("Columns:")
        for col in meta["columns"]:
            pk_str = " [PRIMARY KEY]" if col["primary_key"] else ""
            ddl_lines.append(f"  - {col['name']} ({col['type']}){pk_str}")
        
        if meta["sample_rows"]:
            ddl_lines.append("Sample Data:")
            for idx, row in enumerate(meta["sample_rows"]):
                ddl_lines.append(f"  Row {idx+1}: {row}")
        ddl_lines.append("")
    return "\n".join(ddl_lines)
