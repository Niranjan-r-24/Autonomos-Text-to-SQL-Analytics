"""
Database schema inspection and metadata caching module.
Provides schema-first introspection for LLM grounding and UI schema viewer.
Reads directly from active database and persistent `datasets` registry.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from backend.app.db import engine
from backend.app.datasets import list_datasets

_schema_cache: Optional[Dict[str, Any]] = None

INTERNAL_TABLES = {"datasets", "_uploaded_files_catalog"}

def invalidate_schema_cache():
    """Invalidate cached schema metadata to force fresh database inspection."""
    global _schema_cache
    _schema_cache = None

def get_database_schema(use_cache: bool = True) -> Dict[str, Any]:
    """
    Introspect the current database tables, columns, primary keys, foreign keys,
    row counts, sample values, uploaded file catalog, and persistent datasets.
    """
    global _schema_cache
    if use_cache and _schema_cache is not None:
        return _schema_cache

    inspector = inspect(engine)
    all_raw_tables = inspector.get_table_names()

    # Filter internal catalog tables starting with '_' or 'datasets' from standard business table list
    table_names = [t for t in all_raw_tables if not t.startswith("_") and t.lower() not in INTERNAL_TABLES]

    # Fetch persistent datasets
    try:
        registered_datasets = list_datasets()
    except Exception:
        registered_datasets = []

    # Ensure all registered dataset tables are included in table_names
    for ds in registered_datasets:
        tbl = ds.get("table_name")
        if tbl and tbl not in table_names and tbl in all_raw_tables:
            table_names.append(tbl)

    schema_info: Dict[str, Any] = {
        "status": "success",
        "tables": {},
        "table_names": table_names,
        "relationships": [],
        "uploaded_files": [],
        "datasets": registered_datasets
    }

    # Fetch uploaded files catalog
    try:
        from backend.app.csv_loader import get_uploaded_files_catalog
        schema_info["uploaded_files"] = get_uploaded_files_catalog()
    except Exception:
        schema_info["uploaded_files"] = []

    with engine.connect() as conn:
        for table_name in table_names:
            columns_info = []
            try:
                columns = inspector.get_columns(table_name)
            except Exception:
                columns = []

            try:
                pk_constraint = inspector.get_pk_constraint(table_name)
                pk_columns = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
            except Exception:
                pk_columns = set()

            try:
                fks = inspector.get_foreign_keys(table_name)
            except Exception:
                fks = []

            for col in columns:
                col_name = col["name"]
                col_type = str(col["type"])
                columns_info.append({
                    "name": col_name,
                    "type": col_type,
                    "primary_key": col_name in pk_columns,
                    "nullable": col.get("nullable", True)
                })

            # Record foreign key relationships
            for fk in fks:
                schema_info["relationships"].append({
                    "from_table": table_name,
                    "from_column": fk.get("constrained_columns", [None])[0],
                    "to_table": fk.get("referred_table"),
                    "to_column": fk.get("referred_columns", [None])[0]
                })

            # Get row count
            try:
                count_res = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
                row_count = int(count_res) if count_res is not None else 0
            except Exception:
                row_count = 0

            # Get up to 3 sample rows
            sample_rows = []
            try:
                sample_res = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT 3'))
                sample_rows = [dict(r._mapping) for r in sample_res.fetchall()]
            except Exception:
                sample_rows = []

            schema_info["tables"][table_name] = {
                "name": table_name,
                "columns": columns_info,
                "row_count": row_count,
                "sample_rows": sample_rows,
                "foreign_keys": fks
            }

    _schema_cache = schema_info
    return schema_info

def format_schema_for_prompt(schema_info: Dict[str, Any], excluded_tables: Optional[List[str]] = None) -> str:
    """
    Format schema representation for LLM prompt context.
    Omits excluded tables (like audit_logs unless requested) and internal tables.
    """
    excluded = set(excluded_tables or [])
    lines = []
    
    for tbl_name, tbl_data in schema_info.get("tables", {}).items():
        if tbl_name in excluded or tbl_name.startswith("_") or tbl_name.lower() in INTERNAL_TABLES:
            continue
        cols_repr = [f"{c['name']} ({c['type']})" for c in tbl_data["columns"]]
        lines.append(f"Table: {tbl_name}")
        lines.append(f"  Columns: {', '.join(cols_repr)}")
        if tbl_data.get("sample_rows"):
            lines.append(f"  Sample row: {tbl_data['sample_rows'][0]}")

    if schema_info.get("relationships"):
        lines.append("\nRelationships (Foreign Keys):")
        for rel in schema_info["relationships"]:
            if rel["from_table"] not in excluded and rel["to_table"] not in excluded:
                lines.append(f"  {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")

    return "\n".join(lines)
