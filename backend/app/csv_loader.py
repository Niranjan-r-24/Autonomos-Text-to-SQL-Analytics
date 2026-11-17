"""
Dataset ingestion and dynamic table creation module.
Handles CSV upload, validation, schema type inference, table creation, and cache invalidation.
"""
import io
import re
from typing import Dict, Any, List, Tuple
import pandas as pd
from sqlalchemy import text
from backend.app.db import engine
from backend.app.schema import invalidate_schema_cache

RESERVED_SQL_WORDS = {
    "select", "table", "from", "where", "order", "group", "by", "limit", "join",
    "user", "index", "primary", "foreign", "key", "check", "default", "null"
}

def sanitize_identifier(name: str, default_prefix: str = "col") -> str:
    """
    Sanitize a table or column name into a safe, valid SQL identifier.
    """
    cleaned = re.sub(r"[^\w\s]", "", name).strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"{default_prefix}_{cleaned}"
        
    if cleaned in RESERVED_SQL_WORDS:
        cleaned = f"{cleaned}_tbl" if default_prefix == "tbl" else f"{cleaned}_col"
        
    return cleaned

def infer_sql_type(series: pd.Series) -> str:
    """
    Infer SQLite/PostgreSQL compatible data type from pandas Series.
    """
    non_null = series.dropna()
    if non_null.empty:
        return "TEXT"

    # Try numeric conversion
    if pd.api.types.is_integer_dtype(non_null):
        return "INTEGER"
    if pd.api.types.is_float_dtype(non_null):
        return "REAL"
    if pd.api.types.is_bool_dtype(non_null):
        return "INTEGER"

    # Check for datetime
    try:
        sample = non_null.iloc[:100]
        pd.to_datetime(sample, format="%Y-%m-%d", errors="raise")
        return "DATE"
    except Exception:
        pass

    try:
        sample = non_null.iloc[:100]
        pd.to_datetime(sample, errors="raise")
        return "DATETIME"
    except Exception:
        pass

    return "TEXT"

def load_csv_to_table(file_bytes: bytes, table_name: str, replace_existing: bool = True) -> Dict[str, Any]:
    """
    Parse CSV bytes, validate format, create table dynamically with inferred types,
    load records, and invalidate schema cache.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    # Try reading with utf-8, fallback to latin-1
    for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            break
        except Exception:
            continue
    else:
        raise ValueError("Could not decode CSV file. Please verify file encoding.")

    if df.empty or len(df.columns) == 0:
        raise ValueError("CSV contains no valid columns or data rows.")

    sanitized_table = sanitize_identifier(table_name, default_prefix="ds")

    # Sanitize and deduplicate column names
    seen_cols = set()
    col_mapping = {}
    col_types = []

    for orig_col in df.columns:
        s_col = sanitize_identifier(str(orig_col), default_prefix="c")
        base_col = s_col
        counter = 1
        while s_col in seen_cols:
            s_col = f"{base_col}_{counter}"
            counter += 1
        seen_cols.add(s_col)
        col_mapping[orig_col] = s_col

        sql_type = infer_sql_type(df[orig_col])
        col_types.append((s_col, sql_type))

    df_renamed = df.rename(columns=col_mapping)

    # Create table SQL
    cols_def = [f'"{col}" {stype}' for col, stype in col_types]
    create_sql = f'CREATE TABLE "{sanitized_table}" (\n  _row_id INTEGER PRIMARY KEY AUTOINCREMENT,\n  ' + ",\n  ".join(cols_def) + "\n);"

    with engine.begin() as conn:
        if replace_existing:
            conn.execute(text(f'DROP TABLE IF EXISTS "{sanitized_table}";'))
        conn.execute(text(create_sql))

    # Write data using pandas to_sql
    # Drop _row_id from insertion so AUTOINCREMENT fills it
    df_renamed.to_sql(
        name=sanitized_table,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000
    )

    # Invalidate cached schema so inspector catches new table immediately
    invalidate_schema_cache()

    return {
        "status": "success",
        "table_name": sanitized_table,
        "row_count": len(df),
        "columns": [{"name": c[0], "type": c[1]} for c in col_types]
    }
