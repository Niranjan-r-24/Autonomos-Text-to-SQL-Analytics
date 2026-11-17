"""
SQL safety, validation, and AST inspection module.
Ensures only read-only analytical queries (SELECT, CTEs) are executed.
"""
import re
from typing import Tuple, List, Set, Optional
from backend.app.config import MAX_QUERY_LIMIT

# Blocked operations and keywords
BLOCKED_PATTERNS = [
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    r"\b(ATTACH|DETACH|VACUUM|REINDEX)\b",
    r"\bPRAGMA\b",
    r"\bload_extension\b",
    r"\bINTO\s+OUTFILE\b",
    r"\bINTO\s+DUMPFILE\b",
]

def sanitize_sql(sql: str) -> str:
    """Strip SQL comments and leading/trailing whitespace."""
    if not sql:
        return ""
    # Remove single-line comments
    cleaned = re.sub(r"--[^\n]*", "", sql)
    # Remove multi-line comments
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()

def validate_safe_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a SQL statement is strictly read-only and analytical.
    Returns (is_safe, error_message).
    """
    clean = sanitize_sql(sql)
    if not clean:
        return False, "Query is empty."

    # Prevent multi-statement injection
    statements = [s.strip() for s in clean.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multi-statement queries are forbidden. Only single read-only queries are allowed."

    single_sql = statements[0]

    # Must start with SELECT or WITH
    if not re.match(r"^(SELECT|WITH)\b", single_sql, re.IGNORECASE):
        return False, "Only read-only SELECT or WITH (CTE) queries are permitted."

    # Check blocked keywords
    for pattern in BLOCKED_PATTERNS:
        match = re.search(pattern, single_sql, re.IGNORECASE)
        if match:
            return False, f"Prohibited SQL operation detected: '{match.group(0).upper()}'. Destructive queries are blocked."

    return True, None

def extract_cte_names(sql: str) -> Set[str]:
    """Find CTE alias names defined in WITH clauses."""
    ctes: Set[str] = set()
    clean = sanitize_sql(sql)
    matches = re.finditer(r"(?:WITH|,)\s+([a-zA-Z0-9_]+)\s+AS\s*\(", clean, re.IGNORECASE)
    for m in matches:
        ctes.add(m.group(1).lower())
    return ctes

def extract_table_references(sql: str) -> Set[str]:
    """
    Extract referenced physical table names from a SQL query.
    Filters out SQL keywords and CTE aliases.
    """
    clean = sanitize_sql(sql)
    cte_names = extract_cte_names(clean)
    tables: Set[str] = set()
    
    # Matches FROM <table> or JOIN <table>
    pattern = r"(?:FROM|JOIN)\s+([\"`']?([a-zA-Z0-9_]+)[\"`']?)"
    matches = re.finditer(pattern, clean, re.IGNORECASE)
    for m in matches:
        tbl = m.group(2).lower()
        if tbl not in {"select", "where", "group", "order", "limit", "with", "as", "on"}:
            if tbl not in cte_names:
                tables.add(tbl)

    return tables

def enforce_query_limit(sql: str, default_limit: int = 100, max_limit: int = MAX_QUERY_LIMIT) -> str:
    """
    Enforces a reasonable LIMIT clause if none is specified,
    and caps excessive limits to max_limit.
    """
    clean = sanitize_sql(sql).rstrip(";")
    limit_match = re.search(r"\bLIMIT\s+(\d+)\b", clean, re.IGNORECASE)
    
    if limit_match:
        current_limit = int(limit_match.group(1))
        if current_limit > max_limit:
            clean = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_limit}", clean, flags=re.IGNORECASE)
        return clean
    else:
        return f"{clean} LIMIT {default_limit}"
