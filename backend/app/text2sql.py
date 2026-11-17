"""
Schema-first Text-to-SQL generation and orchestration engine.
Supports Google Gemini, OpenAI, and a schema-grounded analytical fallback.
"""
import re
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
import httpx

from backend.app.config import (
    GEMINI_API_KEY as ENV_GEMINI_KEY,
    OPENAI_API_KEY as ENV_OPENAI_KEY,
    DEFAULT_PROVIDER
)
from backend.app.schema import get_database_schema, format_schema_for_prompt
from backend.app.sql_safety import (
    validate_safe_sql,
    extract_table_references,
    enforce_query_limit,
    sanitize_sql
)
from backend.app.db import execute_raw_sql

logger = logging.getLogger("text2sql.engine")

def is_audit_query(question: str) -> bool:
    """Check if the user is explicitly requesting audit logs or security trails."""
    q_lower = question.lower()
    return bool(re.search(r"\b(audit|audit_log|audit_logs|security logs?|system events?)\b", q_lower))

def build_system_prompt(schema_text: str) -> str:
    return f"""You are an expert SQL engineer. Your task is to generate valid SQLite / standard SQL queries based strictly on the user's natural language request and the database schema below.

DATABASE SCHEMA:
{schema_text}

STRICT GENERATION RULES:
1. Use ONLY the tables and columns explicitly listed in the schema. Do NOT invent columns or tables.
2. NEVER use a default table. Always choose tables based on user intent.
3. NEVER query 'audit_logs' unless the user question explicitly asks about audit logs.
4. When multiple tables are needed, JOIN them using the foreign key relationships shown above.
5. For aggregations (e.g. revenue, sales), sum price or unit_price * quantity appropriately.
6. For date-based aggregations (e.g. monthly revenue), use strftime('%Y-%m', date_column) for SQLite.
7. Return ONLY the raw SQL query inside a ```sql ... ``` code block. Do NOT include markdown explanations.
8. If the question refers to concepts/entities completely absent from the schema, output exactly:
   -- ERROR: Ambiguous or table not found in schema
"""

async def call_gemini_api(prompt: str, api_key: str) -> str:
    """Call Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 800}
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")
        return candidates[0]["content"]["parts"][0]["text"]

async def call_openai_api(system_prompt: str, user_prompt: str, api_key: str) -> str:
    """Call OpenAI API."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.0
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI API error ({resp.status_code}): {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]

def clean_sql_output(raw_output: str) -> str:
    """Extract SQL from markdown code fences or raw output."""
    if "-- ERROR:" in raw_output:
        return raw_output.strip()
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_output.strip()

def find_best_table_match(entity: str, candidates: List[str]) -> Optional[str]:
    """Find the best matching table for an entity name, prioritizing exact matches over substrings."""
    entity_clean = entity.lower().strip()
    entity_singular = entity_clean.rstrip("s")
    
    # 1. Exact match (e.g. 'orders' -> 'orders')
    for tbl in candidates:
        if tbl.lower() == entity_clean:
            return tbl
            
    # 2. Singular/plural match (e.g. 'order' -> 'orders')
    for tbl in candidates:
        if tbl.lower().rstrip("s") == entity_singular:
            return tbl
            
    # 3. Substring match, sorted by shortest length
    sorted_candidates = sorted(candidates, key=lambda x: len(x))
    for tbl in sorted_candidates:
        if entity_singular in tbl.lower().rstrip("s"):
            return tbl
    return None

