"""
SQL and Query Explanation Generation Service.
Generates valid ANSI/SQLite SQL queries and plain-English explanations using LLMs
(Google Gemini, OpenAI) with a reliable deterministic offline fallback engine.
"""
import os
import re
import json
import logging
import httpx
from typing import Dict, Any, Tuple, Optional
try:
    from backend.app.services.schema_service import format_schema_for_llm
    from backend.app.db.database import engine
except ImportError:
    from app.services.schema_service import format_schema_for_llm
    try:
        from app.db.database import engine
    except Exception:
        engine = None

logger = logging.getLogger("text2sql.generator")

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
        logger.info("Generating SQL for question: '%s' using provider: %s", user_question, self.provider)

        # 1. Attempt LLM generation if API key is present
        if self.api_key and self.provider != "fallback":
            try:
                llm_sql, llm_explanation = self._generate_with_llm(user_question, schema_info)
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

    def _generate_with_llm(self, user_question: str, schema_info: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Invokes LLM API to generate JSON containing both SQL and explanation with strict ranking direction rules."""
        formatted_schema = format_schema_for_llm(schema_info)

        system_prompt = f"""You are an expert SQL Developer and Database Architect.
Generate a standard SQLite/ANSI SQL query and a short, clear plain English explanation for the user question.

DATABASE SCHEMA:
{formatted_schema}

CRITICAL INTENT AND RANKING RULES:
1. Strictly respect requested ranking direction:
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
            with httpx.Client(timeout=12) as client:
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
            with httpx.Client(timeout=12) as client:
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
        metrics (revenue, units sold, spending, orders, rating), filters, and limits.
        Strictly guards benchmark queries so they only fire when tables and columns exist in active schema.
        """
        q = user_question.lower()
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))

        # Check if user prompt explicitly references a custom/uploaded table
        # or if active_table was specified
        canonical_tables = {"sales", "products", "customers", "employees", "audit_logs", "sqlite_sequence"}
        target_custom_table = None
        for tbl in schema_info.keys():
            tbl_l = tbl.lower()
            if tbl_l not in canonical_tables:
                if tbl_l in q_tokens or tbl_l in q or tbl_l.replace("_", " ") in q or tbl_l.rstrip("s") in q_tokens:
                    target_custom_table = tbl
                    break
        if not target_custom_table and active_table and active_table in schema_info and active_table.lower() not in canonical_tables:
            target_custom_table = active_table

        if target_custom_table:
            return self._synthesize_dynamic_sql(user_question, schema_info, target_table=target_custom_table)

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

        # 2. Parse limit count
        limit_match = re.search(r"\b(?:top|bottom|lowest|highest|first|last|limit)?\s*(\d+)\b", q)
        limit_val = int(limit_match.group(1)) if limit_match else 5
        has_explicit_limit = bool(limit_match) or any(k in q for k in ["top", "bottom", "lowest", "highest", "limit", "first"])
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

        # Pattern: Security & Audit logs (Strictly require security or audit or log keywords)
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
        target_table = first_table_match.group(1).lower() if first_table_match else None
        if target_table and schema_info and target_table in schema_info and (
            any(k in q for k in ["first", "sample", "all rows", "show rows", "browse", "records"])
            or not any(k in q for k in ["where", "less", "greater", "more", "average", "avg", "count", "sum", "highest", "lowest", "by", ">", "<", "="])
        ):
            sql = f'SELECT * FROM "{target_table}" LIMIT {limit_val};'
            explanation = f"Retrieves the first {limit_val} records from the '{target_table}' table."
            return sql, explanation

        # Dynamic Schema Synthesizer: Intelligently handles custom tables, columns, metrics, and filters
        return self._synthesize_dynamic_sql(user_question, schema_info, target_table=target_custom_table)

    def _synthesize_dynamic_sql(self, user_question: str, schema_info: Dict[str, Any], target_table: Optional[str] = None) -> Tuple[str, str]:
        """
        Dynamically synthesizes schema-grounded SQL for arbitrary databases and custom tables
        when no static benchmark pattern matches.
        
        Performs:
        1. Multi-factor table resolution (exact, stemmed, column token matches, sample data).
        2. Column categorization (numeric, categorical, temporal).
        3. Intent mapping (aggregation, group-by, ranking, filtering, sorting, limits).
        4. Safe standard ANSI/SQLite query generation with clear explanation.
        """
        if not schema_info:
            return 'SELECT * FROM "sales" LIMIT 10;', "Retrieves sample records from the default sales table."

        q = user_question.lower()
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))

        # 1. Ranking & Limit Parsing
        is_lowest = any(k in q for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "min", "minimum", "fewest"
        ])
        is_highest = any(k in q for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "max", "maximum"
        ])
        direction = "ASC" if is_lowest and not is_highest else "DESC"
        direction_word = "ascending" if direction == "ASC" else "descending"
        rank_label = "lowest" if direction == "ASC" else "top"

        limit_match = re.search(r"\b(?:top|bottom|lowest|highest|first|last|limit)?\s*(\d+)\b", q)
        if limit_match:
            limit_val = int(limit_match.group(1))
            has_explicit_limit = True
        elif is_highest or is_lowest:
            if any(k in q for k in ["what is", "which is", "who is", "find the", "single", "most", "least"]):
                limit_val = 1
                has_explicit_limit = True
            else:
                limit_val = 5
                has_explicit_limit = True
        else:
            limit_val = 10
            has_explicit_limit = False

        # 2. Multi-Factor Table Resolution (if not already locked to a target table)
        if not target_table or target_table not in schema_info:
            scores = {}
            canonical_tables = {"sales", "products", "customers", "employees", "audit_logs", "sqlite_sequence"}

            for tbl_name, meta in schema_info.items():
                tbl_clean = tbl_name.lower()
                if tbl_clean == "sqlite_sequence":
                    continue
                score = 0
                
                # Exact or token match on table name
                if tbl_clean in q_tokens or tbl_clean in q:
                    score += 250
                elif tbl_clean.rstrip("s") in q_tokens or (tbl_clean + "s") in q_tokens:
                    score += 180
                elif any(part in q_tokens for part in tbl_clean.split("_") if len(part) > 2):
                    score += 80
                
                # Column token and semantic matches
                cols = meta.get("columns", [])
                for c in cols:
                    c_name = c["name"].lower()
                    if c_name in q_tokens:
                        score += 45
                    elif c_name.replace("_", " ") in q:
                        score += 40
                    elif len(c_name) > 3 and c_name in q:
                        score += 25

                    # Semantic synonym match
                    if any(k in q for k in ["revenue", "sales", "spending", "amount", "total"]):
                        if any(syn in c_name for syn in ["total_amount", "amount", "revenue", "sales", "total_price", "price"]):
                            score += 50
                    if any(k in q for k in ["product", "item", "good"]):
                        if any(syn in c_name for syn in ["product_name", "product", "item_name", "title"]):
                            score += 50
                    if any(k in q for k in ["customer", "user", "client"]):
                        if any(syn in c_name for syn in ["customer_name", "customer", "user", "username"]):
                            score += 50

                # Sample row value matches
                for row in meta.get("sample_rows", []):
                    for val in row.values():
                        if isinstance(val, str) and len(val) >= 3:
                            v_lower = val.lower()
                            if v_lower in q_tokens or v_lower in q:
                                score += 30
                                break

                # Boost custom uploaded tables if they have matching columns
                if tbl_clean not in canonical_tables and score > 0:
                    score += 75

                # Penalize audit_logs if no security/audit terms
                if tbl_clean == "audit_logs" and not any(k in q for k in ["audit", "log", "security", "ip", "fail"]):
                    score -= 100
                    
                scores[tbl_name] = score

            if not scores:
                target_table = list(schema_info.keys())[0]
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

            if any(k in c_type for k in ["INT", "FLOAT", "DOUBLE", "REAL", "NUMERIC", "DECIMAL"]):
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
            elif any(k in q for k in ["rating", "score", "stars"]):
                pref = ["rating", "score"]
            else:
                pref = ["total_amount", "salary", "total_price", "price", "revenue", "amount", "total_spent", "spent", "quantity", "stock_quantity", "stock", "rating", "units", "score", "cost", "credits", "value"]
            metric_col = next((c for p in pref for c in numeric_cols if p in c.lower()), (numeric_cols[0] if numeric_cols else None))

        # 5. Entity / Dimension Detection with Semantic Synonyms
        entity_col = None
        if any(k in q for k in ["product", "item", "good"]):
            prod_cols = [c for c in text_cols if any(syn in c.lower() for syn in ["product_name", "product", "item_name", "item", "title", "sku"])]
            if not prod_cols:
                prod_cols = [c for c in text_cols if "name" in c.lower() and "customer" not in c.lower() and "user" not in c.lower()]
            if prod_cols:
                entity_col = prod_cols[0]
        elif any(k in q for k in ["customer", "client", "user"]):
            cust_cols = [c for c in text_cols if any(syn in c.lower() for syn in ["customer_name", "customer", "user_name", "username", "client_name"])]
            if not cust_cols:
                cust_cols = [c for c in text_cols if "name" in c.lower() and "product" not in c.lower()]
            if cust_cols:
                entity_col = cust_cols[0]
        elif any(k in q for k in ["department", "dept"]):
            dept_cols = [c for c in text_cols if any(syn in c.lower() for syn in ["department", "dept"])]
            if dept_cols:
                entity_col = dept_cols[0]
        elif any(k in q for k in ["category", "genre", "type"]):
            cat_cols = [c for c in text_cols if any(syn in c.lower() for syn in ["category", "type", "genre"])]
            if cat_cols:
                entity_col = cat_cols[0]
        elif any(k in q for k in ["region", "country", "city", "state"]):
            geo_cols = [c for c in text_cols if any(syn in c.lower() for syn in ["region", "country", "city", "state"])]
            if geo_cols:
                entity_col = geo_cols[0]
        elif text_cols and (is_highest or is_lowest or any(k in q for k in ["top", "bottom", "rank", "sort", "who", "which", "list", "show", "first"])):
            candidate_text = [c for c in text_cols if not (c.lower() == "id" or c.lower().endswith("_id"))]
            entity_col = candidate_text[0] if candidate_text else text_cols[0]

        # Explicit Group By parsing (e.g. "by category", "per region", "by department")
        group_col = None
        by_match = re.search(r"\b(?:by|per|for each|in each|across)\s+([a-zA-Z0-9_]+)", q)
        if by_match:
            candidate = by_match.group(1).lower()
            for c in all_cols:
                if c.lower() == candidate or c.lower().rstrip("s") == candidate.rstrip("s"):
                    if c in numeric_cols and (is_highest or is_lowest or "top" in q or "bottom" in q or "rank" in q or "sort" in q):
                        metric_col = c
                    elif c not in numeric_cols:
                        group_col = c
                    break

        if not group_col and entity_col and (
            any(k in q for k in ["distribution", "breakdown"])
            or (any(k in q for k in ["top", "bottom", "highest", "lowest", "rank", "best", "worst"]) and any(k in q for k in ["product", "customer", "department", "user", "item", "category"]))
        ):
            group_col = entity_col

        # 6. Filter (WHERE Clause) Detection
        where_filters = []
        filter_descriptions = []

        candidate_filter_cols = [c for c in text_cols if not (c.lower() == "id" or c.lower().endswith("_id"))]
        stopwords = {"the", "all", "each", "every", "a", "an", "this", "sample", "table", "database", "here", "top", "bottom", "order", "orders", "first", "last", "rows", "records", "data"}

        for c in candidate_filter_cols:
            c_l = c.lower()
            matched_sample = False
            # Check sample rows for known values
            for r in table_meta.get("sample_rows", []):
                val = r.get(c)
                if val and isinstance(val, str) and len(val) >= 2:
                    if re.search(rf"\b{re.escape(val.lower())}\b", q):
                        clean_val = val.replace("'", "''")
                        where_filters.append(f'LOWER("{c}") = \'{clean_val.lower()}\'')
                        filter_descriptions.append(f"{c} is '{val}'")
                        matched_sample = True
                        break

            # Prepositional regex matching strictly to the corresponding domain column
            if not matched_sample:
                if c_l in ["country", "nation"]:
                    m = re.search(r"\b(?:from|country|nation|in)\s+([a-zA-Z]+)\b", q)
                    if m and m.group(1).lower() not in stopwords:
                        val_str = m.group(1).lower()
                        where_filters.append(f'LOWER("{c}") = \'{val_str}\'')
                        filter_descriptions.append(f"{c} is '{m.group(1)}'")
                elif c_l in ["department", "dept"]:
                    m = re.search(r"\b(?:department|dept|in)\s+([a-zA-Z]+)\b", q)
                    if m and m.group(1).lower() not in stopwords:
                        val_str = m.group(1).lower()
                        where_filters.append(f'LOWER("{c}") = \'{val_str}\'')
                        filter_descriptions.append(f"{c} is '{m.group(1)}'")
                elif c_l in ["plan", "tier"]:
                    m = re.search(r"\b(?:plan|tier)\s+([a-zA-Z]+)\b", q)
                    if m and m.group(1).lower() not in stopwords:
                        val_str = m.group(1).lower()
                        where_filters.append(f'LOWER("{c}") = \'{val_str}\'')
                        filter_descriptions.append(f"{c} is '{m.group(1)}'")
                elif c_l in ["city", "state", "region"]:
                    m = re.search(r"\b(?:city|state|region)\s+([a-zA-Z]+)\b", q)
                    if m and m.group(1).lower() not in stopwords:
                        val_str = m.group(1).lower()
                        where_filters.append(f'LOWER("{c}") = \'{val_str}\'')
                        filter_descriptions.append(f"{c} is '{m.group(1)}'")

        # Status completed / failure shortcuts
        if "completed" in q and "status" in [c.lower() for c in all_cols]:
            where_filters.append('"status" = \'Completed\'')
            filter_descriptions.append("status is 'Completed'")
        elif "fail" in q and "status" in [c.lower() for c in all_cols]:
            where_filters.append('("status" = \'FAILURE\' OR "status" LIKE \'%FAIL%\')')
            filter_descriptions.append("status indicates failure")
        elif "active" in q and "status" in [c.lower() for c in all_cols]:
            where_filters.append('"status" = \'Active\'')
            filter_descriptions.append("status is 'Active'")

        # Numeric comparison filters (e.g. price > 100, units < 50)
        for num_c in numeric_cols:
            pat = rf"\b{re.escape(num_c.lower())}\s*(>=|<=|>|<|=|greater than|more than|above|over|less than|below|under)\s*(\d+(?:\.\d+)?)\b"
            m = re.search(pat, q)
            if m:
                op_raw, n_val = m.group(1), m.group(2)
                op_map = {
                    ">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=",
                    "greater than": ">", "more than": ">", "above": ">", "over": ">",
                    "less than": "<", "below": "<", "under": "<"
                }
                op = op_map.get(op_raw, ">")
                where_filters.append(f'"{num_c}" {op} {n_val}')
                filter_descriptions.append(f"{num_c} {op} {n_val}")

        # Date / Temporal filters on target table
        if date_cols:
            d_col = date_cols[0]
            month_names = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
            month_map = {
                "january": "01", "february": "02", "march": "03", "april": "04",
                "may": "05", "june": "06", "july": "07", "august": "08",
                "september": "09", "october": "10", "november": "11", "december": "12"
            }
            month_pat = r"\b(" + "|".join(month_names) + r")(?:\s+(20[12]\d))?\b"
            dyn_between_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\s*(?:and|to)\s*(\d{4}-\d{2}-\d{2})\b", q)
            dyn_rel_year_match = re.search(r"\b(after|since|before|earlier than|later than)\s+(20[12]\d)\b", q)
            dyn_month_match = re.search(month_pat, q)
            dyn_year_match = re.search(r"\b(?:in|for|during|year|of)?\s*(20[12]\d)\b", q)

            if dyn_between_match:
                d1, d2 = dyn_between_match.group(1), dyn_between_match.group(2)
                where_filters.append(f'"{d_col}" BETWEEN \'{d1}\' AND \'{d2}\'')
                filter_descriptions.append(f"{d_col} between {d1} and {d2}")
            elif dyn_rel_year_match:
                op_w, yr = dyn_rel_year_match.group(1), dyn_rel_year_match.group(2)
                if op_w in ["after", "since", "later than"]:
                    where_filters.append(f'"{d_col}" >= \'{yr}-01-01\'')
                    filter_descriptions.append(f"{d_col} after {yr}")
                else:
                    where_filters.append(f'"{d_col}" < \'{yr}-01-01\'')
                    filter_descriptions.append(f"{d_col} before {yr}")
            elif dyn_month_match:
                m_name = dyn_month_match.group(1).lower()
                m_yr = dyn_month_match.group(2) or "2026"
                m_code = month_map[m_name]
                where_filters.append(f'"{d_col}" LIKE \'{m_yr}-{m_code}%\'')
                filter_descriptions.append(f"{d_col} in {m_name.capitalize()} {m_yr}")
            elif dyn_year_match:
                yr = dyn_year_match.group(1)
                where_filters.append(f'"{d_col}" LIKE \'{yr}%\'')
                filter_descriptions.append(f"{d_col} in {yr}")

        where_clause = f" WHERE {' AND '.join(where_filters)}" if where_filters else ""

        # Aggregation intent
        is_avg = any(k in q for k in ["average", "avg", "mean"])
        is_sum = any(k in q for k in ["total", "sum", "overall", "how much", "revenue", "sales", "spending", "spent", "amount", "volume"])
        is_count = any(k in q for k in ["count", "how many", "number of"])
        is_max = any(k in q for k in ["highest", "max", "maximum", "greatest"]) and not has_explicit_limit
        is_min = any(k in q for k in ["lowest", "min", "minimum", "least", "cheapest"]) and not has_explicit_limit

        # Determine if query requires GROUP BY aggregation or individual row ordering
        target_group = group_col or (entity_col if any(k in q for k in ["revenue", "sales", "spending", "spent", "volume", "total", "sum"]) else None)
        needs_group_by = bool(target_group and (
            by_match
            or any(k in q for k in ["average", "avg", "mean", "total", "sum", "distribution", "breakdown", "revenue", "sales", "spending", "spent", "volume"])
        ))

        # Branch 1: Group By Aggregation Query
        if needs_group_by and target_group:
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                alias_name = "total_revenue" if ("revenue" in q or "sales" in q) and "revenue" not in metric_col.lower() else f"total_{metric_col}"
                agg_fn, agg_alias = f'SUM("{metric_col}")', alias_name
            elif is_max and metric_col:
                agg_fn, agg_alias = f'MAX("{metric_col}")', f'max_{metric_col}'
            elif is_min and metric_col:
                agg_fn, agg_alias = f'MIN("{metric_col}")', f'min_{metric_col}'
            elif metric_col and not is_count:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            else:
                agg_fn, agg_alias = 'COUNT(*)', 'total_count'

            l_clause = f" LIMIT {limit_val}" if has_explicit_limit else ""
            sql = f'SELECT "{target_group}", {agg_fn} AS {agg_alias} FROM "{target_table}"{where_clause} GROUP BY "{target_group}" ORDER BY {agg_alias} {direction}{l_clause};'
            explanation = f"Groups the '{target_table}' table by '{target_group}', computing {agg_alias.replace('_', ' ')} sorted in {direction_word} order."
            return sql, explanation

        # Branch 2: Single Scalar Aggregate (No Group By, No explicit limit > 1)
        if (is_avg or is_sum or is_count or is_max or is_min or any(k in q for k in ["how much", "how many", "overall", "total", "revenue"])) and not (has_explicit_limit and limit_val > 1):
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                alias_name = "total_revenue" if ("revenue" in q or "sales" in q) and "revenue" not in metric_col.lower() else f"total_{metric_col}"
                agg_fn, agg_alias = f'SUM("{metric_col}")', alias_name
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
            preferred_disp = ["name", "emp_name", "customer_name", "product_name", "title", "department", "dept", "category", "country", "plan", "role", "email"]
            disp = [c for c in preferred_disp if c in all_cols]
            if not disp and entity_col:
                disp = [entity_col]
            if metric_col not in disp:
                disp.append(metric_col)
            sel_cols = ", ".join([f'"{c}"' for c in disp]) if disp else "*"

            sql = f'SELECT {sel_cols} FROM "{target_table}"{where_clause} ORDER BY "{metric_col}" {direction} LIMIT {limit_val};'
            explanation = f"Retrieves the {rank_label} {limit_val} records from '{target_table}' ordered by '{metric_col}' in {direction_word} order."
            return sql, explanation

        # Branch 4: Chronological / Recent Query
        if date_cols and any(k in q for k in ["recent", "latest", "newest", "last", "hired recently"]):
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
