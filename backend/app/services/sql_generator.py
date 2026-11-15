"""
SQL and Query Explanation Generation Service.
Generates valid ANSI/SQLite SQL queries and plain-English explanations using LLMs
(Google Gemini, OpenAI) with a fast, high-precision, intent-aware deterministic offline engine.
Specially optimized for custom uploaded datasets (.CSV, .XLSX, .JSON, .SQLITE) and multi-table schemas.
"""
import os
import re
import json
import logging
import httpx
from typing import Dict, Any, Tuple, Optional, List
try:
    from backend.app.services.schema_service import format_schema_for_llm
    from backend.app.db.database import engine
except ImportError:
    from app.services.schema_service import format_schema_for_llm
    try:
        from app.db.database import engine
    except Exception:
        engine = None

from sqlalchemy import text

logger = logging.getLogger("text2sql.generator")

_DISTINCT_CACHE: Dict[Tuple[str, str], List[str]] = {}


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

    def generate(self, user_question: str, schema_info: Dict[str, Any], active_table: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Generates SQL query and explanation for the provided user question.
        
        Args:
            user_question: The plain English question from the user.
            schema_info: Structured database schema dictionary.
            active_table: Optional target table to prioritize (e.g. from upload or active context).
            
        Returns:
            Tuple of (sql_query: str, explanation: str, generated_by: str)
        """
        logger.info("Generating SQL for question: '%s' (active_table: %s, provider: %s)", user_question, active_table, self.provider)

        # 1. Attempt LLM generation if API key is present
        if self.api_key and self.provider != "fallback":
            try:
                llm_sql, llm_explanation = self._generate_with_llm(user_question, schema_info, active_table=active_table)
                if llm_sql:
                    cleaned_sql = self._clean_sql(llm_sql)
                    provider_label = "Gemini 1.5 Flash" if "gemini" in self.provider else "OpenAI GPT-4o"
                    logger.info("Successfully generated SQL via %s: %s", provider_label, cleaned_sql)
                    return cleaned_sql, llm_explanation, provider_label
            except Exception as e:
                logger.warning("LLM generation failed, falling back to deterministic engine: %s", str(e))

        # 2. Deterministic Rule-Based Fallback Engine
        sql, explanation = self._generate_deterministic(user_question, schema_info, active_table=active_table)
        logger.info("Generated SQL via Deterministic Engine: %s", sql)
        return sql, explanation, "Deterministic Analytics Engine"

    def _generate_with_llm(self, user_question: str, schema_info: Dict[str, Any], active_table: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Invokes LLM API to generate JSON containing both SQL and explanation with strict ranking direction rules."""
        formatted_schema = format_schema_for_llm(schema_info, active_table=active_table)

        active_table_instruction = ""
        if active_table and active_table in schema_info:
            active_table_instruction = f"\nTARGET TABLE: The active dataset is '{active_table}'. Prioritize writing queries against '{active_table}' unless the question explicitly asks for another table.\n"

        system_prompt = f"""You are an expert SQL Developer and Database Architect.
Generate a standard SQLite/ANSI SQL query and a short, clear plain English explanation for the user question.

DATABASE SCHEMA:
{formatted_schema}
{active_table_instruction}
CRITICAL INTENT AND RANKING RULES:
1. TABLE SELECTION & DOMAIN RULES:
   - Questions about "customers", "clients", "users", "accounts", or "subscribers" (e.g., "How many customers are in the database?") MUST ALWAYS query the 'customers' table (e.g. SELECT COUNT(*) AS customer_count FROM customers;). NEVER query 'audit_logs' or 'sales'.
   - 'audit_logs' contains system security logs (actions, IP addresses, failures). NEVER query 'audit_logs' unless the user explicitly asks about audit logs, security events, logins, or IP addresses.
   - Questions about "products", "catalog", "items", "prices", or "categories" MUST query the 'products' table (or join with 'sales' for sales volume/revenue).
   - Questions about "employees", "staff", "departments", or "salaries" MUST query the 'employees' table.
   - Questions about "sales", "orders", "transactions", or "revenue" MUST query the 'sales' table.
2. Strictly respect requested ranking direction:
   - For "lowest", "bottom", "least", "cheapest", "worst", "minimum", "ascending", or "ASC": use ORDER BY <metric> ASC.
   - For "top", "highest", "most", "best", "greatest", "maximum", "descending", or "DESC": use ORDER BY <metric> DESC.
   - NEVER default to DESC when the user asks for lowest, bottom, or ascending rankings.
2. Distinguish metrics carefully:
   - Revenue / Sales volume in currency -> SUM(s.total_price) or p.price
   - Units sold / Quantity -> SUM(s.quantity)
   - Order count / Number of sales -> COUNT(s.id)
   - Customer spending -> c.total_spent or SUM(s.total_price)
   - Rating -> p.rating or AVG(p.rating)
3. Respect requested limits:
   - e.g., "Top 5" -> LIMIT 5, "Lowest 10" -> LIMIT 10, "Bottom 3" -> LIMIT 3.
4. Security & Safety:
   - Generate strictly read-only SELECT queries (JOINs, aggregations, GROUP BY, ORDER BY, LIMIT).
   - Use clear column aliases (e.g., AS total_revenue, AS customer_count, AS total_units_sold).
5. Explanations:
   - Provide a 1-2 sentence explanation of what the query does (which tables are joined, filters used, ranking metric, and sort direction).
   - If the user request is ambiguous, note any assumptions in the explanation.

JSON Response Format:
{{
  "sql": "SELECT ...",
  "explanation": "This query joins the sales and products tables to aggregate total revenue for the lowest 5 products, sorted in ascending order."
}}"""

        if "gemini" in self.provider:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\nUSER QUESTION: \"{user_question}\""}]}
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }
            with httpx.Client(timeout=6) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    return parsed.get("sql"), parsed.get("explanation")
                else:
                    logger.error("Gemini API error (%d): %s", res.status_code, res.text)

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
            with httpx.Client(timeout=6) as client:
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
        Correctly recognizes ranking direction (ASC for lowest/bottom, DESC for top/highest),
        metrics, filters, and limits.
        """
        q = user_question.lower()
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))
        canonical_tables = {"sales", "products", "customers", "employees", "audit_logs", "sqlite_sequence"}

        # Step A: Table Intent Detection with Semantic Synonyms
        table_synonyms = {
            "customers": ["customer", "customers", "client", "clients", "user", "users", "buyer", "buyers", "subscriber", "subscribers", "account", "accounts", "member", "members"],
            "products": ["product", "products", "item", "items", "catalog", "catalogue", "merchandise", "goods"],
            "employees": ["employee", "employees", "staff", "worker", "workers", "headcount", "personnel", "engineer", "engineers"],
            "sales": ["sale", "sales", "transaction", "transactions", "order", "orders", "purchase", "purchases"],
            "audit_logs": ["audit", "audits", "audit_log", "audit_logs", "audit log", "audit logs", "security event", "security events", "failed login", "login failure", "security log"]
        }

        target_table_name = None
        # 1. Match semantic table synonyms
        for tbl, syns in table_synonyms.items():
            if tbl in schema_info and any(s in q_tokens or f" {s} " in f" {q} " for s in syns):
                target_table_name = tbl
                break

        # 2. Match exact schema table names
        if not target_table_name:
            for tbl in schema_info.keys():
                tbl_l = tbl.lower()
                if tbl_l == "sqlite_sequence":
                    continue
                if tbl_l in q_tokens or tbl_l in q or tbl_l.replace("_", " ") in q or tbl_l.rstrip("s") in q_tokens:
                    target_table_name = tbl
                    break

        # Step A.1: Direct Entity Count Pattern (e.g. "How many customers are in the database?", "How many products?", "Count of employees")
        is_count_intent = (
            any(k in q for k in ["how many", "count of", "number of", "total number of", "total count of", "how many "])
            or ("count" in q and not any(k in q for k in ["by", "per", "group", "plan", "country", "status", "department", "category", "where"]))
        )
        if is_count_intent and not any(k in q for k in ["average", "avg", "highest", "lowest", "top", "bottom", "more than", "greater than", "less than", "between"]):
            # Determine count table
            count_table = None
            if any(k in q for k in ["customer", "client", "user", "buyer", "subscriber", "member", "account"]):
                count_table = "customers" if "customers" in schema_info else target_table_name
            elif any(k in q for k in ["employee", "staff", "worker", "personnel", "headcount"]):
                count_table = "employees" if "employees" in schema_info else target_table_name
            elif any(k in q for k in ["product", "item", "catalog"]):
                count_table = "products" if "products" in schema_info else target_table_name
            elif any(k in q for k in ["sale", "order", "transaction", "purchase"]):
                count_table = "sales" if "sales" in schema_info else target_table_name
            elif any(k in q for k in ["audit", "log", "security event"]):
                count_table = "audit_logs" if "audit_logs" in schema_info else target_table_name
            elif target_table_name and target_table_name != "audit_logs":
                count_table = target_table_name

            if count_table and count_table in schema_info:
                sql = f'SELECT COUNT(*) AS total_count FROM "{count_table}";'
                explanation = f"Calculates total count of records in the '{count_table}' table."
                return sql, explanation

        # Step A.2: Check if user explicitly asked for a table that does NOT exist in the database
        if not target_table_name:
            stopwords = {
                "the", "a", "an", "all", "each", "this", "that", "these", "my", "our", "database",
                "data", "db", "here", "current", "active", "system", "first", "last", "top", "bottom",
                "any", "some", "every", "select", "where", "group", "order", "limit", "records",
                "rows", "items", "entries", "values", "details", "information", "info", "columns",
                "fields", "table", "tables", "chart", "graph", "analytics", "insights", "summary",
                "scratch", "file", "csv", "json", "sample", "view"
            }
            explicit_table_requested = None
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
                            explicit_table_requested = m.group(1)
                            break

            if explicit_table_requested:
                return (
                    f'SELECT * FROM "{explicit_table_requested}" LIMIT 10;',
                    f"Attempted to query requested table '{explicit_table_requested}'."
                )

        # Step B: If not mentioned, check active_table
        if not target_table_name and active_table and active_table in schema_info and active_table.lower() != "sqlite_sequence":
            target_table_name = active_table

        # Step C: If still not set, check if an uploaded (non-canonical) table exists in schema
        if not target_table_name:
            non_canonicals = [t for t in schema_info.keys() if t.lower() not in canonical_tables]
            if len(non_canonicals) == 1:
                # If there's a custom uploaded table, and user isn't asking about audit logs, prioritize it
                if not any(k in q for k in ["audit", "log", "ip_address"]):
                    target_table_name = non_canonicals[0]

        # If a custom uploaded table is targeted, route directly to dynamic synthesizer
        if target_table_name and target_table_name.lower() not in canonical_tables:
            return self._synthesize_dynamic_sql(user_question, schema_info, target_table=target_table_name)

        # 1. Parse ranking direction
        is_lowest = any(k in q for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "min", "minimum", "fewest"
        ])
        is_highest = any(k in q for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "max", "maximum"
        ])
        direction = "ASC" if is_lowest and not is_highest else ("DESC" if is_highest else ("ASC" if "ascending" in q or " asc" in q else "DESC"))
        direction_word = "ascending" if direction == "ASC" else "descending"
        rank_label = "lowest" if direction == "ASC" else "top"

        # 2. Parse limit count without capturing comparison numbers like > 30000
        limit_match = re.search(r"\b(?:top|bottom|lowest|highest|first|last|limit)\s*(\d+)\b", q)
        if not limit_match:
            limit_match = re.search(r"\b(\d+)\s*(?:rows?|records?|items?|entries|results?|products?|users?|customers?|employees?)\b", q)

        if limit_match:
            limit_val = int(limit_match.group(1))
            has_explicit_limit = True
        elif is_highest or is_lowest:
            limit_val = 1 if any(k in q for k in ["what is", "which is", "who is", "find the", "single", "most", "least"]) else 5
            has_explicit_limit = True
        else:
            limit_val = 5
            has_explicit_limit = False

        limit_clause = f" LIMIT {limit_val}" if has_explicit_limit else ""

        # 3. Parse date / temporal filters if specified
        date_where_s = ""
        date_where_sales = ""
        date_desc = ""

        month_names = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        month_map = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        month_pat = r"\b(" + "|".join(month_names) + r")(?:\s+(20[12]\d))?\b"

        between_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\s*(?:and|to)\s*(\d{4}-\d{2}-\d{2})\b", q)
        rel_year_match = re.search(r"\b(after|since|before|earlier than|later than)\s+(20[12]\d)\b", q)
        month_match = re.search(month_pat, q)
        year_match = re.search(r"\b(?:in|for|during|year|of)?\s*(20[12]\d)\b", q)

        if between_match:
            d1, d2 = between_match.group(1), between_match.group(2)
            date_where_s = f" AND s.sale_date BETWEEN '{d1}' AND '{d2}'"
            date_where_sales = f" AND sale_date BETWEEN '{d1}' AND '{d2}'"
            date_desc = f" between {d1} and {d2}"
        elif rel_year_match:
            op_w, yr = rel_year_match.group(1), rel_year_match.group(2)
            if op_w in ["after", "since", "later than"]:
                date_where_s = f" AND s.sale_date >= '{yr}-01-01'"
                date_where_sales = f" AND sale_date >= '{yr}-01-01'"
                date_desc = f" after {yr}"
            else:
                date_where_s = f" AND s.sale_date < '{yr}-01-01'"
                date_where_sales = f" AND sale_date < '{yr}-01-01'"
                date_desc = f" before {yr}"
        elif month_match:
            m_name = month_match.group(1).lower()
            m_yr = month_match.group(2) or "2026"
            m_code = month_map[m_name]
            date_where_s = f" AND s.sale_date LIKE '{m_yr}-{m_code}%'"
            date_where_sales = f" AND sale_date LIKE '{m_yr}-{m_code}%'"
            date_desc = f" in {m_name.capitalize()} {m_yr}"
        elif year_match:
            yr = year_match.group(1)
            date_where_s = f" AND s.sale_date LIKE '{yr}%'"
            date_where_sales = f" AND sale_date LIKE '{yr}%'"
            date_desc = f" in {yr}"

        # Pattern: Compare Regions
        if self._has_cols(schema_info, "sales", ["region", "total_price", "status"]) and ("compare" in q or " vs " in q or "versus" in q or "between" in q) and ("region" in q or any(r in q for r in ["north", "south", "east", "west", "europe", "asia", "america", "apac", "latam", "emea"])):
            region_candidates = ["North America", "Latin America", "Asia-Pacific", "Europe", "North", "South", "East", "West"]
            regions = [r for r in region_candidates if r.lower() in q]
            if "North America" in regions and "North" in regions:
                regions.remove("North")
            if "Latin America" in regions and "Latin" in regions:
                regions.remove("Latin")
            if len(regions) >= 2:
                region_or = " OR ".join([f"(region = '{r}' OR region LIKE '{r}%')" for r in regions])
                sql = (
                    f"SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales "
                    f"FROM sales WHERE status = 'Completed' AND ({region_or}){date_where_sales} "
                    f"GROUP BY region ORDER BY total_revenue DESC;"
                )
                explanation = f"Compares sales performance between the {', '.join(regions)} regions{date_desc}."
                return sql, explanation

        # Pattern: Compare Departments
        if self._has_cols(schema_info, "employees", ["department", "salary"]) and ("compare" in q or " vs " in q or "versus" in q or "between" in q) and ("dept" in q or "department" in q or "salary" in q):
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

        # Pattern: Single aggregate KPI ("total revenue", "what is total sales", "how much revenue")
        if self._has_cols(schema_info, "sales", ["total_price", "status"]) and ("total" in q or "overall" in q or "sum" in q or "how much" in q) and ("revenue" in q or "sales" in q) and not any(k in q for k in ["product", "customer", "region", "month", "by"]):
            sql = (
                f"SELECT SUM(total_price) AS total_revenue, COUNT(id) AS total_sales "
                f"FROM sales WHERE status = 'Completed'{date_where_sales};"
            )
            explanation = f"Calculates overall total revenue and completed sales count across all transactions{date_desc}."
            return sql, explanation

        # Pattern: Completed Sales Detailed Transactions with Customer and Product Names (Multi-Table 3-Way Join)
        if (
            self._has_cols(schema_info, "sales", ["id", "customer_id", "product_id", "total_price", "sale_date", "status"])
            and self._has_cols(schema_info, "customers", ["id", "name"])
            and self._has_cols(schema_info, "products", ["id", "name"])
            and ("sale" in q or "transaction" in q or "order" in q)
            and ("customer" in q or "user" in q)
            and ("product" in q or "item" in q)
        ):
            sql = (
                "SELECT s.id, c.name AS customer_name, p.name AS product_name, s.total_price, s.sale_date "
                "FROM sales s "
                "JOIN customers c ON s.customer_id = c.id "
                "JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed'{date_where_s} "
                f"ORDER BY s.sale_date DESC{limit_clause or ' LIMIT 10'};"
            )
            explanation = (
                f"Performs a three-table join across sales, customers, and products to list completed "
                f"transaction records with customer and product names{date_desc}."
            )
            return sql, explanation

        # Pattern: Customer Spending by Product Category (Multi-Table 3-Way Join)
        if (
            self._has_cols(schema_info, "sales", ["id", "customer_id", "product_id", "total_price", "status"])
            and self._has_cols(schema_info, "customers", ["id", "plan"])
            and self._has_cols(schema_info, "products", ["id", "category"])
            and ("customer" in q or "plan" in q)
            and ("category" in q or "product category" in q)
            and ("spent" in q or "spending" in q or "revenue" in q or "sales" in q)
        ):
            sql = (
                "SELECT c.plan, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS sales_count "
                "FROM sales s "
                "JOIN customers c ON s.customer_id = c.id "
                "JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed'{date_where_s} "
                "GROUP BY c.plan, p.category "
                "ORDER BY total_revenue DESC;"
            )
            explanation = (
                f"Performs a three-table join between sales, customers, and products to aggregate "
                f"total revenue and transaction count by customer plan and product category{date_desc}."
            )
            return sql, explanation

        # Pattern: Average Order Value per Customer Plan (Multi-Table Join)
        if (
            self._has_cols(schema_info, "sales", ["id", "customer_id", "total_price", "status"])
            and self._has_cols(schema_info, "customers", ["id", "plan"])
            and "plan" in q
            and ("order value" in q or "average order" in q or "avg order" in q or ("order" in q and ("average" in q or "avg" in q)) or "aov" in q)
        ):
            sql = (
                "SELECT c.plan, COUNT(s.id) AS order_count, AVG(s.total_price) AS avg_order_value, SUM(s.total_price) AS total_spent "
                "FROM sales s "
                "JOIN customers c ON s.customer_id = c.id "
                f"WHERE s.status = 'Completed'{date_where_s} "
                "GROUP BY c.plan "
                "ORDER BY avg_order_value DESC;"
            )
            explanation = (
                f"Joins sales and customers by plan to calculate order count, average order value, "
                f"and total spending per subscription tier{date_desc}."
            )
            return sql, explanation

        # Pattern: Products by Units Sold / Quantity
        if (
            self._has_cols(schema_info, "sales", ["id", "product_id", "quantity", "status"])
            and self._has_cols(schema_info, "products", ["id", "name", "category"])
            and (("unit" in q and ("sold" in q or "sale" in q)) or "quantity" in q or "volume" in q or "sold" in q)
            and ("product" in q or "item" in q or "top" in q or "bottom" in q or "lowest" in q or "highest" in q)
            and not ("inventory" in q or "stock" in q)
        ):
            sql = (
                f"SELECT p.name AS product_name, p.category, SUM(s.quantity) AS total_quantity "
                f"FROM sales s JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed'{date_where_s} "
                f"GROUP BY p.id, p.name, p.category "
                f"ORDER BY total_quantity {direction}{limit_clause};"
            )
            explanation = (
                f"Joins the 'sales' and 'products' tables, filters for completed transactions{date_desc}, "
                f"and aggregates total quantity sold for {rank_label} products sorted in {direction_word} order."
            )
            return sql, explanation

        # Pattern: Products by Revenue / Sales or Default Benchmark Ranking
        if (
            self._has_cols(schema_info, "sales", ["id", "product_id", "total_price", "status"])
            and self._has_cols(schema_info, "products", ["id", "name", "category"])
            and ("product" in q or "item" in q)
            and (
                "revenue" in q or "sales" in q
                or ("rank" in q and not "price" in q and not "rating" in q and not "stock" in q)
                or (is_highest and not "price" in q and not "rating" in q and not "stock" in q and not "unit" in q)
                or (is_lowest and not "price" in q and not "rating" in q and not "stock" in q and not "unit" in q)
            )
        ):
            is_unspecified_metric = not any(k in q for k in ["revenue", "sales", "price", "profit", "order"])
            sql = (
                f"SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders "
                f"FROM sales s JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed'{date_where_s} "
                f"GROUP BY p.id, p.name, p.category "
                f"ORDER BY total_revenue {direction}{limit_clause};"
            )
            if is_unspecified_metric:
                explanation = (
                    f"Defaulted to total revenue as the primary ranking benchmark since no metric was specified; "
                    f"aggregates completed sales for {rank_label} products in {direction_word} order{date_desc} (can also rank by quantity sold, order count, or customer rating)."
                )
            else:
                explanation = (
                    f"Joins the 'sales' and 'products' tables, filters for completed transactions{date_desc}, "
                    f"and aggregates total revenue for {rank_label} products sorted in {direction_word} order."
                )
            return sql, explanation

        # Pattern: Customers by Spending / Value
        if (
            self._has_cols(schema_info, "customers", ["name", "email", "company", "country", "plan", "total_spent"])
            and ("customer" in q or "user" in q or "client" in q)
            and ("spent" in q or "spending" in q or "revenue" in q or "highest" in q or "lowest" in q or "top" in q or "bottom" in q)
        ):
            sql = (
                f"SELECT name AS customer_name, email, company, country, plan, total_spent "
                f"FROM customers "
                f"ORDER BY total_spent {direction}{limit_clause};"
            )
            explanation = (
                f"Retrieves customers ranked by total spending in {direction_word} order ({'lowest spenders first' if direction == 'ASC' else 'highest spenders first'})."
            )
            return sql, explanation

        # Pattern: Customer Distribution by Plan & Country
        if (
            self._has_cols(schema_info, "customers", ["country", "plan", "id", "total_spent"])
            and "customer" in q
            and ("plan" in q or "country" in q or "distribution" in q or "count" in q)
        ):
            sql = (
                "SELECT country, plan, COUNT(id) AS customer_count, AVG(total_spent) AS avg_spent "
                "FROM customers "
                "GROUP BY country, plan "
                "ORDER BY customer_count DESC;"
            )
            explanation = (
                "Groups the 'customers' table by country and subscription plan, computing customer counts "
                "and average spend per segment in descending order."
            )
            return sql, explanation

        # Pattern: Monthly Sales Trend / Revenue Over Time
        if (
            self._has_cols(schema_info, "sales", ["sale_date", "total_price", "region", "status"])
            and ("month" in q or "monthly" in q or "trend" in q or "time" in q)
            and ("sale" in q or "revenue" in q)
        ):
            is_postgres = (engine is not None and getattr(engine, "dialect", None) is not None and engine.dialect.name == "postgresql")
            month_expr = "TO_CHAR(sale_date, 'YYYY-MM')" if is_postgres else "strftime('%Y-%m', sale_date)"
            sql = (
                f"SELECT {month_expr} AS sales_month, region, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions "
                "FROM sales "
                f"WHERE status = 'Completed'{date_where_sales} "
                "GROUP BY sales_month, region "
                "ORDER BY sales_month ASC, monthly_revenue DESC;"
            )
            explanation = (
                "Extracts year and month from 'sale_date' in the 'sales' table, grouping by month and geographical region "
                f"to calculate monthly revenue and transaction volume{date_desc}."
            )
            return sql, explanation

        # Pattern: Sales by Region
        if self._has_cols(schema_info, "sales", ["region", "total_price", "status"]) and "region" in q:
            sql = (
                f"SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales, AVG(total_price) AS avg_sale_value "
                f"FROM sales "
                f"WHERE status = 'Completed'{date_where_sales} "
                f"GROUP BY region "
                f"ORDER BY total_revenue {direction};"
            )
            explanation = (
                f"Calculates total revenue, transaction counts, and average order value across geographical regions in {direction_word} order{date_desc}."
            )
            return sql, explanation

        # Pattern: Product Categories & Ratings
        if self._has_cols(schema_info, "products", ["category", "id", "price", "rating", "stock_quantity"]) and ("category" in q or "rating" in q or "stock" in q):
            sort_metric = "avg_rating" if "rating" in q else ("total_stock" if "stock" in q else "product_count")
            sql = (
                f"SELECT category, COUNT(id) AS product_count, AVG(price) AS avg_price, AVG(rating) AS avg_rating, SUM(stock_quantity) AS total_stock "
                f"FROM products "
                f"GROUP BY category "
                f"ORDER BY {sort_metric} {direction};"
            )
            explanation = (
                f"Aggregates the 'products' table by category, computing price, customer rating, "
                f"and stock levels in {direction_word} order."
            )
            return sql, explanation

        # Pattern: Security & Audit logs
        if self._has_cols(schema_info, "audit_logs", ["action", "status", "ip_address"]) and (any(k in q for k in ["audit", "audit_log", "audit_logs", "security", "ip_address"]) or ("log" in q and not "catalog" in q) or ("fail" in q and ("event" in q or "log" in q))):
            if "action" in q and ("ip" in q or "address" in q):
                sql = (
                    "SELECT action, status, ip_address, COUNT(id) AS event_count, MAX(timestamp) AS last_occurred "
                    "FROM audit_logs "
                    "WHERE status = 'FAILURE' OR action LIKE '%FAIL%' "
                    "GROUP BY action, status, ip_address "
                    "ORDER BY event_count DESC LIMIT 10;"
                )
                explanation = (
                    "Queries the 'audit_logs' table for security events with failure status, "
                    "grouping by action and IP address to highlight recurring issues."
                )
                return sql, explanation
            elif any(k in q for k in ["record", "recent", "detail", "row"]) or ("show" in q and "audit" in q and not "action" in q and not "ip" in q):
                sql = (
                    "SELECT id, action, status, user_id, ip_address, timestamp "
                    "FROM audit_logs "
                    "WHERE status = 'FAILURE' OR action LIKE '%FAIL%' "
                    "ORDER BY timestamp DESC LIMIT 10;"
                )
                explanation = (
                    "Retrieves recent failed security and audit log event records sorted chronologically in descending order."
                )
                return sql, explanation
            else:
                sql = (
                    "SELECT action, status, ip_address, COUNT(id) AS event_count, MAX(timestamp) AS last_occurred "
                    "FROM audit_logs "
                    "WHERE status = 'FAILURE' OR action LIKE '%FAIL%' "
                    "GROUP BY action, status, ip_address "
                    "ORDER BY event_count DESC LIMIT 10;"
                )
                explanation = (
                    "Queries the 'audit_logs' table for security events with failure status, "
                    "grouping by action and IP address to highlight recurring issues."
                )
                return sql, explanation

        # Pattern: First N rows from specific table (e.g. from table chips or direct prompt)
        first_table_match = re.search(r"(?:from|in|table)\s+([a-zA-Z0-9_]+)", q)
        target_table_candidate = first_table_match.group(1).lower() if first_table_match else None
        if target_table_candidate and schema_info and target_table_candidate in schema_info and (
            any(k in q for k in ["first", "sample", "all rows", "show rows", "browse", "records"])
            or not any(k in q for k in ["where", "less", "greater", "more", "average", "avg", "count", "sum", "highest", "lowest", "by", ">", "<", "="])
        ):
            sql = f'SELECT * FROM "{target_table_candidate}" LIMIT {limit_val};'
            explanation = f"Retrieves the first {limit_val} records from the '{target_table_candidate}' table."
            return sql, explanation

        # Dynamic Schema Synthesizer: Intelligently handles custom tables, columns, metrics, and filters
        return self._synthesize_dynamic_sql(user_question, schema_info, target_table=target_table_name)

    def _synthesize_dynamic_sql(self, user_question: str, schema_info: Dict[str, Any], target_table: Optional[str] = None) -> Tuple[str, str]:
        """
        Dynamically synthesizes schema-grounded SQL for arbitrary databases and custom tables.
        Handles numeric comparisons, text filters, aggregations, group-bys, and ranked limits accurately.
        """
        if not schema_info:
            return 'SELECT * FROM "sales" LIMIT 10;', "Retrieves sample records from the default sales table."

        q = user_question.lower()
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))

        # 1. Ranking Direction & Limits
        is_lowest = any(k in q for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "min", "minimum", "fewest"
        ])
        is_highest = any(k in q for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "max", "maximum"
        ])
        direction = "ASC" if is_lowest and not is_highest else "DESC"
        direction_word = "ascending" if direction == "ASC" else "descending"
        rank_label = "lowest" if direction == "ASC" else "top"

        # Explicit limit parsing (guarded so comparison numbers like > 30000 or years 2024 are never captured)
        limit_match = re.search(r"\b(?:top|bottom|lowest|highest|first|last|limit)\s*(\d+)\b", q)
        if not limit_match:
            limit_match = re.search(r"\b(\d+)\s*(?:rows?|records?|items?|entries|results?|products?|cars?|students?|employees?|users?)\b", q)

        if limit_match:
            num = int(limit_match.group(1))
            # Make sure it's not a comparison value like > 30000
            comp_match = re.search(r"(?:>=|<=|>|<|=|!=|greater than|less than|above|below|over|under)\s*" + str(num), q)
            if not comp_match and num < 5000 and num not in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
                limit_val = num
                has_explicit_limit = True
            else:
                limit_val = 5 if (is_highest or is_lowest) else 10
                has_explicit_limit = False
        elif is_highest or is_lowest:
            limit_val = 1 if any(k in q for k in ["what is", "which is", "who is", "find the", "single", "most", "least"]) else 5
            has_explicit_limit = True
        else:
            limit_val = 10
            has_explicit_limit = False

        # 2. Multi-Factor Table Resolution (if target_table is not explicitly locked)
        canonical_tables = {"sales", "products", "customers", "employees", "audit_logs", "sqlite_sequence"}
        if not target_table or target_table not in schema_info:
            scores = {}
            for tbl_name, meta in schema_info.items():
                tbl_clean = tbl_name.lower()
                if tbl_clean == "sqlite_sequence":
                    continue
                score = 0

                # Match table name
                if tbl_clean in q_tokens or tbl_clean in q:
                    score += 300
                elif tbl_clean.rstrip("s") in q_tokens or (tbl_clean + "s") in q_tokens:
                    score += 200
                elif any(part in q_tokens for part in tbl_clean.split("_") if len(part) > 2):
                    score += 100

                # Match column names
                cols = meta.get("columns", [])
                for c in cols:
                    c_name = c["name"].lower()
                    if c_name in q_tokens:
                        score += 50
                    elif c_name.replace("_", " ") in q:
                        score += 45

                # Boost non-canonical uploaded tables if they match columns
                if tbl_clean not in canonical_tables and score > 0:
                    score += 120

                if tbl_clean == "audit_logs" and not any(k in q for k in ["audit", "log", "security", "ip", "fail"]):
                    score -= 500

                scores[tbl_name] = score

            if not scores or max(scores.values()) <= 0:
                # Do NOT default to audit_logs! Default to the table matching question domain keywords, or sales
                if any(k in q for k in ["customer", "client", "user", "buyer", "people", "account", "subscriber"]):
                    target_table = "customers" if "customers" in schema_info else list(schema_info.keys())[0]
                elif any(k in q for k in ["employee", "staff", "salary", "department", "hire"]):
                    target_table = "employees" if "employees" in schema_info else list(schema_info.keys())[0]
                elif any(k in q for k in ["product", "item", "stock", "price", "category", "rating"]):
                    target_table = "products" if "products" in schema_info else list(schema_info.keys())[0]
                else:
                    uploaded = [t for t in schema_info.keys() if t.lower() not in canonical_tables]
                    target_table = uploaded[0] if uploaded else ("sales" if "sales" in schema_info else list(schema_info.keys())[0])
            else:
                target_table = max(scores, key=scores.get)

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

        # 4. Metric Column Selection with Semantic Synonyms
        mentioned_num = [c for c in numeric_cols if c.lower() in q or c.lower().replace("_", " ") in q]
        if mentioned_num:
            metric_col = mentioned_num[0]
        else:
            if any(k in q for k in ["revenue", "sales", "spending", "amount", "income", "turnover", "total", "spent"]):
                pref = ["total_amount", "amount", "revenue", "sales", "total_price", "total_spent", "price", "unit_price", "value", "total"]
            elif any(k in q for k in ["quantity", "units", "volume", "sold", "stock"]):
                pref = ["quantity", "units_sold", "units", "qty", "volume", "stock_quantity", "stock"]
            elif any(k in q for k in ["price", "cost", "cheap", "expensive"]):
                pref = ["price", "unit_price", "cost", "retail_price"]
            elif any(k in q for k in ["salary", "pay", "wage", "compensation"]):
                pref = ["salary", "compensation", "pay"]
            elif any(k in q for k in ["rating", "score", "stars", "grade", "performance"]):
                pref = ["rating", "score", "performance_score", "grade"]
            elif any(k in q for k in ["age", "years old"]):
                pref = ["age", "years"]
            elif any(k in q for k in ["mileage", "distance", "miles"]):
                pref = ["mileage", "miles"]
            else:
                pref = ["total_amount", "salary", "total_price", "price", "revenue", "amount", "total_spent", "spent", "quantity", "stock_quantity", "stock", "rating", "score", "units", "cost", "value"]
            metric_col = next((c for p in pref for c in numeric_cols if p in c.lower()), (numeric_cols[0] if numeric_cols else None))

        # 5. Entity / Dimension Column Detection
        entity_col = None
        for cand in ["name", "title", "item_name", "product_name", "car_name", "student_name", "emp_name", "customer_name"]:
            match = next((c for c in text_cols if c.lower() == cand), None)
            if match:
                entity_col = match
                break
        if not entity_col:
            entity_col = next((c for c in text_cols if "name" in c.lower()), (text_cols[0] if text_cols else None))

        # Explicit Group By parsing (e.g. "by brand", "per department", "by category", "for each fuel type")
        group_col = None
        by_match = re.search(r"\b(?:by|per|for each|in each|across|grouped by)\s+([a-zA-Z0-9_ ]+)", q)
        if by_match:
            candidate = by_match.group(1).strip().lower().replace(" ", "_")
            candidate_raw = by_match.group(1).strip().lower()
            for c in all_cols:
                c_l = c.lower()
                if c_l == candidate or c_l.rstrip("s") == candidate.rstrip("s") or c_l == candidate_raw:
                    group_col = c
                    break
                elif candidate in c_l or c_l in candidate:
                    group_col = c
                    break

        if not group_col and entity_col and (
            any(k in q for k in ["distribution", "breakdown"])
            or (any(k in q for k in ["top", "bottom", "highest", "lowest", "rank", "best", "worst"]) and any(k in q for k in ["product", "customer", "department", "user", "item", "category", "brand", "role"]))
        ):
            group_col = entity_col

        # 6. Filter (WHERE Clause) Detection
        where_filters = []
        filter_descriptions = []

        # 6a. Numeric comparison filters (e.g. price > 30000, salary >= 80000, mileage < 20000)
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

        # 6b. Text distinct value matching across text columns in target table
        matched_text_cols = set()
        for c in text_cols:
            distinct_vals = _get_column_distinct_values(target_table, c)
            # Combine cached distinct values with sample rows
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
                    matched_text_cols.add(c)
                    break

        # 6c. Explicit column = value expressions (e.g. brand is Honda, role = Developer)
        for c in text_cols:
            if c in matched_text_cols:
                continue
            c_l = c.lower()
            m_col = re.search(rf"\b{re.escape(c_l)}\s*(?:is|=|equals|like)\s*['\"]?([a-zA-Z0-9_\s-]+?)['\"]?(?:\s+(?:and|or|\b)|\Z)", q)
            if m_col:
                v = m_col.group(1).strip()
                if v and v not in ["the", "a", "an"]:
                    clean_v = v.replace("'", "''")
                    where_filters.append(f'LOWER("{c}") = \'{clean_v.lower()}\'')
                    filter_descriptions.append(f"{c} is '{v}'")
                    matched_text_cols.add(c)

        # 6d. Status keywords
        if "status" in [c.lower() for c in all_cols] and "status" not in matched_text_cols:
            if "completed" in q:
                where_filters.append('"status" = \'Completed\'')
                filter_descriptions.append("status is 'Completed'")
            elif "fail" in q:
                where_filters.append('("status" = \'FAILURE\' OR "status" LIKE \'%FAIL%\')')
                filter_descriptions.append("status indicates failure")
            elif "active" in q:
                where_filters.append('"status" = \'Active\'')
                filter_descriptions.append("status is 'Active'")

        where_clause = f" WHERE {' AND '.join(where_filters)}" if where_filters else ""

        # 7. Aggregation Intent Analysis
        is_avg = any(k in q for k in ["average", "avg", "mean"])
        is_sum = any(k in q for k in ["total", "sum", "overall", "how much", "revenue", "spending", "spent", "budget"])
        is_count = any(k in q for k in ["count", "how many", "number of", "for each", "by"])
        is_max = any(k in q for k in ["highest", "max", "maximum", "greatest"]) and not has_explicit_limit
        is_min = any(k in q for k in ["lowest", "min", "minimum", "least", "cheapest"]) and not has_explicit_limit

        needs_group_by = bool(group_col and (
            by_match
            or any(k in q for k in ["average", "avg", "mean", "total", "sum", "distribution", "breakdown", "count", "how many"])
        ))

        # Branch 1: Group By Aggregation Query
        if needs_group_by and group_col:
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            elif is_max and metric_col:
                agg_fn, agg_alias = f'MAX("{metric_col}")', f'max_{metric_col}'
            elif is_min and metric_col:
                agg_fn, agg_alias = f'MIN("{metric_col}")', f'min_{metric_col}'
            elif metric_col and not is_count:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            else:
                agg_fn, agg_alias = 'COUNT(*)', 'total_count'

            l_clause = f" LIMIT {limit_val}" if has_explicit_limit else ""
            sql = f'SELECT "{group_col}", {agg_fn} AS {agg_alias} FROM "{target_table}"{where_clause} GROUP BY "{group_col}" ORDER BY {agg_alias} {direction}{l_clause};'
            explanation = f"Groups the '{target_table}' table by '{group_col}', computing {agg_alias.replace('_', ' ')} sorted in {direction_word} order."
            return sql, explanation

        # Branch 2: Single Scalar Aggregate (No Group By, No explicit limit > 1)
        if (is_avg or is_sum or (is_count and not has_explicit_limit) or is_max or is_min or any(k in q for k in ["how much", "how many", "overall total"])) and not (has_explicit_limit and limit_val > 1):
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            elif is_max and metric_col:
                agg_fn, agg_alias = f'MAX("{metric_col}")', f'highest_{metric_col}'
            elif is_min and metric_col:
                agg_fn, agg_alias = f'MIN("{metric_col}")', f'lowest_{metric_col}'
            elif metric_col and not is_count:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            else:
                agg_fn, agg_alias = 'COUNT(*)', 'total_count'

            sql = f'SELECT {agg_fn} AS {agg_alias} FROM "{target_table}"{where_clause};'
            explanation = f"Calculates overall {agg_alias.replace('_', ' ')} across records in the '{target_table}' table."
            return sql, explanation

        # Branch 3: Ranked Ordering (Highest / Lowest / Top N)
        if (is_highest or is_lowest or "top" in q or "bottom" in q or "rank" in q or "sort" in q) and metric_col:
            sql = f'SELECT * FROM "{target_table}"{where_clause} ORDER BY "{metric_col}" {direction} LIMIT {limit_val};'
            explanation = f"Retrieves the {rank_label} {limit_val} records from '{target_table}' ordered by '{metric_col}' in {direction_word} order."
            return sql, explanation

        # Branch 4: Chronological / Recent Query
        if date_cols and any(k in q for k in ["recent", "latest", "newest", "last"]):
            d_col = date_cols[0]
            sql = f'SELECT * FROM "{target_table}"{where_clause} ORDER BY "{d_col}" DESC LIMIT {limit_val};'
            explanation = f"Retrieves the most recent records from '{target_table}' sorted chronologically by '{d_col}' in descending order."
            return sql, explanation

        # Branch 5: Filtered or Browse Query
        sql = f'SELECT * FROM "{target_table}"{where_clause} LIMIT {limit_val};'
        if where_filters:
            explanation = f"Retrieves records from '{target_table}' where {', '.join(filter_descriptions)} (up to {limit_val} records)."
        else:
            explanation = f"Retrieves the first {limit_val} records from the '{target_table}' table."
        return sql, explanation

    def _clean_sql(self, raw_sql: str) -> str:
        """Strips markdown fences and leading/trailing whitespace from SQL."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()
