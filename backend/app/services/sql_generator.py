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
except ImportError:
    from app.services.schema_service import format_schema_for_llm

logger = logging.getLogger("text2sql.generator")

class SQLGenerator:
    """Generates SQL queries and plain-English query explanations from user natural language input."""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.provider = (provider or "gemini").lower()
        self.api_key = api_key or (
            os.getenv("GEMINI_API_KEY") if "gemini" in self.provider else os.getenv("OPENAI_API_KEY")
        )

    def generate(self, user_question: str, schema_info: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        Generates SQL query and explanation for the provided user question.
        
        Args:
            user_question: The plain English question from the user.
            schema_info: Structured database schema dictionary.
            
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
        sql, explanation = self._generate_deterministic(user_question, schema_info)
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

    def _generate_deterministic(self, user_question: str, schema_info: Dict[str, Any]) -> Tuple[str, str]:
        """
        Provides high-precision, intent-aware deterministic SQL queries and explanations.
        Correctly recognizes ranking direction (ASC for lowest/bottom, DESC for top/highest),
        metrics (revenue, units sold, spending, orders, rating), filters, and limits.
        """
        q = user_question.lower()

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

        # Pattern: Single aggregate KPI ("total revenue", "what is total sales", "how much revenue")
        if ("total" in q or "overall" in q or "sum" in q or "how much" in q) and ("revenue" in q or "sales" in q) and not any(k in q for k in ["product", "customer", "region", "month", "by"]):
            sql = (
                "SELECT SUM(total_price) AS total_revenue, COUNT(id) AS total_sales "
                "FROM sales WHERE status = 'Completed';"
            )
            explanation = "Calculates overall total revenue and completed sales count across all transactions."
            return sql, explanation

        # Pattern: Products by Units Sold / Quantity
        if ("unit" in q or "quantity" in q or "volume" in q or "sold" in q) and ("product" in q or "item" in q or "top" in q or "bottom" in q or "lowest" in q or "highest" in q):
            sql = (
                f"SELECT p.name AS product_name, p.category, SUM(s.quantity) AS total_quantity "
                f"FROM sales s JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed' "
                f"GROUP BY p.id, p.name, p.category "
                f"ORDER BY total_quantity {direction}{limit_clause};"
            )
            explanation = (
                f"Joins the 'sales' and 'products' tables, filters for completed transactions, "
                f"and aggregates total quantity sold for {rank_label} products sorted in {direction_word} order."
            )
            return sql, explanation

        # Pattern: Products by Revenue / Sales
        if ("revenue" in q or "sales" in q or "price" in q) and ("product" in q or "item" in q):
            sql = (
                f"SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders "
                f"FROM sales s JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed' "
                f"GROUP BY p.id, p.name, p.category "
                f"ORDER BY total_revenue {direction}{limit_clause};"
            )
            explanation = (
                f"Joins the 'sales' and 'products' tables, filters for completed transactions, "
                f"and aggregates total revenue for {rank_label} products sorted in {direction_word} order."
            )
            return sql, explanation

        # Pattern: Customers by Spending / Value
        if ("customer" in q or "user" in q or "client" in q) and ("spent" in q or "spending" in q or "revenue" in q or "highest" in q or "lowest" in q or "top" in q or "bottom" in q):
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
        if "customer" in q and ("plan" in q or "country" in q or "distribution" in q or "count" in q):
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
        if ("month" in q or "monthly" in q or "trend" in q or "time" in q) and ("sale" in q or "revenue" in q):
            sql = (
                "SELECT strftime('%Y-%m', sale_date) AS sales_month, region, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions "
                "FROM sales "
                "WHERE status = 'Completed' "
                "GROUP BY sales_month, region "
                "ORDER BY sales_month ASC, monthly_revenue DESC;"
            )
            explanation = (
                "Extracts year and month from 'sale_date' in the 'sales' table, grouping by month and geographical region "
                "to calculate monthly revenue and transaction volume."
            )
            return sql, explanation

        # Pattern: Sales by Region
        if "region" in q:
            sql = (
                f"SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales, AVG(total_price) AS avg_sale_value "
                f"FROM sales "
                f"WHERE status = 'Completed' "
                f"GROUP BY region "
                f"ORDER BY total_revenue {direction};"
            )
            explanation = (
                f"Calculates total revenue, transaction counts, and average order value across geographical regions in {direction_word} order."
            )
            return sql, explanation

        # Pattern: Product Categories & Ratings
        if "category" in q or "rating" in q or "stock" in q:
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
        if any(k in q for k in ["audit", "audit_log", "audit_logs", "security", "ip_address"]) or ("log" in q and not "catalog" in q) or ("fail" in q and "event" in q):
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
        if target_table and schema_info and target_table in schema_info:
            sql = f'SELECT * FROM "{target_table}" LIMIT {limit_val};'
            explanation = f"Retrieves the first {limit_val} records from the '{target_table}' table."
            return sql, explanation

        # Safe Default: NEVER default to audit_logs for business questions!
        if schema_info:
            if "product" in q or "item" in q:
                fallback_table = "products" if "products" in schema_info else "sales"
            elif "customer" in q or "client" in q:
                fallback_table = "customers" if "customers" in schema_info else "sales"
            elif "sale" in q or "revenue" in q or "order" in q or "sales" in schema_info:
                fallback_table = "sales"
            elif "products" in schema_info:
                fallback_table = "products"
            else:
                non_audit = [t for t in schema_info.keys() if t != "audit_logs"]
                fallback_table = non_audit[0] if non_audit else "sales"
        else:
            fallback_table = "sales"

        sql = f'SELECT * FROM "{fallback_table}" LIMIT 10;'
        explanation = f"Retrieves sample records from the '{fallback_table}' table."
        return sql, explanation

    def _clean_sql(self, raw_sql: str) -> str:
        """Strips markdown fences and leading/trailing whitespace from SQL."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()
