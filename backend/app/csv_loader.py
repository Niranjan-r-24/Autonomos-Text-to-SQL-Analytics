"""
Dataset ingestion and dynamic table creation module.
Handles CSV upload, validation, schema type inference, table creation, and cache invalidation.
"""
import io
import re
from typing import Dict, Any, List, Tuple, Optional
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
        return "TIMESTAMP"
    except Exception:
        pass

    return "TEXT"

def parse_bytes_to_dataframe(file_bytes: bytes, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Robust multi-format dataset parser.
    Supports CSV, TSV, JSON, Excel (.xlsx, .xls), and delimited text.
    """
    fname = (filename or "").lower()

    # 1. Excel files
    if fname.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))

    # 2. JSON files
    if fname.endswith(".json") or file_bytes.strip().startswith((b"[", b"{")):
        try:
            return pd.read_json(io.BytesIO(file_bytes))
        except Exception:
            try:
                import json
                data = json.loads(file_bytes.decode("utf-8", errors="replace"))
                if isinstance(data, list):
                    return pd.json_normalize(data)
                elif isinstance(data, dict):
                    # Check if nested list inside dict (e.g. {"data": [...]})
                    for v in data.values():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            return pd.json_normalize(v)
                    return pd.json_normalize([data])
            except Exception:
                pass

    # 3. Delimited text (CSV, TSV, semicolon, pipe)
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        for sep in [None, ",", "\t", ";", "|"]:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, engine="python", encoding=encoding)
                if not df.empty and len(df.columns) > 0:
                    return df
            except Exception:
                continue

    # 4. Fallback: line-by-line text parsing
    text_str = file_bytes.decode("utf-8", errors="replace")
    lines = [line.strip() for line in text_str.splitlines() if line.strip()]
    if lines:
        return pd.DataFrame({"line_number": range(1, len(lines) + 1), "text": lines})

    raise ValueError("Could not parse file into a valid dataset table. Format not recognized.")

def load_csv_to_table(
    file_bytes: bytes,
    table_name: str,
    filename: Optional[str] = None,
    replace_existing: bool = True
) -> Dict[str, Any]:
    """
    Parse dataset bytes, validate format, create table dynamically with inferred types,
    load records, and invalidate schema cache.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    df = parse_bytes_to_dataframe(file_bytes, filename=filename)

    if df.empty or len(df.columns) == 0:
        raise ValueError("Uploaded dataset contains no valid rows or columns.")

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

    # Primary key and table definition
    pk_def = "_row_id INTEGER PRIMARY KEY" if engine.url.drivername.startswith("sqlite") else "_row_id SERIAL PRIMARY KEY"
    cols_def = [f'"{col}" {stype}' for col, stype in col_types]
    create_sql = f'CREATE TABLE "{sanitized_table}" (\n  {pk_def},\n  ' + ",\n  ".join(cols_def) + "\n);"

    with engine.begin() as conn:
        if replace_existing:
            cascade = " CASCADE" if not engine.url.drivername.startswith("sqlite") else ""
            conn.execute(text(f'DROP TABLE IF EXISTS "{sanitized_table}"{cascade};'))
        conn.execute(text(create_sql))

    # Write data using pandas to_sql
    # Drop _row_id from insertion so database sequence/rowid fills it
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
