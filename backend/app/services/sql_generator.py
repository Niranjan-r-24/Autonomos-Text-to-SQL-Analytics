"""
SQL and Query Explanation Generation Service.
Generates valid ANSI/SQLite SQL queries and plain-English explanations using LLMs
(Google Gemini, OpenAI) with a schema-first, intent-aware deterministic offline engine.
Specially optimized for custom uploaded datasets (.CSV, .XLSX, .JSON, .SQLITE) and multi-table schemas.
"""
import os
import re
import json
import logging
import httpx
from typing import Dict, Any, Tuple, Optional, List

try:
    from backend.app.services.schema_service import format_schema_for_llm, detect_relationships
    from backend.app.db.database import engine
except ImportError:
    from app.services.schema_service import format_schema_for_llm, detect_relationships
    try:
        from app.db.database import engine
    except Exception:
        engine = None

from sqlalchemy import text

logger = logging.getLogger("text2sql.generator")

_DISTINCT_CACHE: Dict[Tuple[str, str], List[str]] = {}


def clear_distinct_cache() -> None:
    """Clears the cached distinct column values to force fresh reads after uploads or re-seeding."""
    global _DISTINCT_CACHE
    _DISTINCT_CACHE.clear()
    logger.info("Distinct values cache cleared.")


def _get_column_distinct_values(table_name: str, col_name: str) -> List[str]:
    """Retrieves cached distinct text values from SQLite for smart intent filtering."""
    cache_key = (table_name.lower(), col_name.lower())
    if cache_key in _DISTINCT_CACHE:
        return _DISTINCT_CACHE[cache_key]

    vals: List[str] = []
    if engine is not None:
        try:
            with engine.connect() as conn:
                res = conn.execute(text(f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 40;'))
                vals = [str(r[0]).strip() for r in res.fetchall() if r[0] is not None and len(str(r[0]).strip()) >= 2]
        except Exception:
            pass
    _DISTINCT_CACHE[cache_key] = vals
    return vals


class SQLGenerator:
    """Generates SQL queries and plain-English query explanations from user natural language input."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.provider = (provider or "gemini").lower()
        self.api_key = api_key or (
            os.getenv("GEMINI_API_KEY") if "gemini" in self.provider else os.getenv("OPENAI_API_KEY")
        )

    @staticmethod
    def _has_cols(schema_info: Dict[str, Any], table_name: str, required_cols: List[str]) -> bool:
        """Verifies that table_name exists in schema_info and contains all required_cols."""
        if not schema_info or table_name not in schema_info:
            return False
        meta = schema_info[table_name]
        actual_cols = {c["name"].lower() for c in meta.get("columns", [])}
        return all(rc.lower() in actual_cols for rc in required_cols)

    @staticmethod
    def _resolve_col(schema_info: Dict[str, Any], table_name: str, candidate_names: List[str]) -> Optional[str]:
        """Finds the first existing column in table_name matching any candidate name (case-insensitive)."""
        if not schema_info or table_name not in schema_info:
            return None
        cols = {c["name"].lower(): c["name"] for c in schema_info[table_name].get("columns", [])}
        for cand in candidate_names:
            if cand.lower() in cols:
                return cols[cand.lower()]
        return None

    def generate(self, user_question: str, schema_info: Dict[str, Any], active_table: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Generates SQL query and explanation for the provided user question.
        """
        logger.info("Generating SQL for question: '%s' (active_table: %s, provider: %s)", user_question, active_table, self.provider)

        # Security/audit logs are an internal dataset.  Keep them out of the
        # generation context altogether unless the question explicitly asks
        # for audit/security activity.  This is stronger than trying to repair
        # an unrelated SQL statement after a model has already selected it.
        question_lower = user_question.lower()
        is_audit_question = any(re.search(rf"\b{re.escape(term)}\b", question_lower) for term in [
            "audit", "audit_log", "audit_logs", "audit log", "audit logs",
            "security log", "security logs", "security audit", "security event", "security events",
            "failed login", "failed logins", "ip address",
        ])
        generation_schema = schema_info if is_audit_question else {
            table: meta for table, meta in schema_info.items() if table.lower() != "audit_logs"
        }

        # Determine permitted tables and schema for generation
        permitted_tables: Optional[set] = None
        if active_table:
            atl = active_table.lower()
            if atl in ("audit_logs", "sqlite_sequence") and not is_audit_question:
                active_table = None
            elif atl in [t.lower() for t in schema_info.keys()]:
                matched_table = next(t for t in schema_info.keys() if t.lower() == atl)
                active_table = matched_table
                table_meta = schema_info[matched_table]
                permitted_tables = {matched_table}
                for rel in table_meta.get("relationships", []):
                    t_to = rel.get("to_table")
                    if t_to and t_to in schema_info and t_to.lower() not in ("audit_logs", "sqlite_sequence"):
                        permitted_tables.add(t_to)
                    t_from = rel.get("from_table")
                    if t_from and t_from in schema_info and t_from.lower() not in ("audit_logs", "sqlite_sequence"):
                        permitted_tables.add(t_from)
                generation_schema = {t: schema_info[t] for t in permitted_tables}
            else:
                active_table = None

        # 1. Attempt LLM generation if API key is present
        if self.api_key and self.provider != "fallback":
            try:
                llm_sql, llm_explanation = self._generate_with_llm(user_question, generation_schema, active_table=active_table)
                if llm_sql:
                    cleaned_sql = self._clean_sql(llm_sql, generation_schema, user_question)
                    is_valid_sql = bool(cleaned_sql)
                    if is_valid_sql and active_table and permitted_tables:
                        # SQL must reference active_table
                        if not self._sql_references_table(cleaned_sql, active_table):
                            logger.warning("Rejected LLM SQL because it does not reference active table '%s': %s", active_table, cleaned_sql)
                            is_valid_sql = False
                        else:
                            # Verify no unpermitted tables are queried
                            ref_tables = re.findall(r"\b(?:FROM|JOIN)\s+[\"`\[]?([a-zA-Z0-9_]+)[\"`\]]?", cleaned_sql, re.IGNORECASE)
                            for rt in ref_tables:
                                if rt.lower() not in [pt.lower() for pt in permitted_tables]:
                                    logger.warning("Rejected LLM SQL referencing unpermitted table '%s' (active: %s)", rt, active_table)
                                    is_valid_sql = False
                                    break
                    elif is_valid_sql:
                        mentioned_tables = self._explicit_schema_tables(user_question, generation_schema)
                        if not all(self._sql_references_table(cleaned_sql, table) for table in mentioned_tables):
                            is_valid_sql = False

                    if is_valid_sql:
                        provider_label = "Gemini 1.5 Flash" if "gemini" in self.provider else "OpenAI GPT-4o"
                        logger.info("Successfully generated SQL via %s: %s", provider_label, cleaned_sql)
                        return cleaned_sql, llm_explanation, provider_label
                    else:
                        logger.warning("LLM SQL rejected by schema/active-table validator, falling back to deterministic engine.")
            except Exception as e:
                logger.warning("LLM generation failed, falling back to deterministic engine: %s", str(e))

        # 2. Deterministic Rule-Based Fallback Engine
        sql, explanation = self._generate_deterministic(user_question, generation_schema, active_table=active_table)
        logger.info("Generated SQL via Deterministic Engine: %s", sql)
        return sql, explanation, "Deterministic Analytics Engine"

    @staticmethod
    def _explicit_schema_tables(user_question: str, schema_info: Dict[str, Any]) -> List[str]:
        """Return live-schema tables directly named by the user.

        Singular/plural forms are accepted, while identifiers are matched as
        tokens so ``order`` does not accidentally match ``preorder``.
        """
        tokens = set(re.findall(r"[a-z0-9_]+", user_question.lower()))
        matches: List[str] = []
        for table in schema_info:
            normalized = table.lower()
            forms = {normalized, normalized.rstrip("s")}
            if normalized.endswith("ies"):
                forms.add(normalized[:-3] + "y")
            if any(form and form in tokens for form in forms):
                matches.append(table)
        return matches

    @staticmethod
    def _sql_references_table(sql: str, table: str) -> bool:
        """Check a SQL FROM/JOIN reference without confusing column names."""
        quoted = re.escape(table)
        return bool(re.search(rf"\b(?:FROM|JOIN)\s+(?:[\"`\[]?{quoted}[\"`\]]?)\b", sql, re.IGNORECASE))

    def _generate_with_llm(self, user_question: str, schema_info: Dict[str, Any], active_table: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Invokes LLM API to generate JSON containing both SQL and explanation with strict ranking direction rules."""
        formatted_schema = format_schema_for_llm(schema_info, active_table=active_table)

        active_table_instruction = ""
        if active_table and active_table in schema_info:
            active_table_instruction = f"\nTARGET TABLE: The active dataset is '{active_table}'. Prioritize writing queries against '{active_table}' unless the question explicitly asks for another table.\n"

        system_prompt = f"""You are an expert SQL Developer and Database Architect.
Generate a standard SQLite/ANSI SQL query and a short, clear plain English explanation for the user question.

DATABASE SCHEMA AND RELATIONSHIPS:
{formatted_schema}
{active_table_instruction}
CRITICAL INTENT AND SCHEMA GROUNDING RULES:
1. STRICT SCHEMA GROUNDING (NEVER GUESS COLUMN NAMES):
   - You MUST ONLY query table names and column names that appear in the DATABASE SCHEMA above.
   - If 'products' has 'product_name' and 'product_id', you MUST use 'products.product_name' and 'products.product_id' (NEVER 'p.name' or 'p.id').
   - If 'customers' has 'customer_name' and 'customer_id', use 'customers.customer_name' and 'customers.customer_id'.

2. MULTI-TABLE RELATIONAL DATASETS (E-COMMERCE / ORDERS / TRANSACTIONS):
   - If 'order_items' and 'products' exist:
     Product revenue or sales volume queries MUST join 'order_items' and 'products' on 'order_items.product_id = products.product_id':
     SELECT p.product_name, SUM(oi.line_total) AS total_revenue, SUM(oi.quantity) AS total_units_sold
     FROM order_items oi
     JOIN products p ON oi.product_id = p.product_id
     GROUP BY p.product_id, p.product_name
     ORDER BY total_revenue DESC LIMIT 5;
   - If 'orders' and 'customers' exist: join on 'orders.customer_id = customers.customer_id'.
   - If 'orders' and 'order_items' exist: monthly revenue is:
     SELECT strftime('%Y-%m', o.order_date) AS sales_month, SUM(oi.line_total) AS monthly_revenue
     FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
     GROUP BY sales_month ORDER BY sales_month ASC;

3. DOMAIN & TABLE ROUTING RULES:
   - Questions about "customers", "users", "clients", "subscribers" (e.g., "How many customers are in the database?") MUST ALWAYS query the 'customers' table (e.g. SELECT COUNT(*) AS total_customers FROM customers;). NEVER query 'audit_logs'.
   - 'audit_logs' contains system security logs (actions, IP addresses, failures). NEVER query 'audit_logs' unless the user explicitly asks about audit logs, security events, logins, or IP addresses.
   - Questions about "products", "catalog", "items", "prices" MUST query the 'products' table.
   - Questions about "orders", "purchases", "order status" MUST query 'orders'.
   - Questions about nonexistent tables: Do NOT substitute another table. Return empty string for sql and clear error.

4. RANKING DIRECTION & LIMITS:
   - For "lowest", "bottom", "least", "cheapest", "worst", "minimum", "ascending", or "ASC": use ORDER BY <metric> ASC.
   - For "top", "highest", "most", "best", "greatest", "maximum", "descending", or "DESC": use ORDER BY <metric> DESC.
   - Respect requested limits: e.g., "Top 5" -> LIMIT 5, "first 10 rows" -> LIMIT 10.

5. SECURITY & READ-ONLY SAFETY:
   - Generate strictly read-only SELECT queries.
   - Always qualify column names with table prefixes in joins to avoid ambiguous column errors.

JSON Response Format:
{{
  "sql": "SELECT ...",
  "explanation": "Brief 1-2 sentence plain-English explanation of the query logic and filters."
}}"""

        if "gemini" in self.provider:
            models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [
                        {"role": "user", "parts": [{"text": f"{system_prompt}\n\nUSER QUESTION: \"{user_question}\""}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json"
                    }
                }
                try:
                    with httpx.Client(timeout=20) as client:
                        res = client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            parsed = json.loads(raw_text)
                            return parsed.get("sql"), parsed.get("explanation")
                        elif res.status_code in (404, 429, 503):
                            continue
                        else:
                            logger.error("Gemini API error (%d): %s", res.status_code, res.text)
                            break
                except Exception as e_gem:
                    logger.warning("Gemini model %s error: %s", model_name, str(e_gem))
                    continue

        elif "openai" in self.provider:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            with httpx.Client(timeout=8) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["choices"][0]["message"]["content"]
                    parsed = json.loads(raw_text)
                    return parsed.get("sql"), parsed.get("explanation")
                else:
                    logger.error("OpenAI API error (%d): %s", res.status_code, res.text)

        return None, None

    def _generate_deterministic(self, user_question: str, schema_info: Dict[str, Any], active_table: Optional[str] = None) -> Tuple[str, str]:
        """
        Provides high-precision, intent-aware deterministic SQL queries and explanations.
        Never defaults to audit_logs for business questions.
        Accurately generates multi-table queries, aggregations, groupings, and temporal trends.
        """
        q = user_question.lower()
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))

        # "all" is a request for the complete matching result set, not the
        # default preview.  A numeric limit still takes precedence.
        requests_all_rows = bool(re.search(r"\b(?:all|every|entire|full)\b", q))
        canonical_tables = {"sales", "products", "customers", "employees", "audit_logs", "sqlite_sequence", "order_items", "orders", "payments", "support_tickets"}

        is_postgres = (engine is not None and getattr(engine, "dialect", None) is not None and getattr(engine.dialect, "name", "") == "postgresql")

        # Step 0: Check if question specifically requests a NON-EXISTENT table
        stopwords = {
            "the", "a", "an", "all", "each", "this", "that", "these", "my", "our", "database",
            "data", "db", "here", "current", "active", "system", "first", "last", "top", "bottom",
            "any", "some", "every", "select", "where", "group", "order", "limit", "records",
            "rows", "items", "entries", "values", "details", "information", "info", "columns",
            "fields", "table", "tables", "chart", "graph", "analytics", "insights", "summary",
            "scratch", "file", "csv", "json", "sample", "view", "show", "display", "get", "fetch", "list", "see"
        }
        for pat in [r"\bfrom\s+([a-zA-Z0-9_]+)\b", r"\btable\s+([a-zA-Z0-9_]+)\b", r"\b([a-zA-Z0-9_]+)\s+table\b"]:
            m = re.search(pat, q)
            if m:
                cand = m.group(1).lower()
                if cand not in stopwords and len(cand) > 1:
                    exists_in_schema = any(
                        cand == t.lower() or cand.rstrip("s") == t.lower().rstrip("s")
                        for t in schema_info.keys()
                    )
                    if not exists_in_schema:
                        avail = [t for t in schema_info.keys() if t.lower() not in ("audit_logs", "sqlite_sequence")]
                        avail_str = ", ".join(avail) if avail else "none"
                        return (
                            f'SELECT * FROM "{m.group(1)}" LIMIT 10;',
                            f"Database Error: Table '{m.group(1)}' does not exist in the database. Connected tables: {avail_str}. Please verify the table name or check your schema."
                        )

        # Step 1: Direct Table Browse / First N Rows / Show All
        candidate_browse_tbl = None
        tbl_browse_match = re.search(r"(?:from|in|table)\s+[\"']?([a-zA-Z0-9_]+)[\"']?", q)
        if tbl_browse_match:
            candidate_tbl = tbl_browse_match.group(1).lower()
            if candidate_tbl not in ("the", "database", "data", "db", "this", "all", "our", "system"):
                matching_tbl = next((t for t in schema_info.keys() if t.lower() == candidate_tbl or t.lower().rstrip("s") == candidate_tbl.rstrip("s")), None)
                if matching_tbl and (
                    any(k in q for k in ["first", "sample", "all rows", "show rows", "show first", "browse", "records from", "rows from", "view", "display"])
                    or not any(k in q for k in ["where", "less", "greater", "more", "average", "avg", "count", "sum", "highest", "lowest", "by", ">", "<", "=", "top", "bottom", "how many", "number of", "total number", "how much", "what is the total", "trend", "revenue"])
                ):
                    candidate_browse_tbl = matching_tbl
        elif (
            any(k in q for k in ["give me all", "show all", "list all", "get all", "all ", "browse ", "display "])
            or q.startswith("show ") or q.startswith("list ") or q.startswith("all ") or q in [t.lower() for t in schema_info.keys()]
        ) and not any(k in q for k in ["where", "less", "greater", "more", "average", "avg", "count", "sum", "highest", "lowest", "by", ">", "<", "=", "top", "bottom", "revenue", "sales", "spend", "sold", "how many", "number of", "total number", "prices", "price"]):
            for t in schema_info.keys():
                tl = t.lower()
                if tl in ("sqlite_sequence", "audit_logs"):
                    continue
                if tl in q_tokens or tl in q or tl.rstrip("s") in q_tokens:
                    candidate_browse_tbl = t
                    break

        if candidate_browse_tbl:
            lim_m = re.search(r"\b(\d+)\b", q)
            has_all = any(k in q for k in ["all", "every", "full"]) and not lim_m
            if lim_m:
                lim = int(lim_m.group(1))
                limit_clause = f" LIMIT {lim}"
                limit_desc = f"first {lim} "
            elif has_all:
                limit_clause = ""
                limit_desc = "all "
            else:
                # A browse request without a numeric limit should expose the
                # actual table, not silently become a ten-row sample.
                limit_clause = ""
                limit_desc = "all "

            tbl_name_str = candidate_browse_tbl if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", candidate_browse_tbl) else f'"{candidate_browse_tbl}"'
            sql = f"SELECT * FROM {tbl_name_str}{limit_clause}"
            explanation = f"Retrieves {limit_desc}records from the '{candidate_browse_tbl}' table."
            return sql, explanation

        # Step 2: Table Intent Detection with Semantic Synonyms
        table_synonyms = {
            "customers": ["customer", "customers", "client", "clients", "user", "users", "buyer", "buyers", "subscriber", "subscribers", "account", "accounts", "member", "members"],
            "products": ["product", "products", "item", "items", "catalog", "catalogue", "merchandise", "goods"],
            "employees": ["employee", "employees", "staff", "worker", "workers", "headcount", "personnel", "engineer", "engineers", "salary", "salaries"],
            "order_items": ["order item", "order items", "line item", "line items", "order_item", "order_items"],
            "orders": ["order", "orders", "shipment", "shipments"],
            "payments": ["payment", "payments", "paid", "upi", "card"],
            "support_tickets": ["ticket", "tickets", "complaint", "complaints", "support", "support ticket"],
            "sales": ["sale", "sales", "transaction", "transactions", "purchase", "purchases"],
            "audit_logs": [
                "audit", "audits", "audit_log", "audit_logs", "audit log", "audit logs",
                "security log", "security logs", "security audit"
            ]
        }

        target_table_name = None
        canonical_tables = {"sales", "products", "customers", "employees", "audit_logs", "sqlite_sequence", "order_items", "orders", "payments", "support_tickets"}

        if active_table and active_table in schema_info and active_table.lower() not in ("sqlite_sequence", "audit_logs"):
            target_table_name = active_table
            # For custom uploaded datasets, route directly to dynamic synthesis for that table
            if active_table.lower() not in canonical_tables:
                return self._synthesize_dynamic_sql(user_question, schema_info, target_table=active_table)

        business_tables_syns = {k: v for k, v in table_synonyms.items() if k != "audit_logs"}
        for tbl, syns in business_tables_syns.items():
            if tbl in schema_info and any(s in q_tokens or f" {s} " in f" {q} " for s in syns):
                target_table_name = tbl
                break

        if not target_table_name:
            for tbl in schema_info.keys():
                tbl_l = tbl.lower()
                if tbl_l in ("sqlite_sequence", "audit_logs"):
                    continue
                if tbl_l in q_tokens or tbl_l in q or tbl_l.replace("_", " ") in q or tbl_l.rstrip("s") in q_tokens:
                    target_table_name = tbl
                    break

        if not target_table_name and "audit_logs" in schema_info:
            audit_syns = table_synonyms["audit_logs"]
            if any(s in q_tokens or f" {s} " in f" {q} " for s in audit_syns):
                target_table_name = "audit_logs"

        if not target_table_name and active_table and active_table in schema_info and active_table.lower() not in ("sqlite_sequence", "audit_logs"):
            target_table_name = active_table

        # Step 3: Entity Count Pattern ("How many customers are in the database?", "How many products?", "Count of orders")
        is_count_intent = (
            any(k in q for k in ["how many", "count of", "number of", "total number of", "total count of", "how many "])
            or ("count" in q and not any(k in q for k in ["by", "per", "group", "plan", "country", "status", "department", "category", "where", "order by"]))
        )
        if is_count_intent and not any(k in q for k in ["average", "avg", "highest", "lowest", "top", "bottom", "more than", "greater than", "less than", "between"]):
            if any(k in q for k in ["failed login", "failed logins", "security failure", "failed event"]) and "audit_logs" in schema_info:
                sql = "SELECT COUNT(*) AS total_failed_logins FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%';"
                explanation = "Calculates total count of failed login and error events in the 'audit_logs' table."
                return sql, explanation

            count_table = None
            alias = "total_count"
            if any(k in q for k in ["customer", "client", "user", "buyer", "subscriber", "member", "account"]):
                count_table = "customers" if "customers" in schema_info else target_table_name
                alias = "total_customers"
            elif any(k in q for k in ["employee", "staff", "worker", "personnel", "headcount", "salary", "salaries"]):
                count_table = "employees" if "employees" in schema_info else target_table_name
                alias = "total_employees"
            elif any(k in q for k in ["product", "item", "catalog"]):
                count_table = "products" if "products" in schema_info else target_table_name
                alias = "total_products"
            elif any(k in q for k in ["ticket", "complaint", "support"]):
                count_table = "support_tickets" if "support_tickets" in schema_info else target_table_name
                alias = "total_tickets"
            elif any(k in q for k in ["payment"]):
                count_table = "payments" if "payments" in schema_info else target_table_name
                alias = "total_payments"
            elif any(k in q for k in ["order"]):
                count_table = "orders" if "orders" in schema_info else target_table_name
                alias = "total_orders"
            elif any(k in q for k in ["sale", "transaction", "purchase"]):
                count_table = "sales" if "sales" in schema_info else target_table_name
                alias = "total_sales"
            elif any(k in q_tokens or f" {k} " in f" {q} " for k in ["audit", "audit_log", "audit_logs", "security_log"]):
                count_table = "audit_logs" if "audit_logs" in schema_info else target_table_name
                alias = "total_audit_logs"
            elif target_table_name and target_table_name.lower() != "audit_logs":
                count_table = target_table_name
                alias = f"total_{target_table_name}"

            if count_table and count_table in schema_info:
                tbl_str = count_table if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", count_table) else f'"{count_table}"'
                sql = f"SELECT COUNT(*) AS {alias} FROM {tbl_str}"
                explanation = f"Calculates total count of records in the '{count_table}' table."
                return sql, explanation

        # Step 4: Parse ranking direction and limit
        is_lowest = any(k in q for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "minimum", "fewest"
        ]) or bool(re.search(r"\bmin\b", q))
        is_highest = any(k in q for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "maximum"
        ]) or bool(re.search(r"\bmax\b", q))
        direction = "ASC" if is_lowest and not is_highest else "DESC"
        direction_word = "ascending" if direction == "ASC" else "descending"
        rank_label = "lowest" if direction == "ASC" else "top"

        limit_match = re.search(r"\b(?:top|bottom|lowest|highest|first|last|limit)\s*(\d+)\b", q)
        if not limit_match:
            limit_match = re.search(r"\b(\d+)\s*(?:rows?|records?|items?|entries|results?|products?|users?|customers?|employees?)\b", q)

        if limit_match:
            limit_val = int(limit_match.group(1))
            has_explicit_limit = True
        elif is_highest or is_lowest:
            limit_val = 5
            has_explicit_limit = True
        else:
            limit_val = 5
            has_explicit_limit = False

        limit_clause = f" LIMIT {limit_val}" if has_explicit_limit else ""

        # Step 5: Single aggregate KPI ("What is the total revenue?", "how much revenue")
        if (
            ("total revenue" in q or "overall revenue" in q or "what is the total revenue" in q or "how much revenue" in q or (("total" in q or "sum" in q or "how much" in q) and ("revenue" in q or "sales" in q)))
            and not any(k in q for k in ["product", "customer", "region", "month", "by", "plan", "department", "employee", "per"])
        ):
            if "order_items" in schema_info and self._resolve_col(schema_info, "order_items", ["line_total"]):
                sql = "SELECT SUM(line_total) AS total_revenue, COUNT(order_item_id) AS total_sales FROM order_items;"
                explanation = "Calculates overall total revenue across all transactions."
                return sql, explanation
            elif "sales" in schema_info and self._resolve_col(schema_info, "sales", ["total_price"]):
                sql = "SELECT SUM(total_price) AS total_revenue, COUNT(id) AS total_sales FROM sales WHERE status = 'Completed';"
                explanation = "Calculates overall total revenue across all completed sales transactions."
                return sql, explanation

        # Step 6: Multi-Table Relational E-Commerce Queries
        has_order_items = "order_items" in schema_info and "products" in schema_info
        p_id = self._resolve_col(schema_info, "products", ["product_id", "id", "item_id"])
        p_name = self._resolve_col(schema_info, "products", ["product_name", "name", "title"]) or p_id
        p_cat = self._resolve_col(schema_info, "products", ["category", "dept", "department"])
        p_price = self._resolve_col(schema_info, "products", ["unit_price", "price", "retail_price", "cost"])

        c_id = self._resolve_col(schema_info, "customers", ["customer_id", "id", "user_id"])
        c_name = self._resolve_col(schema_info, "customers", ["customer_name", "name", "full_name"]) or c_id

        # Pattern: List all products and their prices
        if any(k in q for k in ["list all products and their prices", "products and their prices", "product prices", "all products and prices"]):
            if "products" in schema_info:
                sql = f"SELECT {p_name}, {p_price} FROM products;"
                explanation = "Lists all products and their corresponding prices from the 'products' table."
                return sql, explanation

        # Pattern: Product Quantity Ranking using sales table (when quantity specifically requested and sales table exists)
        if (
            "sales" in schema_info and "products" in schema_info
            and any(k in q for k in ["product", "item"])
            and ("quantity" in q or "unit" in q or "sold the highest" in q or "sold the lowest" in q or "sold the most" in q)
            and not any(k in q for k in ["revenue", "dollar", "$", "price", "line_total", "spending"])
            and not any(k in q for k in ["customer", "employee", "ticket", "payment", "audit", "plan"])
        ):
            s_pid = self._resolve_col(schema_info, "sales", ["product_id", "id"])
            s_qty = self._resolve_col(schema_info, "sales", ["quantity", "qty"])
            if s_pid and s_qty and p_id:
                sql = (
                    f"SELECT p.{p_name} AS product_name, SUM(s.{s_qty}) AS total_quantity "
                    f"FROM sales s JOIN products p ON s.{s_pid} = p.{p_id} "
                    f"GROUP BY p.{p_id}, p.{p_name} "
                    f"ORDER BY total_quantity {direction}{limit_clause or ' LIMIT 3'};"
                )
                explanation = f"Joins 'sales' and 'products' to aggregate total quantity for {rank_label} products sorted in {direction_word} order."
                return sql, explanation

        # Pattern: Product Revenue / Quantity Ranking ("Which product has the highest revenue?", "top 5 revenue products", "Rank products")
        if (
            has_order_items
            and any(k in q for k in ["product", "item"])
            and (
                any(k in q for k in ["revenue", "sales", "sold", "quantity", "units", "qty", "turnover", "volume", "highest", "top", "lowest", "best"])
                or q.strip() in ["rank products", "top products", "product rankings", "best products"]
            )
            and not any(k in q for k in ["customer", "employee", "ticket", "payment", "audit", "plan"])
        ):
            oi_p_id = self._resolve_col(schema_info, "order_items", ["product_id", "item_id", "id"])
            oi_rev = self._resolve_col(schema_info, "order_items", ["line_total", "total_price", "amount", "revenue"])
            oi_qty = self._resolve_col(schema_info, "order_items", ["quantity", "qty", "units"])
            oi_price = self._resolve_col(schema_info, "order_items", ["unit_price", "price"])

            if p_id and oi_p_id:
                is_qty_ranking = ("quantity" in q or "volume" in q or "unit" in q or "sold" in q) and not ("revenue" in q or "sales" in q or "dollar" in q or "$" in q or "line_total" in q)
                cat_select = f", p.{p_cat}" if p_cat else ""
                cat_group = f", p.{p_cat}" if p_cat else ""

                rev_expr = f"SUM(oi.{oi_rev})" if oi_rev else (f"SUM(oi.{oi_qty} * oi.{oi_price})" if (oi_qty and oi_price) else f"COUNT(oi.{oi_p_id})")
                qty_expr = f"SUM(oi.{oi_qty})" if oi_qty else "COUNT(*)"

                order_metric = "total_units_sold" if is_qty_ranking else "total_revenue"
                metric_desc = "total units sold" if is_qty_ranking else "total revenue"

                sql = (
                    f"SELECT p.{p_name} AS product_name{cat_select}, "
                    f"{rev_expr} AS total_revenue, "
                    f"{qty_expr} AS total_units_sold "
                    f"FROM order_items oi "
                    f"JOIN products p ON oi.{oi_p_id} = p.{p_id} "
                    f"GROUP BY p.{p_id}, p.{p_name}{cat_group} "
                    f"ORDER BY {order_metric} {direction}{limit_clause or ' LIMIT 5'};"
                )
                default_prefix = ""
                if not is_qty_ranking and not any(k in q for k in ["revenue", "sales", "spending", "price", "line_total", "dollar", "$"]):
                    default_prefix = "Defaulted to total revenue as primary ranking metric; "
                explanation = (
                    f"{default_prefix}Joins 'order_items' and 'products' to aggregate {metric_desc} "
                    f"for {rank_label} products sorted in {direction_word} order."
                )
                return sql, explanation

        # Pattern: Fallback product revenue via sales table
        if (
            "sales" in schema_info and "products" in schema_info
            and any(k in q for k in ["product", "item"])
            and (
                any(k in q for k in ["revenue", "sales", "sold", "highest", "top", "lowest", "best"])
                or q.strip() in ["rank products", "top products", "product rankings", "best products"]
            )
            and not any(k in q for k in ["customer", "employee", "ticket", "payment", "audit", "plan"])
        ):
            s_pid = self._resolve_col(schema_info, "sales", ["product_id", "id"])
            s_rev = self._resolve_col(schema_info, "sales", ["total_price", "amount", "revenue"])
            if s_pid and s_rev and p_id:
                cat_select = f", p.{p_cat}" if p_cat else ""
                cat_group = f", p.{p_cat}" if p_cat else ""
                sql = (
                    f"SELECT p.{p_name} AS product_name{cat_select}, SUM(s.{s_rev}) AS total_revenue, COUNT(*) AS total_orders "
                    f"FROM sales s JOIN products p ON s.{s_pid} = p.{p_id} "
                    f"WHERE s.status = 'Completed' "
                    f"GROUP BY p.{p_id}, p.{p_name}{cat_group} "
                    f"ORDER BY total_revenue {direction}{limit_clause or ' LIMIT 5'};"
                )
                explanation = f"Defaulted to total revenue as primary ranking metric; aggregates completed sales for {rank_label} products."
                return sql, explanation

        # Pattern: Orders by Status ("Count orders by status", "breakdown of orders by status")
        if "orders" in schema_info and ("order" in q or "shipping" in q) and ("status" in q or "state" in q or "by status" in q or "breakdown" in q) and not any(k in q for k in ["product", "revenue", "item", "line_total"]):
            o_status = self._resolve_col(schema_info, "orders", ["status", "order_status", "state"])
            if o_status:
                sql = f'SELECT "{o_status}", COUNT(*) AS order_count FROM "orders" GROUP BY "{o_status}" ORDER BY order_count DESC;'
                explanation = f"Aggregates order volumes grouped by order status in descending order."
                return sql, explanation

        # Pattern: Monthly Revenue / Sales Trends ("Show monthly revenue", "Monthly sales trend", "Monthly sales trend by region")
        has_monthly_cues = any(k in q for k in ["month", "monthly", "trend", "over time", "sales trend", "by month"])
        if has_monthly_cues and any(k in q for k in ["revenue", "sales", "order", "income", "volume"]):
            has_region = "region" in q and ("sales" in schema_info or "customers" in schema_info)
            region_select = ", region" if has_region else ""
            region_group = ", region" if has_region else ""
            region_order = ", monthly_revenue DESC" if has_region else ""
            region_desc = " and geographical region" if has_region else ""

            year_match = re.search(r'\b(20\d\d)\b', q)
            year_val = year_match.group(1) if year_match else None

            # Check sales table if question explicitly mentions 'sales trend' or if order_items not present
            if "sales" in schema_info and ("sales trend" in q or "sales" in q or "order_items" not in schema_info):
                month_expr = "TO_CHAR(sale_date, 'YYYY-MM')" if is_postgres else "strftime('%Y-%m', sale_date)"
                where_clauses = ["status = 'Completed'"]
                if year_val:
                    if is_postgres:
                        where_clauses.append(f"TO_CHAR(sale_date, 'YYYY') = '{year_val}'")
                    else:
                        where_clauses.append(f"sale_date LIKE '{year_val}%'")
                where_str = f"WHERE {' AND '.join(where_clauses)} "
                sql = (
                    f"SELECT {month_expr} AS sales_month{region_select}, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions "
                    "FROM sales "
                    f"{where_str}"
                    f"GROUP BY sales_month{region_group} "
                    f"ORDER BY sales_month ASC{region_order};"
                )
                explanation = f"Extracts year and month from 'sale_date' in 'sales', grouping by month{region_desc} to calculate monthly revenue in chronological order."
                return sql, explanation

            elif "orders" in schema_info and "order_items" in schema_info:
                month_expr = "TO_CHAR(o.order_date, 'YYYY-MM')" if is_postgres else "strftime('%Y-%m', o.order_date)"
                where_str = ""
                if year_val:
                    if is_postgres:
                        where_str = f"WHERE TO_CHAR(o.order_date, 'YYYY') = '{year_val}' "
                    else:
                        where_str = f"WHERE o.order_date LIKE '{year_val}%' "
                sql = (
                    f"SELECT {month_expr} AS sales_month, SUM(oi.line_total) AS monthly_revenue, COUNT(DISTINCT o.order_id) AS total_orders "
                    f"FROM orders o JOIN order_items oi ON o.order_id = oi.order_id "
                    f"{where_str}"
                    "GROUP BY sales_month "
                    "ORDER BY sales_month ASC;"
                )
                explanation = "Aggregates revenue and order volume by month from 'orders' and 'order_items' in chronological order."
                return sql, explanation

        # Pattern: Customer Spending by Product Category (Multi-Table 3-Way Join)
        if (
            self._has_cols(schema_info, "sales", ["customer_id", "product_id", "total_price"])
            and "customers" in schema_info and "products" in schema_info
            and ("category" in q and ("spend" in q or "revenue" in q or "spent" in q or "plan" in q or "customer" in q))
        ):
            c_plan = self._resolve_col(schema_info, "customers", ["plan", "tier"]) or f"c.{c_name}"
            sql = (
                f"SELECT {c_plan}, p.{p_cat}, SUM(s.total_price) AS total_revenue, COUNT(*) AS sales_count "
                f"FROM sales s "
                f"JOIN customers c ON s.customer_id = c.{c_id} "
                f"JOIN products p ON s.product_id = p.{p_id} "
                f"WHERE s.status = 'Completed' "
                f"GROUP BY {c_plan}, p.{p_cat} "
                f"ORDER BY total_revenue DESC;"
            )
            explanation = "Performs a three-table join between sales, customers, and products to aggregate total revenue by customer plan and product category."
            return sql, explanation

        # Pattern: Average Order Value per Customer Plan (Multi-Table Join)
        if (
            self._has_cols(schema_info, "sales", ["customer_id", "total_price"])
            and "customers" in schema_info
            and "plan" in q
            and ("order value" in q or "aov" in q or ("order" in q and "avg" in q) or "average order" in q)
        ):
            sql = (
                f"SELECT c.plan, COUNT(s.id) AS order_count, AVG(s.total_price) AS avg_order_value, SUM(s.total_price) AS total_spent "
                f"FROM sales s "
                f"JOIN customers c ON s.customer_id = c.{c_id} "
                f"WHERE s.status = 'Completed' "
                f"GROUP BY c.plan "
                f"ORDER BY avg_order_value DESC;"
            )
            explanation = "Joins sales and customers by plan to calculate order count, average order value, and total spending per subscription tier."
            return sql, explanation

        # Pattern: Detailed Completed Sales with Customer and Product Names (Multi-Table 3-Way Join)
        if (
            self._has_cols(schema_info, "sales", ["customer_id", "product_id", "total_price", "sale_date"])
            and "customers" in schema_info and "products" in schema_info
            and ("completed sales" in q or "completed transactions" in q)
            and ("customer" in q and "product" in q)
        ):
            s_cid = self._resolve_col(schema_info, "sales", ["customer_id", "id"]) or "customer_id"
            s_pid = self._resolve_col(schema_info, "sales", ["product_id", "id"]) or "product_id"
            sql = (
                f"SELECT s.id, c.{c_name} AS customer_name, p.{p_name} AS product_name, s.total_price, s.sale_date "
                f"FROM sales s "
                f"JOIN customers c ON s.{s_cid} = c.{c_id} "
                f"JOIN products p ON s.{s_pid} = p.{p_id} "
                f"WHERE s.status = 'Completed' "
                f"ORDER BY s.sale_date DESC LIMIT 10;"
            )
            explanation = "Performs a three-table join across sales, customers, and products to list completed transactions with customer and product names."
            return sql, explanation

        # Pattern: Customer Orders / Spending Ranking ("Which customers placed the most orders?", "Top customers by total spending")
        is_cust_order_q = (
            "customers" in schema_info
            and ("customer" in q or "client" in q or "user" in q)
            and ("order" in q or "purchase" in q or "spent" in q or "spending" in q or "placed" in q or "most orders" in q)
            and not any(k in q for k in ["country", "plan", "status", "distribution"])
        )
        if is_cust_order_q:
            is_order_count_metric = any(k in q for k in ["most orders", "placed the most", "order count", "number of orders", "frequent", "highest orders"])
            if "orders" in schema_info:
                o_cid = self._resolve_col(schema_info, "orders", ["customer_id", "c_id", "id"])
                o_id = self._resolve_col(schema_info, "orders", ["order_id", "id"])
                has_items = "order_items" in schema_info
                oi_oid = self._resolve_col(schema_info, "order_items", ["order_id", "o_id"]) if has_items else None
                oi_total = self._resolve_col(schema_info, "order_items", ["line_total", "total_price", "amount"]) if has_items else None

                if o_cid and o_id and has_items and oi_oid and oi_total and not is_order_count_metric:
                    sql = (
                        f"SELECT c.{c_name} AS customer_name, SUM(oi.{oi_total}) AS total_spent, COUNT(DISTINCT o.{o_id}) AS total_orders "
                        f"FROM customers c "
                        f"JOIN orders o ON c.{c_id} = o.{o_cid} "
                        f"JOIN order_items oi ON o.{o_id} = oi.{oi_oid} "
                        f"GROUP BY c.{c_id}, c.{c_name} "
                        f"ORDER BY total_spent {direction}{limit_clause or ' LIMIT 5'};"
                    )
                    explanation = f"Joins 'customers', 'orders', and 'order_items' to rank customers by total spending in {direction_word} order."
                    return sql, explanation
                elif o_cid and o_id:
                    sql = (
                        f"SELECT c.{c_name} AS customer_name, COUNT(DISTINCT o.{o_id}) AS total_orders "
                        f"FROM customers c "
                        f"JOIN orders o ON c.{c_id} = o.{o_cid} "
                        f"GROUP BY c.{c_id}, c.{c_name} "
                        f"ORDER BY total_orders {direction}{limit_clause or ' LIMIT 5'};"
                    )
                    explanation = f"Joins 'customers' and 'orders' to identify customers who placed the most orders in {direction_word} order."
                    return sql, explanation

            c_spent = self._resolve_col(schema_info, "customers", ["total_spent", "spent", "spending"])
            if c_spent:
                sql = f"SELECT {c_name} AS customer_name, {c_spent} FROM customers ORDER BY {c_spent} {direction}{limit_clause or ' LIMIT 5'};"
                explanation = f"Retrieves customers ranked by {c_spent} in {direction_word} order."
                return sql, explanation

        # Pattern: Compare Revenue by Region ("Compare revenue by region", "Sales by region")
        if any(k in q for k in ["region", "by region"]) and any(k in q for k in ["revenue", "sales", "compare", "performance"]):
            c_reg = self._resolve_col(schema_info, "customers", ["region", "state", "city"])
            if c_reg and "orders" in schema_info and "order_items" in schema_info:
                o_cid = self._resolve_col(schema_info, "orders", ["customer_id", "c_id", "id"])
                o_id = self._resolve_col(schema_info, "orders", ["order_id", "id"])
                oi_oid = self._resolve_col(schema_info, "order_items", ["order_id", "o_id"])
                oi_total = self._resolve_col(schema_info, "order_items", ["line_total", "total_price", "amount"])
                if o_cid and o_id and oi_oid and oi_total:
                    sql = (
                        f"SELECT c.{c_reg} AS region, SUM(oi.{oi_total}) AS total_revenue, COUNT(DISTINCT o.{o_id}) AS total_orders "
                        f"FROM customers c "
                        f"JOIN orders o ON c.{c_id} = o.{o_cid} "
                        f"JOIN order_items oi ON o.{o_id} = oi.{oi_oid} "
                        f"GROUP BY c.{c_reg} "
                        f"ORDER BY total_revenue DESC;"
                    )
                    explanation = "Joins 'customers', 'orders', and 'order_items' to aggregate total revenue by customer region in descending order."
                    return sql, explanation

            if "sales" in schema_info:
                s_reg = self._resolve_col(schema_info, "sales", ["region", "country"])
                s_rev = self._resolve_col(schema_info, "sales", ["total_price", "amount", "revenue"])
                if s_reg and s_rev:
                    sql = (
                        f"SELECT {s_reg} AS region, SUM({s_rev}) AS total_revenue, COUNT(*) AS total_sales "
                        f"FROM sales "
                        f"WHERE status = 'Completed' "
                        f"GROUP BY {s_reg} "
                        f"ORDER BY total_revenue DESC;"
                    )
                    explanation = "Aggregates completed sales revenue across geographical regions in descending order."
                    return sql, explanation

        # Pattern: Compare Departments
        if self._has_cols(schema_info, "employees", ["department", "salary"]) and ("compare" in q or " vs " in q or "between" in q) and ("dept" in q or "department" in q or "salary" in q):
            depts = [d for d in ["Engineering", "Product", "Marketing", "Sales", "Finance", "HR"] if d.lower() in q]
            if len(depts) >= 2:
                d_in = ", ".join([f"'{d}'" for d in depts])
                sql = (
                    f"SELECT department, AVG(salary) AS avg_salary, COUNT(id) AS employee_count "
                    f"FROM employees WHERE department IN ({d_in}) "
                    f"GROUP BY department ORDER BY avg_salary DESC;"
                )
                explanation = f"Compares average salary and employee count between the {', '.join(depts)} departments."
                return sql, explanation

        # Pattern: Audit Logs ("Show audit logs", "Show security logs", "Failed audit log events")
        is_explicit_audit = any(k in q_tokens or f" {k} " in f" {q} " for k in [
            "audit", "audit_log", "audit_logs", "audit logs",
            "security log", "security logs", "security event", "security events", "security audit"
        ])
        if is_explicit_audit and "audit_logs" in schema_info:
            has_fail_intent = any(k in q for k in ["fail", "failed", "error", "errors", "issue"])
            lim = limit_val if has_explicit_limit else 10
            if has_fail_intent:
                if ("action" in q and ("ip" in q or "address" in q)) or q.strip() == "failed audit log events":
                    sql = "SELECT action, status, ip_address, COUNT(id) AS event_count, MAX(timestamp) AS last_occurred FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%' GROUP BY action, status, ip_address ORDER BY event_count DESC LIMIT 10;"
                    explanation = "Queries the 'audit_logs' table for security events with failure status, grouping by action and IP address."
                else:
                    sql = f"SELECT id, action, status, user_id, ip_address, timestamp FROM audit_logs WHERE status = 'FAILURE' OR action LIKE '%FAIL%' ORDER BY timestamp DESC LIMIT {lim};"
                    explanation = f"Retrieves the {lim} most recent failed audit and security event records."
            else:
                sql = f"SELECT id, action, status, user_id, ip_address, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT {lim};"
                explanation = f"Retrieves the {lim} most recent audit log event records from the 'audit_logs' table."
            return sql, explanation

        # Pattern: Employees ranking by salary or department salary
        if self._has_cols(schema_info, "employees", ["name", "department", "salary"]) and (
            any(k in q for k in ["employee", "staff", "worker", "salary", "paid", "compensation", "earn", "earning"])
        ):
            if any(k in q for k in ["department", "dept"]) and any(k in q for k in ["avg", "average", "mean"]):
                sql = "SELECT department, AVG(salary) AS avg_salary, COUNT(id) AS employee_count FROM employees GROUP BY department ORDER BY avg_salary DESC;"
                explanation = "Groups employees by department to compute average salary and headcount."
                return sql, explanation
            else:
                sql = f"SELECT name, department, salary FROM employees ORDER BY salary {direction}{limit_clause};"
                explanation = f"Retrieves employees ranked by salary in {direction_word} order."
                return sql, explanation

        # Step 7: Dynamic Schema Synthesizer for arbitrary databases and custom tables
        return self._synthesize_dynamic_sql(user_question, schema_info, target_table=target_table_name)

    def _synthesize_dynamic_sql(self, user_question: str, schema_info: Dict[str, Any], target_table: Optional[str] = None) -> Tuple[str, str]:
        """
        Dynamically synthesizes schema-grounded SQL for arbitrary databases and custom tables.
        Handles numeric comparisons, text filters, aggregations, group-bys, and ranked limits accurately.
        """
        if not schema_info:
            return "", "Unable to generate query: No database schema provided."

        q = user_question.lower()
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))

        # Preserve an explicit request for the complete result set instead of
        # silently turning it into the default ten-row preview.
        requests_all_rows = bool(re.search(r"\b(?:all|every|entire|full)\b", q))

        # 1. Ranking Direction & Limits
        is_lowest = any(k in q for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "minimum", "fewest"
        ]) or bool(re.search(r"\bmin\b", q))
        is_highest = any(k in q for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "maximum"
        ]) or bool(re.search(r"\bmax\b", q))
        direction = "ASC" if is_lowest and not is_highest else "DESC"
        direction_word = "ascending" if direction == "ASC" else "descending"

        limit_match = re.search(r"\b(?:top|bottom|lowest|highest|first|last|limit)\s*(\d+)\b", q)
        if not limit_match:
            limit_match = re.search(r"\b(\d+)\s*(?:rows?|records?|items?|entries|results?|products?|cars?|students?|employees?|users?)\b", q)

        if limit_match:
            num = int(limit_match.group(1))
            comp_match = re.search(r"(?:>=|<=|>|<|=|!=|greater than|less than|above|below|over|under)\s*" + str(num), q)
            if not comp_match and num < 5000 and num not in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
                limit_val = num
                has_explicit_limit = True
            else:
                limit_val = 5 if (is_highest or is_lowest) else 10
                has_explicit_limit = False
        elif is_highest or is_lowest:
            limit_val = 5
            has_explicit_limit = True
        else:
            limit_val = 10
            has_explicit_limit = False

        if requests_all_rows and not limit_match:
            has_explicit_limit = False

        # 2. Multi-Factor Table Resolution
        stopwords_score = {
            "the", "a", "an", "all", "each", "this", "that", "these", "my", "our", "database",
            "data", "db", "here", "current", "active", "system", "first", "last", "top", "bottom",
            "any", "some", "every", "select", "where", "group", "order", "limit", "records",
            "rows", "items", "entries", "values", "details", "information", "info", "columns",
            "fields", "table", "tables", "show", "display", "view", "get", "fetch", "list", "see",
            "id", "status"
        }
        if (
            not target_table
            or target_table not in schema_info
            or (target_table.lower() == "audit_logs" and not any(k in q_tokens or f" {k} " in f" {q} " for k in ["audit", "audit_log", "audit_logs"]))
        ):
            scores = {}
            for tbl_name, meta in schema_info.items():
                tbl_clean = tbl_name.lower()
                if tbl_clean == "sqlite_sequence":
                    continue
                score = 0

                # Match table name
                if tbl_clean in q_tokens or f" {tbl_clean} " in f" {q} ":
                    score += 300
                elif tbl_clean.rstrip("s") in q_tokens or (tbl_clean + "s") in q_tokens:
                    score += 200
                elif any(part in q_tokens for part in tbl_clean.split("_") if len(part) > 2 and part not in ("all", "table", "data", "db", "log", "logs")):
                    score += 100

                # Match column names
                cols = meta.get("columns", [])
                for c in cols:
                    c_name = c["name"].lower()
                    if len(c_name) < 2 or c_name in stopwords_score or c_name.isdigit() or c_name == "id":
                        continue
                    if c_name in q_tokens:
                        score += 50
                    elif "_" in c_name and f" {c_name.replace('_', ' ')} " in f" {q} ":
                        score += 45

                if tbl_clean == "audit_logs":
                    score = -999999 if not any(k in q_tokens or f" {k} " in f" {q} " for k in ["audit", "audit_log", "audit_logs"]) else score

                scores[tbl_name] = score

            if not scores or max(scores.values()) <= 0:
                available_tables = [t for t in schema_info.keys() if t.lower() not in ("audit_logs", "sqlite_sequence")]
                avail_str = ", ".join(available_tables) if available_tables else "available tables"
                return "", f"No matching database table or attributes found for your question. Available tables: {avail_str}."
            else:
                target_table = max(scores, key=scores.get)

        if not target_table or target_table not in schema_info:
            available_tables = [t for t in schema_info.keys() if t.lower() not in ("audit_logs", "sqlite_sequence")]
            avail_str = ", ".join(available_tables) if available_tables else "available tables"
            return "", f"No matching database table or attributes found for your question. Available tables: {avail_str}."

        table_meta = schema_info.get(target_table, {})
        cols_meta = table_meta.get("columns", [])
        all_cols = [c["name"] for c in cols_meta]

        # 3. Categorize Columns
        numeric_cols = []
        date_cols = []
        text_cols = []
        id_cols = []

        for c in cols_meta:
            c_name = c["name"]
            c_lower = c_name.lower()
            c_type = str(c.get("type", "")).upper()

            is_num_type = any(k in c_type for k in ["INT", "FLOAT", "DOUBLE", "REAL", "NUMERIC", "DECIMAL", "BIGINT"])
            sample_vals = [r.get(c_name) for r in table_meta.get("sample_rows", []) if r.get(c_name) is not None]
            has_numeric_samples = sample_vals and all(
                isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).replace("-", "", 1).isdigit())
                for v in sample_vals
            )

            if is_num_type or has_numeric_samples:
                if not (c_lower == "id" or c_lower.endswith("_id")):
                    numeric_cols.append(c_name)
                else:
                    id_cols.append(c_name)
            elif any(k in c_lower for k in ["date", "time", "month", "year", "created", "hired", "timestamp"]) or any(k in c_type for k in ["DATE", "TIME", "TIMESTAMP"]):
                date_cols.append(c_name)
            elif c_lower == "id" or c_lower.endswith("_id"):
                id_cols.append(c_name)
            else:
                text_cols.append(c_name)

        # 4. Metric Column Selection
        mentioned_num = [c for c in numeric_cols if c.lower() in q or c.lower().replace("_", " ") in q]
        if mentioned_num:
            metric_col = mentioned_num[0]
        else:
            pref = ["total_amount", "amount", "line_total", "revenue", "sales", "total_price", "total_spent", "price", "unit_price", "value", "salary", "stock_quantity", "rating", "mileage"]
            metric_col = next((c for p in pref for c in numeric_cols if p in c.lower()), (numeric_cols[0] if numeric_cols else None))

        # 5. Group By / Dimension Column Detection
        group_col = None
        by_matches = list(re.finditer(r"\b(?:by|per|for each|in each|across|grouped by)\s+([a-zA-Z0-9_ ]+)", q))
        valid_by_match = None
        for bm in by_matches:
            prefix = q[:bm.start()].strip().lower()
            if not any(prefix.endswith(k) for k in ["order", "ordered", "sort", "sorted", "rank", "ranked"]):
                valid_by_match = bm
                break

        if valid_by_match:
            candidate = valid_by_match.group(1).strip().lower().replace(" ", "_")
            candidate_raw = valid_by_match.group(1).strip().lower()
            for c in all_cols:
                c_l = c.lower()
                if c_l == candidate or c_l.rstrip("s") == candidate.rstrip("s") or c_l == candidate_raw:
                    group_col = c
                    break
                elif candidate in c_l or c_l in candidate:
                    group_col = c
                    break

        # 6. Filters (WHERE clause)
        where_filters = []
        filter_descriptions = []

        for num_c in numeric_cols + date_cols:
            pat = rf"\b{re.escape(num_c.lower())}\s*(>=|<=|>|<|=|!=|greater than|more than|above|over|less than|below|under)\s*(\d+(?:\.\d+)?)\b"
            m = re.search(pat, q)
            if m:
                op_raw, n_val = m.group(1), m.group(2)
                op_map = {
                    ">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=", "!=": "!=",
                    "greater than": ">", "more than": ">", "above": ">", "over": ">",
                    "less than": "<", "below": "<", "under": "<"
                }
                op = op_map.get(op_raw, ">")
                where_filters.append(f'"{num_c}" {op} {n_val}')
                filter_descriptions.append(f"{num_c} {op} {n_val}")

        for c in text_cols:
            distinct_vals = _get_column_distinct_values(target_table, c)
            for r in table_meta.get("sample_rows", []):
                val = r.get(c)
                if val and isinstance(val, str) and str(val).strip() not in distinct_vals:
                    distinct_vals.append(str(val).strip())

            for val in distinct_vals:
                val_l = val.lower()
                if len(val_l) >= 2 and re.search(rf"\b{re.escape(val_l)}\b", q):
                    clean_val = val.replace("'", "''")
                    where_filters.append(f'LOWER("{c}") = \'{clean_val.lower()}\'')
                    filter_descriptions.append(f"{c} is '{val}'")
                    break

        where_clause = f" WHERE {' AND '.join(where_filters)}" if where_filters else ""

        # 7. Aggregation Intent Analysis
        is_avg = any(k in q for k in ["average", "avg", "mean"])
        is_sum = any(k in q for k in ["total", "sum", "overall", "how much", "revenue", "spending", "spent"])
        is_count = any(k in q for k in ["count", "how many", "number of"])

        # Branch A: Group By Query
        if group_col:
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            elif metric_col and not is_count:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            else:
                agg_fn, agg_alias = 'COUNT(*)', 'total_count'

            l_clause = f" LIMIT {limit_val}" if has_explicit_limit else ""
            sql = f'SELECT "{group_col}", {agg_fn} AS {agg_alias} FROM "{target_table}"{where_clause} GROUP BY "{group_col}" ORDER BY {agg_alias} {direction}{l_clause};'
            explanation = f"Groups the '{target_table}' table by '{group_col}', computing {agg_alias.replace('_', ' ')} in {direction_word} order."
            return sql, explanation

        # Branch B: Single Scalar Aggregate
        if (is_avg or is_sum or (is_count and not has_explicit_limit)) and not (has_explicit_limit and limit_val > 1):
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            else:
                agg_fn, agg_alias = 'COUNT(*)', 'total_count'

            sql = f'SELECT {agg_fn} AS {agg_alias} FROM "{target_table}"{where_clause};'
            explanation = f"Calculates overall {agg_alias.replace('_', ' ')} across records in the '{target_table}' table."
            return sql, explanation

        # Branch C: Ranked Ordering
        if (is_highest or is_lowest or "top" in q or "bottom" in q) and metric_col:
            sql = f'SELECT * FROM "{target_table}"{where_clause} ORDER BY "{metric_col}" {direction} LIMIT {limit_val};'
            explanation = f"Retrieves records from '{target_table}' ordered by '{metric_col}' in {direction_word} order."
            return sql, explanation

        # Branch D: Browse / Filtered Query
        # The result renderer/executor already has a 1,000-row safety cap.
        # Do not introduce an undocumented ten-row cap for normal questions.
        browse_limit = ""
        sql = f'SELECT * FROM "{target_table}"{where_clause}{browse_limit};'
        if where_filters:
            suffix = "all matching records"
            explanation = f"Retrieves records from '{target_table}' where {', '.join(filter_descriptions)} ({suffix})."
        else:
            explanation = f"Retrieves all records from the '{target_table}' table."
        return sql, explanation

    def _clean_sql(self, raw_sql: str, schema_info: Optional[Dict[str, Any]] = None, user_question: Optional[str] = None) -> str:
        """Strips markdown fences and leading/trailing whitespace from SQL, and normalizes columns to match schema."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        sql = sql.strip()

        if not schema_info:
            return sql

        # 1. Block audit_logs if user question didn't explicitly ask for audit logs
        if user_question:
            q_low = user_question.lower()
            is_audit_intent = any(re.search(rf"\b{re.escape(k)}\b", q_low) for k in [
                "audit", "audit_log", "audit_logs", "security log", "security logs", "security audit",
                "failed login", "failed logins"
            ])
            if "audit_logs" in sql.lower() and not is_audit_intent:
                logger.warning("Blocked LLM from querying audit_logs for question '%s'", user_question)
                return ""

        # 2. Schema Column Normalization
        if "products" in schema_info:
            p_cols = {c["name"].lower(): c["name"] for c in schema_info["products"].get("columns", [])}
            actual_name = next((p_cols[k] for k in ["product_name", "name", "title"] if k in p_cols), None)
            if actual_name and "name" not in p_cols:
                sql = re.sub(r"\b(?:p|products)\.name\b", f"p.{actual_name}", sql, flags=re.IGNORECASE)
            actual_id = next((p_cols[k] for k in ["product_id", "id", "item_id"] if k in p_cols), None)
            if actual_id and "id" not in p_cols:
                sql = re.sub(r"\b(?:p|products)\.id\b", f"p.{actual_id}", sql, flags=re.IGNORECASE)

        if "customers" in schema_info:
            c_cols = {c["name"].lower(): c["name"] for c in schema_info["customers"].get("columns", [])}
            actual_c_name = next((c_cols[k] for k in ["customer_name", "name", "full_name"] if k in c_cols), None)
            if actual_c_name and "name" not in c_cols:
                sql = re.sub(r"\b(?:c|customers)\.name\b", f"c.{actual_c_name}", sql, flags=re.IGNORECASE)
            actual_c_id = next((c_cols[k] for k in ["customer_id", "id", "user_id"] if k in c_cols), None)
            if actual_c_id and "id" not in c_cols:
                sql = re.sub(r"\b(?:c|customers)\.id\b", f"c.{actual_c_id}", sql, flags=re.IGNORECASE)

        return sql.strip()
