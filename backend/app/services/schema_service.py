"""
Schema Retrieval, Relational Linking, and Inspection Service.
Extracts table schemas, column data types, foreign key relationships, row counts,
and sample records from the active database with high-performance in-memory caching.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import inspect, text

try:
    from backend.app.db.database import engine
except ImportError:
    from app.db.database import engine

logger = logging.getLogger("text2sql.schema")

_SCHEMA_CACHE: Optional[Dict[str, Any]] = None
_RELATIONSHIPS_CACHE: Optional[List[Dict[str, str]]] = None


def clear_schema_cache() -> None:
    """Clears in-memory schema and relationship caches to force fresh reads on next request."""
    global _SCHEMA_CACHE, _RELATIONSHIPS_CACHE
    _SCHEMA_CACHE = None
    _RELATIONSHIPS_CACHE = None
    try:
        from backend.app.services.sql_generator import clear_distinct_cache
        clear_distinct_cache()
    except Exception:
        try:
            from app.services.sql_generator import clear_distinct_cache
            clear_distinct_cache()
        except Exception:
            pass
    logger.info("Schema and distinct values cache cleared.")


def detect_relationships(schema_info: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Discovers verified relational relationships and join paths across tables in schema_info.
    Combines formal database foreign keys with inferred entity identifier linkages.
    
    Returns:
        List of relationship dictionaries with:
        - from_table: str
        - from_column: str
        - to_table: str
        - to_column: str
        - join_clause: str
    """
    global _RELATIONSHIPS_CACHE
    if _RELATIONSHIPS_CACHE is not None:
        return _RELATIONSHIPS_CACHE

    relationships: List[Dict[str, str]] = []
    registered_pairs = set()

    # 1. Formal Foreign Keys from Database Inspector
    try:
        inspector = inspect(engine)
        for tbl in schema_info.keys():
            if tbl.lower() in ("sqlite_sequence", "audit_logs"):
                continue
            try:
                fks = inspector.get_foreign_keys(tbl)
                for fk in fks:
                    referred_table = fk.get("referred_table")
                    constrained_cols = fk.get("constrained_columns", [])
                    referred_cols = fk.get("referred_columns", [])
                    if referred_table and referred_table in schema_info and constrained_cols and referred_cols:
                        fc = constrained_cols[0]
                        tc = referred_cols[0]
                        pair_key = (tbl.lower(), fc.lower(), referred_table.lower(), tc.lower())
                        if pair_key not in registered_pairs:
                            registered_pairs.add(pair_key)
                            relationships.append({
                                "from_table": tbl,
                                "from_column": fc,
                                "to_table": referred_table,
                                "to_column": tc,
                                "join_clause": f"{tbl}.{fc} = {referred_table}.{tc}"
                            })
            except Exception:
                pass
    except Exception:
        pass

    # 2. Inferred Relationships based on relational column conventions
    business_tables = [t for t in schema_info.keys() if t.lower() not in ("sqlite_sequence", "audit_logs")]
    for t1 in business_tables:
        cols1 = {c["name"].lower(): c["name"] for c in schema_info[t1].get("columns", [])}
        for col1_l, col1_orig in cols1.items():
            if col1_l.endswith("_id") and col1_l != "id":
                entity = col1_l[:-3]
                for t2 in business_tables:
                    if t1 == t2:
                        continue
                    t2_l = t2.lower()
                    # Match target table: customer -> customers, product -> products, order -> orders
                    is_match = (
                        t2_l == entity
                        or t2_l == f"{entity}s"
                        or t2_l == f"{entity}es"
                        or (entity in t2_l and not t2_l.startswith("order_item"))
                    )
                    if is_match:
                        cols2 = {c["name"].lower(): c["name"] for c in schema_info[t2].get("columns", [])}
                        target_col = None
                        if col1_l in cols2:
                            target_col = cols2[col1_l]
                        elif "id" in cols2:
                            target_col = cols2["id"]
                        
                        if target_col:
                            pair_key = (t1.lower(), col1_orig.lower(), t2.lower(), target_col.lower())
                            if pair_key not in registered_pairs:
                                registered_pairs.add(pair_key)
                                relationships.append({
                                    "from_table": t1,
                                    "from_column": col1_orig,
                                    "to_table": t2,
                                    "to_column": target_col,
                                    "join_clause": f"{t1}.{col1_orig} = {t2}.{target_col}"
                                })

    _RELATIONSHIPS_CACHE = relationships
    return relationships


