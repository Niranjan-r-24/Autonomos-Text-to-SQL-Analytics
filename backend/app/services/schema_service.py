"""
Schema Retrieval and Inspection Service.
Extracts table schemas, column data types, row counts, and sample records from the active database.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy import inspect, text
try:
    from backend.app.db.database import engine
except ImportError:
    from app.db.database import engine

logger = logging.getLogger("text2sql.schema")

def get_db_schema_info() -> Dict[str, Any]:
    """
    Inspects the connected database and returns structured schema metadata.
    
    Returns:
        Dict mapping table names to column details, row count, and sample records.
    """
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        schema_info: Dict[str, Any] = {}
        with engine.connect() as conn:
            for table in table_names:
                # Skip internal sqlite system tables
                if table.startswith("sqlite_"):
                    continue

                columns = inspector.get_columns(table)
                col_details: List[Dict[str, Any]] = []
                for col in columns:
                    col_details.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "primary_key": col.get("primary_key", 0) > 0
                    })

                # Fetch row count
                row_count = 0
                try:
                    count_res = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                    row_count = count_res.scalar() or 0
                except Exception as e:
                    logger.warning("Failed to count rows for table %s: %s", table, e)

                # Fetch sample rows (up to 3) for grounding
                sample_rows: List[Dict[str, Any]] = []
                try:
                    res = conn.execute(text(f'SELECT * FROM "{table}" LIMIT 3'))
                    cols = list(res.keys())
                    sample_rows = [dict(zip(cols, row)) for row in res.fetchall()]
                except Exception as e:
                    logger.warning("Failed to fetch sample rows for table %s: %s", table, e)

                schema_info[table] = {
                    "columns": col_details,
                    "row_count": row_count,
                    "sample_rows": sample_rows
                }

        logger.info("Successfully retrieved schema for %d tables: %s", len(schema_info), list(schema_info.keys()))
        return schema_info

    except Exception as e:
        logger.error("Error retrieving database schema: %s", str(e), exc_info=True)
        raise RuntimeError(f"Database schema retrieval failed: {str(e)}") from e


def format_schema_for_llm(schema_info: Dict[str, Any]) -> str:
    """
    Formats the schema metadata into a concise, clear prompt representation for the LLM.
    """
    ddl_lines: List[str] = []
    for table_name, meta in schema_info.items():
        ddl_lines.append(f"Table: {table_name} (Total Rows: {meta.get('row_count', 0)})")
        ddl_lines.append("Columns:")
        for col in meta.get("columns", []):
            pk = " [PRIMARY KEY]" if col.get("primary_key") else ""
            ddl_lines.append(f"  - {col['name']} ({col['type']}){pk}")
        
        sample_rows = meta.get("sample_rows", [])
        if sample_rows:
            ddl_lines.append("Sample Data:")
            for idx, row in enumerate(sample_rows[:2]):
                ddl_lines.append(f"  Row {idx + 1}: {row}")
        ddl_lines.append("")
        
    return "\n".join(ddl_lines)