def schema_grounded_fallback(question: str, schema_info: Dict[str, Any]) -> str:
    """
    Deterministic schema-first query planner for offline / local mode when LLM keys are absent.
    Understands intent, identifies tables/columns directly from active schema, and constructs valid SQL.
    """
    q = question.lower().strip()
    tables = schema_info.get("tables", {})
    available_table_names = list(schema_info.get("table_names", []))

    # Audit logs protection rule: audit_logs is selected ONLY when explicitly requested
    if "audit" in q or "log" in q:
        if "audit_logs" in available_table_names:
            limit_m = re.search(r"(?:limit|top|first)\s+(\d+)", q)
            lim = limit_m.group(1) if limit_m else "50"
            return f"SELECT * FROM audit_logs LIMIT {lim};"
        else:
            return "-- ERROR: audit_logs table not found in schema."

    # Prevent accidental audit_logs
    non_audit_tables = [t for t in available_table_names if t != "audit_logs"]

    # 1. Count questions: e.g. "how many customers", "count of orders"
    count_match = re.search(r"(?:how many|count (?:of )?|total number of)\s+([a-zA-Z0-9_]+)", q)
    if count_match:
        target_entity = count_match.group(1)
        matched_tbl = find_best_table_match(target_entity, non_audit_tables)
        if matched_tbl:
            return f"SELECT COUNT(*) AS total_count FROM {matched_tbl};"

    # 2. Count by status: e.g. "count orders by status", "orders by status"
    if "by status" in q or "group by status" in q:
        # Check if table name mentioned
        for word in q.split():
            matched_tbl = find_best_table_match(word, non_audit_tables)
            if matched_tbl and "status" in [c["name"].lower() for c in tables[matched_tbl]["columns"]]:
                return f"SELECT status, COUNT(*) AS count FROM {matched_tbl} GROUP BY status ORDER BY count DESC;"
        # Fallback to any table with status
        for tbl in non_audit_tables:
            col_names = [c["name"].lower() for c in tables[tbl]["columns"]]
            if "status" in col_names:
                return f"SELECT status, COUNT(*) AS count FROM {tbl} GROUP BY status ORDER BY count DESC;"

    # 3. Highest revenue product: e.g. "which product generated the highest revenue"
    if "highest revenue" in q or "top revenue" in q or "most revenue" in q or "top selling product" in q:
        if "order_items" in tables and "products" in tables:
            return (
                "SELECT p.id, p.name, SUM(oi.quantity * oi.unit_price) AS total_revenue "
                "FROM products p "
                "JOIN order_items oi ON p.id = oi.product_id "
                "GROUP BY p.id, p.name "
                "ORDER BY total_revenue DESC "
                "LIMIT 1;"
            )
        elif "orders" in tables and "total_amount" in [c["name"] for c in tables["orders"]["columns"]]:
            return "SELECT * FROM orders ORDER BY total_amount DESC LIMIT 1;"

    # 4. Monthly revenue / trends
    if "monthly" in q and ("revenue" in q or "sales" in q or "income" in q):
        if "orders" in tables:
            date_col = next((c["name"] for c in tables["orders"]["columns"] if "date" in c["name"].lower()), None)
            amt_col = next((c["name"] for c in tables["orders"]["columns"] if "amount" in c["name"].lower() or "price" in c["name"].lower()), None)
            if date_col and amt_col:
                return (
                    f"SELECT strftime('%Y-%m', {date_col}) AS month, SUM({amt_col}) AS monthly_revenue "
                    f"FROM orders "
                    f"GROUP BY month "
                    f"ORDER BY month ASC;"
                )

    # 5. Top N or First N items: e.g. "show the first 10 products", "top 5 customers"
    top_match = re.search(r"(?:first|top|limit)\s+(\d+)\s+([a-zA-Z0-9_]+)", q)
    if top_match:
        lim = top_match.group(1)
        entity = top_match.group(2)
        matched_tbl = find_best_table_match(entity, non_audit_tables)
        if matched_tbl:
            return f"SELECT * FROM {matched_tbl} LIMIT {lim};"

    # 6. Show all <entity>: e.g. "show all orders", "list products", "get customers"
    show_match = re.search(r"(?:show|list|get|display|view)\s+(?:all\s+)?([a-zA-Z0-9_]+)", q)
    if show_match:
        entity = show_match.group(1)
        matched_tbl = find_best_table_match(entity, non_audit_tables)
        if matched_tbl:
            return f"SELECT * FROM {matched_tbl};"

    # 7. Generic search for matching table in question words
    for word in q.split():
        clean_word = re.sub(r"[^\w]", "", word)
        if len(clean_word) < 3:
            continue
        matched_tbl = find_best_table_match(clean_word, non_audit_tables)
        if matched_tbl:
            return f"SELECT * FROM {matched_tbl} LIMIT 50;"

    # If no table matches the question intent at all
    return "-- ERROR: No matching table or columns found for this question in the database schema."

async def generate_sql_for_question(
    question: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None
) -> Tuple[str, str, Optional[str]]:
    """
    Orchestrate SQL generation using schema-first reasoning.
    Returns (sql_query, provider_used, error_if_any).
    """
    schema_info = get_database_schema(use_cache=True)
    if not schema_info.get("tables"):
        return "", "none", "The database contains no tables. Please upload a dataset or seed benchmark data."

    allows_audit = is_audit_query(question)
    excluded_tables = [] if allows_audit else ["audit_logs"]

    # Choose provider
    req_provider = (provider or DEFAULT_PROVIDER or "").lower()
    openai_key = api_key if req_provider == "openai" else ENV_OPENAI_KEY
    gemini_key = api_key if req_provider == "gemini" else ENV_GEMINI_KEY

    generated_sql = ""
    provider_used = "schema_fallback"
    error = None

    schema_prompt = format_schema_for_prompt(schema_info, excluded_tables=excluded_tables)
    system_prompt = build_system_prompt(schema_prompt)

    # 1. Try Gemini
    if req_provider == "gemini" and gemini_key:
        try:
            full_prompt = f"{system_prompt}\n\nUSER QUESTION: {question}\nSQL QUERY:"
            raw = await call_gemini_api(full_prompt, gemini_key)
            cleaned = clean_sql_output(raw)
            if cleaned.startswith("-- ERROR:"):
                return "", "gemini", cleaned.replace("-- ERROR:", "").strip()
            generated_sql = cleaned
            provider_used = "gemini"
        except Exception as e:
            logger.warning("Gemini API call failed (%s). Falling back to schema engine.", str(e))
            error = f"Gemini provider warning: {str(e)}"

    # 2. Try OpenAI
    elif req_provider == "openai" and openai_key:
        try:
            raw = await call_openai_api(system_prompt, question, openai_key)
            cleaned = clean_sql_output(raw)
            if cleaned.startswith("-- ERROR:"):
                return "", "openai", cleaned.replace("-- ERROR:", "").strip()
            generated_sql = cleaned
            provider_used = "openai"
        except Exception as e:
            logger.warning("OpenAI API call failed (%s). Falling back to schema engine.", str(e))
            error = f"OpenAI provider warning: {str(e)}"

    # 3. Fallback
    if not generated_sql:
        generated_sql = schema_grounded_fallback(question, schema_info)
        provider_used = "schema_grounded_fallback"

    if generated_sql.startswith("-- ERROR:"):
        err_msg = generated_sql.replace("-- ERROR:", "").strip()
        return "", provider_used, err_msg

    # Post-generation Schema and Security Guard
    referenced_tables = extract_table_references(generated_sql)
    all_known_tables = set(t.lower() for t in schema_info.get("table_names", []))

    for ref_tbl in referenced_tables:
        if ref_tbl not in all_known_tables:
            return "", provider_used, f"Generated SQL references nonexistent table '{ref_tbl}'."
        if ref_tbl == "audit_logs" and not allows_audit:
            return "", provider_used, "Security Guard: 'audit_logs' table cannot be queried unless explicitly requested."

    safe_sql = enforce_query_limit(generated_sql)
    return safe_sql, provider_used, None
