"""
SQL Execution Service.
Safely executes validated SELECT queries against the database with execution timing,
strict security checks blocking data-modifying queries, and structured error handling.
"""
import re
import time
import logging
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy import text
from backend.app.db.database import engine

logger = logging.getLogger("text2sql.executor")

# Prohibited destructive and data-modifying SQL keywords
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "EXEC", "EXECUTE", "ATTACH", "DETACH",
    "GRANT", "REVOKE", "VACUUM", "PRAGMA", "COMMIT", "ROLLBACK"
]

def validate_safe_sql(sql_query: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that the SQL query is strictly a read-only SELECT statement.
    Allows standard SELECT and Common Table Expressions (WITH ... SELECT).
    
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not sql_query or not sql_query.strip():
        return False, "Query string is empty."

    cleaned_sql = sql_query.strip()
    
    # Remove leading comments if present
    cleaned_sql = re.sub(r"^--.*?\n", "", cleaned_sql, flags=re.MULTILINE).strip()
    cleaned_sql = re.sub(r"^/\*.*?\*/", "", cleaned_sql, flags=re.DOTALL).strip()

    # Query must start with SELECT, WITH, or EXPLAIN
    if not re.match(r"^(SELECT|WITH|EXPLAIN)\s+", cleaned_sql, re.IGNORECASE):
        return False, "Security Error: Only read-only SELECT queries are permitted. Modifying statements are blocked."

    # Check for forbidden destructive keywords using word boundaries
    upper_sql = cleaned_sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        # Match as whole standalone keyword to avoid false positives on column names like `created_at` or `updated_at`
        pattern = r"\b" + re.escape(kw) + r"\b"
        # If forbidden keyword is present and not part of allowed syntax (e.g. within string literal or table alias)
        if re.search(pattern, upper_sql):
            # Special check for INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE
            if kw in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]:
                logger.warning("Security Alert: Blocked attempted query containing forbidden keyword '%s': %s", kw, sql_query)
                return False, f"Security Violation: '{kw}' operations are strictly forbidden. Only read-only SELECT queries are allowed."

    # Reject multi-statement execution (semicolons separating queries)
    # Strip any trailing semicolon first
    sql_without_trailing_semicolon = cleaned_sql.rstrip(";\t\n\r ")
    if ";" in sql_without_trailing_semicolon:
        logger.warning("Security Alert: Multi-statement query blocked: %s", sql_query)
        return False, "Security Violation: Multi-statement queries are prohibited. Please provide a single SELECT statement."

    return True, None


def execute_safe_query(sql_query: str) -> Dict[str, Any]:
    """
    Safely executes a read-only SQL query against the database engine.
    
    Returns:
        Dict containing:
            - success (bool)
            - rows (List[Dict[str, Any]])
            - columns (List[str])
            - row_count (int)
            - execution_time_ms (float)
            - error (Optional[str])
    """
    start_time = time.time()
    
    # 1. Validate query safety
    is_valid, validation_error = validate_safe_sql(sql_query)
    if not is_valid:
        exec_duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.warning("SQL Validation Failed: %s | Query: %s", validation_error, sql_query)
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": exec_duration_ms,
            "error": validation_error
        }

    # 2. Execute against SQLAlchemy engine
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            
            if result.returns_rows:
                columns = list(result.keys())
                raw_rows = result.fetchall()
                # Format each row into a serializable dict
                rows = [dict(zip(columns, row)) for row in raw_rows]
            else:
                columns = []
                rows = []

        exec_duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "SQL Execution Successful: returned %d rows, %d columns in %.2f ms | Query: %s",
            len(rows), len(columns), exec_duration_ms, sql_query
        )
        return {
            "success": True,
            "rows": rows,
            "columns": columns,
            "row_count": len(rows),
            "execution_time_ms": exec_duration_ms,
            "error": None
        }

    except Exception as e:
        exec_duration_ms = round((time.time() - start_time) * 1000, 2)
        raw_error = str(e)
        friendly_error = _format_friendly_db_error(raw_error, sql_query)
        logger.error("SQL Execution Error in %.2f ms: %s | Query: %s", exec_duration_ms, raw_error, sql_query)
        
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": exec_duration_ms,
            "error": friendly_error
        }


def _format_friendly_db_error(raw_error: str, sql_query: str) -> str:
    """Formats raw database driver errors into clean, user-friendly messages."""
    err_lower = raw_error.lower()
    
    if "no such table" in err_lower:
        match = re.search(r"no such table:\s*([a-zA-Z0-9_\.]+)", raw_error, re.IGNORECASE)
        table_name = match.group(1) if match else "unknown"
        return f"Database Error: Table '{table_name}' does not exist in the database. Please check the schema."

    if "no such column" in err_lower:
        match = re.search(r"no such column:\s*([a-zA-Z0-9_\.]+)", raw_error, re.IGNORECASE)
        col_name = match.group(1) if match else "unknown"
        return f"Database Error: Column '{col_name}' was not found. Please verify column names against the schema."

    if "syntax error" in err_lower:
        return f"SQL Syntax Error: The generated query contains invalid SQL syntax ({raw_error.split(']')[-1].strip()})."

    if "ambiguous column" in err_lower:
        return f"SQL Ambiguity Error: A column name is ambiguous across joined tables. Table prefixes are required."

    if "operationalerror" in err_lower or "database is locked" in err_lower:
        return "Database Connection Error: The database is currently busy or unavailable. Please retry in a moment."

    return f"Execution Error: {raw_error.split(']')[-1].strip()}"