def get_db_schema_info(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Inspects the connected database and returns structured schema metadata.
    Uses in-memory caching for sub-millisecond execution on repeated requests.
    
    Returns:
        Dict mapping table names to column details, row count, sample records, and detected foreign keys.
    """
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is not None and not force_refresh:
        return _SCHEMA_CACHE

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

                # Fetch sample rows (up to 10) for grounding and dynamic value matching
                sample_rows: List[Dict[str, Any]] = []
                try:
                    res = conn.execute(text(f'SELECT * FROM "{table}" LIMIT 10'))
                    cols = list(res.keys())
                    sample_rows = [dict(zip(cols, row)) for row in res.fetchall()]
                except Exception as e:
                    logger.warning("Failed to fetch sample rows for table %s: %s", table, e)

                schema_info[table] = {
                    "columns": col_details,
                    "row_count": row_count,
                    "sample_rows": sample_rows
                }

        # Sort schema_info so uploaded custom tables appear first, canonical business tables next, audit_logs last
        canonical_order = ["customers", "products", "orders", "order_items", "payments", "support_tickets", "sales", "employees"]
        def _table_priority(tbl: str):
            tl = tbl.lower()
            if tl == "audit_logs":
                return (3, tl)
            if tl in canonical_order:
                return (1, canonical_order.index(tl))
            return (0, tl)

        sorted_keys = sorted(schema_info.keys(), key=_table_priority)
        ordered_schema_info = {k: schema_info[k] for k in sorted_keys}

        # Attach detected relationships
        rels = detect_relationships(ordered_schema_info)
        for tbl, meta in ordered_schema_info.items():
            meta["relationships"] = [r for r in rels if r["from_table"].lower() == tbl.lower() or r["to_table"].lower() == tbl.lower()]

        logger.info("Successfully retrieved schema for %d tables: %s", len(ordered_schema_info), list(ordered_schema_info.keys()))
        _SCHEMA_CACHE = ordered_schema_info
        return ordered_schema_info

    except Exception as e:
        logger.error("Error retrieving database schema: %s", str(e), exc_info=True)
        raise RuntimeError(f"Database schema retrieval failed: {str(e)}") from e


def format_schema_for_llm(schema_info: Dict[str, Any], active_table: Optional[str] = None) -> str:
    """
    Formats the schema metadata into a concise, clear prompt representation for the LLM.
    Includes explicit foreign-key relationships and safety boundaries around audit_logs.
    """
    ddl_lines: List[str] = []
    
    canonical_priority = ["customers", "products", "orders", "order_items", "payments", "support_tickets", "sales", "employees"]
    def table_sort_key(t: str):
        t_l = t.lower()
        if active_table and t_l == active_table.lower():
            return (0, 0)
        if t_l not in canonical_priority and t_l != "audit_logs":
            return (1, 0)
        if t_l in canonical_priority:
            return (2, canonical_priority.index(t_l))
        if t_l == "audit_logs":
            return (3, 0)
        return (4, t_l)

    # Exclude internal system/audit tables unless explicitly requested as active_table
    valid_tables = [
        t for t in schema_info.keys()
        if not (t.lower() in ("sqlite_sequence", "audit_logs") and (not active_table or active_table.lower() != t.lower()))
    ]
    sorted_tables = sorted(valid_tables, key=table_sort_key)

    for table_name in sorted_tables:
        meta = schema_info[table_name]
        is_active = " [CURRENT ACTIVE/UPLOADED DATASET]" if active_table and table_name.lower() == active_table.lower() else ""
        audit_note = " [INTERNAL SYSTEM AUDIT LOGS - NEVER QUERY FOR BUSINESS QUESTIONS]" if table_name.lower() == "audit_logs" else ""
        ddl_lines.append(f"Table: {table_name}{is_active}{audit_note} (Total Rows: {meta.get('row_count', 0)})")
        ddl_lines.append("Columns:")
        for col in meta.get("columns", []):
            pk = " [PRIMARY KEY]" if col.get("primary_key") else ""
            ddl_lines.append(f"  - {col['name']} ({col['type']}){pk}")
        
        sample_rows = meta.get("sample_rows", [])
        if sample_rows:
            ddl_lines.append("Sample Data:")
            for idx, row in enumerate(sample_rows[:3]):
                ddl_lines.append(f"  Row {idx + 1}: {row}")
        ddl_lines.append("")

    # Append Verified Relationships
    rels = detect_relationships(schema_info)
    if rels:
        ddl_lines.append("VERIFIED RELATIONSHIPS & JOIN CONDITIONS:")
        for r in rels:
            ddl_lines.append(f"  - {r['join_clause']}")
        ddl_lines.append("")

    return "\n".join(ddl_lines)
