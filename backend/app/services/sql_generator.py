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
from backend.app.services.schema_service import format_schema_for_llm

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
        """Invokes LLM API to generate JSON containing both SQL and explanation."""
        formatted_schema = format_schema_for_llm(schema_info)

        system_prompt = f"""You are an expert SQL Developer and Database Architect.
Generate a standard SQLite/ANSI SQL query and a short, clear plain English explanation for the user question.

DATABASE SCHEMA:
{formatted_schema}

INSTRUCTIONS:
- Generate strictly read-only SELECT queries (JOINs, aggregations, GROUP BY, ORDER BY, LIMIT).
- Use clear column aliases (e.g., AS total_revenue, AS customer_count).
- Provide a 1-2 sentence explanation of what the query does (which tables are joined, filters used, and how results are aggregated/sorted).
- Respond in strictly valid JSON format with keys "sql" and "explanation".

JSON Response Format:
{{
  "sql": "SELECT ...",
  "explanation": "This query joins the sales and products tables to calculate total revenue per product, sorted in descending order."
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
        """Provides high-precision deterministic SQL queries and explanations for standard analytical prompts."""
        q = user_question.lower()

        # Pattern 1: Top revenue products
        if "top" in q and ("revenue" in q or "sales" in q or "price" in q) and "product" in q:
            sql = (
                "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders "
                "FROM sales s JOIN products p ON s.product_id = p.id "
                "WHERE s.status = 'Completed' "
                "GROUP BY p.id, p.name, p.category "
                "ORDER BY total_revenue DESC LIMIT 5;"
            )
            explanation = (
                "Joins the 'sales' and 'products' tables, filters for completed transactions, "
                "and aggregates total revenue and order count for the top 5 revenue-generating products."
            )
            return sql, explanation

        # Pattern 2: Monthly sales trend / revenue over time
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

        # Pattern 3: Customer distribution by plan / country
        if "customer" in q and ("plan" in q or "country" in q or "distribution" in q or "count" in q or "spent" in q):
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

        # Pattern 4: Security & Audit logs
        if "audit" in q or "log" in q or "security" in q or "failed" in q:
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

        # Pattern 5: Product categories & ratings
        if "category" in q or "rating" in q or "stock" in q:
            sql = (
                "SELECT category, COUNT(id) AS product_count, AVG(price) AS avg_price, AVG(rating) AS avg_rating, SUM(stock_quantity) AS total_stock "
                "FROM products "
                "GROUP BY category "
                "ORDER BY avg_rating DESC;"
            )
            explanation = (
                "Aggregates the 'products' table by category, calculating average price, average customer rating, "
                "and total available stock."
            )
            return sql, explanation

        # Pattern 6: Sales by region
        if "region" in q:
            sql = (
                "SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales, AVG(total_price) AS avg_sale_value "
                "FROM sales "
                "WHERE status = 'Completed' "
                "GROUP BY region "
                "ORDER BY total_revenue DESC;"
            )
            explanation = (
                "Calculates total revenue, transaction counts, and average order value across all geographical regions in the 'sales' table."
            )
            return sql, explanation

        # Default query for custom/uploaded tables or unknown intent
        first_table = list(schema_info.keys())[0] if schema_info else "sales"
        sql = f'SELECT * FROM "{first_table}" LIMIT 10;'
        explanation = f"Retrieves the first 10 sample records from the '{first_table}' table."
        return sql, explanation

    def _clean_sql(self, raw_sql: str) -> str:
        """Strips markdown fences and leading/trailing whitespace from SQL."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()
