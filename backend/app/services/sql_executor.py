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
try:
    from backend.app.db.database import engine
except ImportError:
    from app.db.database import engine

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


def validate_sql_against_live_schema(sql_query: str) -> Tuple[bool, Optional[str]]:
    """Preflight a read-only statement against the connected database.

    ``EXPLAIN QUERY PLAN`` makes SQLite resolve every referenced table and
    column without reading result rows.  This is deliberately shared by the
    generated and manually edited SQL paths so an uploaded schema is always
    the source of truth.
    """
    is_valid, validation_error = validate_safe_sql(sql_query)
    if not is_valid:
        return False, validation_error

    try:
        with engine.connect() as conn:
            conn.execute(text(f"EXPLAIN QUERY PLAN {sql_query.strip().rstrip(';')}"))
        return True, None
    except Exception as exc:
        return False, _format_friendly_db_error(str(exc), sql_query)


def _readonly_authorizer(action: int, arg1: Any, arg2: Any, db_name: Any, trigger_name: Any) -> int:
    """Enforces SQLite engine-level read-only permissions by denying any data-modifying action."""
    import sqlite3
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute_safe_query(sql_query: str) -> Dict[str, Any]:
    """
    Safely executes a read-only SQL query against the database engine with both
    AST/regex pre-validation and SQLite kernel-level authorization checks.
    
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

    # 2. Resolve tables and columns on the live connection before execution.
    # This catches stale/hallucinated schema references without ever returning
    # data from an unrelated fallback query.
    schema_valid, schema_error = validate_sql_against_live_schema(sql_query)
    if not schema_valid:
        exec_duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": exec_duration_ms,
            "error": schema_error,
        }

    # 3. Execute against SQLAlchemy engine with read-only authorizer
    try:
        with engine.connect() as conn:
            raw_conn = getattr(getattr(conn, "connection", None), "dbapi_connection", None)
            is_sqlite = hasattr(raw_conn, "set_authorizer")
            if is_sqlite:
                raw_conn.set_authorizer(_readonly_authorizer)

            try:
                result = conn.execute(text(sql_query))
                
                if result.returns_rows:
                    columns = list(result.keys())
                    raw_rows = result.fetchmany(1000)
                    rows = [dict(zip(columns, row)) for row in raw_rows]
                else:
                    columns = []
                    rows = []
            finally:
                if is_sqlite:
                    try:
                        raw_conn.set_authorizer(None)
                    except Exception:
                        pass

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
        logger.warning("SQL Execution Error in %.2f ms: %s | Query: %s", exec_duration_ms, raw_error, sql_query)

        # Level-0 Self-Healing for missing column names (e.g. p.name -> p.product_name, p.id -> p.product_id)
        if "no such column" in raw_error.lower():
            try:
                try:
                    from backend.app.services.schema_service import get_db_schema_info
                except ImportError:
                    from app.services.schema_service import get_db_schema_info
                schema_info = get_db_schema_info()

                healed_sql = sql_query
                if "products" in schema_info:
                    p_cols = {c["name"].lower(): c["name"] for c in schema_info["products"].get("columns", [])}
                    actual_name = next((p_cols[k] for k in ["product_name", "name", "title", "item_name"] if k in p_cols), None)
                    if actual_name and "name" not in p_cols:
                        healed_sql = re.sub(r"\b(?:p|products)\.name\b", f"p.{actual_name}", healed_sql, flags=re.IGNORECASE)
                        healed_sql = re.sub(r"\bproducts\.name\b", f"products.{actual_name}", healed_sql, flags=re.IGNORECASE)
                    actual_id = next((p_cols[k] for k in ["product_id", "id", "item_id"] if k in p_cols), None)
                    if actual_id and "id" not in p_cols:
                        healed_sql = re.sub(r"\b(?:p|products)\.id\b", f"p.{actual_id}", healed_sql, flags=re.IGNORECASE)
                        healed_sql = re.sub(r"\bproducts\.id\b", f"products.{actual_id}", healed_sql, flags=re.IGNORECASE)
                    actual_price = next((p_cols[k] for k in ["unit_price", "price", "retail_price", "cost"] if k in p_cols), None)
                    if actual_price and "price" not in p_cols:
                        healed_sql = re.sub(r"\b(?:p|products)\.price\b", f"p.{actual_price}", healed_sql, flags=re.IGNORECASE)
                    actual_stock = next((p_cols[k] for k in ["stock_qty", "stock_quantity", "stock"] if k in p_cols), None)
                    if actual_stock and "stock_quantity" not in p_cols:
                        healed_sql = re.sub(r"\b(?:p|products)\.stock_quantity\b", f"p.{actual_stock}", healed_sql, flags=re.IGNORECASE)

                if "customers" in schema_info:
                    c_cols = {c["name"].lower(): c["name"] for c in schema_info["customers"].get("columns", [])}
                    actual_c_name = next((c_cols[k] for k in ["customer_name", "name", "full_name"] if k in c_cols), None)
                    if actual_c_name and "name" not in c_cols:
                        healed_sql = re.sub(r"\b(?:c|customers)\.name\b", f"c.{actual_c_name}", healed_sql, flags=re.IGNORECASE)
                        healed_sql = re.sub(r"\bcustomers\.name\b", f"customers.{actual_c_name}", healed_sql, flags=re.IGNORECASE)
                    actual_c_id = next((c_cols[k] for k in ["customer_id", "id", "user_id"] if k in c_cols), None)
                    if actual_c_id and "id" not in c_cols:
                        healed_sql = re.sub(r"\b(?:c|customers)\.id\b", f"c.{actual_c_id}", healed_sql, flags=re.IGNORECASE)
                        healed_sql = re.sub(r"\bcustomers\.id\b", f"customers.{actual_c_id}", healed_sql, flags=re.IGNORECASE)

                if "orders" in schema_info:
                    o_cols = {c["name"].lower(): c["name"] for c in schema_info["orders"].get("columns", [])}
                    actual_o_id = next((o_cols[k] for k in ["order_id", "id"] if k in o_cols), None)
                    if actual_o_id and "id" not in o_cols:
                        healed_sql = re.sub(r"\b(?:o|orders)\.id\b", f"o.{actual_o_id}", healed_sql, flags=re.IGNORECASE)

                if "order_items" in schema_info:
                    oi_cols = {c["name"].lower(): c["name"] for c in schema_info["order_items"].get("columns", [])}
                    actual_oi_id = next((oi_cols[k] for k in ["order_item_id", "id"] if k in oi_cols), None)
                    if actual_oi_id and "id" not in oi_cols:
                        healed_sql = re.sub(r"\b(?:oi|order_items)\.id\b", f"oi.{actual_oi_id}", healed_sql, flags=re.IGNORECASE)

                healed_sql = re.sub(r"COUNT\s*\(\s*s\.id\s*\)", "COUNT(*)", healed_sql, flags=re.IGNORECASE)

                # Dynamic fuzzy fix for whatever column name failed
                col_match = re.search(r"no such column:\s*([a-zA-Z0-9_\.]+)", raw_error, re.IGNORECASE)
                if col_match:
                    bad_raw = col_match.group(1)
                    bad_base = bad_raw.split(".")[-1].lower()
                    for tname, tdata in schema_info.items():
                        all_t_cols = [c["name"] for c in tdata.get("columns", [])]
                        close = [c for c in all_t_cols if bad_base in c.lower() or c.lower() in bad_base]
                        if close:
                            replacement = close[0]
                            healed_sql = re.sub(r"\b" + re.escape(bad_raw) + r"\b", replacement if "." not in bad_raw else f"{bad_raw.split('.')[0]}.{replacement}", healed_sql)
                            break

                if healed_sql.strip() != sql_query.strip():
                    logger.info("execute_safe_query: Level-0 self-healed SQL '%s' -> '%s' and retrying", sql_query, healed_sql)
                    with engine.connect() as retry_conn:
                        retry_res = retry_conn.execute(text(healed_sql))
                        if retry_res.returns_rows:
                            cols = list(retry_res.keys())
                            r_rows = retry_res.fetchmany(1000)
                            ret_rows = [dict(zip(cols, r)) for r in r_rows]
                        else:
                            cols = []
                            ret_rows = []
                        exec_duration_ms = round((time.time() - start_time) * 1000, 2)
                        return {
                            "success": True,
                            "rows": ret_rows,
                            "columns": cols,
                            "row_count": len(ret_rows),
                            "execution_time_ms": exec_duration_ms,
                            "error": None
                        }
            except Exception as retry_err:
                logger.warning("execute_safe_query: Immediate retry after level-0 healing failed: %s", retry_err)

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
        try:
            from backend.app.services.schema_service import get_db_schema_info
            schema = get_db_schema_info()
            available = [t for t in schema.keys() if t.lower() != "sqlite_sequence"]
            if available:
                tables_list = ", ".join(available)
                return f"Database Error: Table '{table_name}' does not exist in the database. Connected tables: {tables_list}. Please verify the table name or check your schema."
        except Exception:
            pass
        return f"Database Error: Table '{table_name}' does not exist in the database. Please check the schema."

    if "no such column" in err_lower:
        match = re.search(r"no such column:\s*([a-zA-Z0-9_\.]+)", raw_error, re.IGNORECASE)
        col_name = match.group(1) if match else "unknown"
        return f"Database Error: Column '{col_name}' was not found. Please verify column names against the schema."

    if "syntax error" in err_lower:
        return f"SQL Syntax Error: The generated query contains invalid SQL syntax ({raw_error.split(']')[-1].strip()})."

    if "ambiguous column" in err_lower:
        return f"SQL Ambiguity Error: A column name is ambiguous across joined tables. Table prefixes are required."

    if "not authorized" in err_lower:
        return "Database Security Error: Operation is not authorized. Only read-only queries are permitted."

    if "operationalerror" in err_lower or "database is locked" in err_lower:
        return "Database Connection Error: The database is currently busy or unavailable. Please retry in a moment."

    return f"Execution Error: {raw_error.split(']')[-1].strip()}"
