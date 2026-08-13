import json
import os
import re
import httpx
from typing import Dict, Any, List

class SQLGeneratorAgent:
    """
    SQL Generator Agent:
    Transforms natural language queries and linked schema into valid, clean ANSI SQL code.
    """
    def __init__(self, api_key: str = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider.lower()

    def run(self, user_query: str, linked_schema: Dict[str, Any]) -> Dict[str, Any]:
        thought_log = []
        thought_log.append("⚙️ Generating ANSI SQL query from linked schema context...")

        # 1. Check LLM generation first if key available
        if self.api_key:
            try:
                llm_sql = self._call_llm_sql_generation(user_query, linked_schema)
                if llm_sql:
                    cleaned_sql = self._clean_sql(llm_sql)
                    thought_log.append("✨ LLM generated SQL query successfully.")
                    return {
                        "sql": cleaned_sql,
                        "thought_log": thought_log,
                        "generated_by": "LLM (" + self.provider + ")"
                    }
            except Exception as e:
                thought_log.append(f"⚠️ LLM SQL generation fallback due to: {str(e)}")

        # 2. High-precision rule-based SQL generator for analytics prompts & general patterns
        sql, explanation = self._fallback_sql_generator(user_query, linked_schema)
        thought_log.append(f"🤖 Deterministic SQL Engine applied: {explanation}")
        
        return {
            "sql": sql,
            "thought_log": thought_log,
            "generated_by": "Deterministic Analytics Engine"
        }

    def _clean_sql(self, raw_sql: str) -> str:
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()

    def _fallback_sql_generator(self, query: str, schema: Dict[str, Any]) -> tuple:
        q = query.lower()

        # Enterprise Query Pattern 1: Top 5 revenue products
        if "top" in q and "revenue" in q and "product" in q:
            return (
                "SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders "
                "FROM sales s JOIN products p ON s.product_id = p.id "
                "WHERE s.status = 'Completed' "
                "GROUP BY p.id, p.name, p.category "
                "ORDER BY total_revenue DESC LIMIT 5;",
                "Generated Top Revenue Products query with JOIN between sales & products."
            )

        # Enterprise Query Pattern 2: Monthly sales breakdown / trend
        if ("monthly" in q or "month" in q or "trend" in q) and "sale" in q:
            return (
                "SELECT strftime('%Y-%m', sale_date) AS sales_month, region, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions "
                "FROM sales "
                "WHERE status = 'Completed' "
                "GROUP BY sales_month, region "
                "ORDER BY sales_month ASC, monthly_revenue DESC;",
                "Generated Monthly Sales Breakdown query grouped by YYYY-MM and region."
            )

        # Enterprise Query Pattern 3: Customer distribution by plan & country
        if "customer" in q and ("plan" in q or "country" in q or "distribution" in q or "count" in q):
            return (
                "SELECT country, plan, COUNT(id) AS customer_count, AVG(total_spent) AS avg_spent "
                "FROM customers "
                "GROUP BY country, plan "
                "ORDER BY customer_count DESC;",
                "Generated Customer Distribution query grouped by country and subscription plan."
            )

        # Enterprise Query Pattern 4: Audit log / security events
        if "audit" in q or "log" in q or "failed" in q or "security" in q:
            return (
                "SELECT action, status, ip_address, COUNT(id) AS event_count, MAX(timestamp) AS last_occurred "
                "FROM audit_logs "
                "WHERE status = 'FAILURE' OR action LIKE '%FAIL%' "
                "GROUP BY action, status, ip_address "
                "ORDER BY event_count DESC LIMIT 10;",
                "Generated Audit Log Security Events query filtering failed logs."
            )

        # Enterprise Query Pattern 5: Product category ratings & stock
        if "category" in q or "rating" in q or "stock" in q:
            return (
                "SELECT category, COUNT(id) AS product_count, AVG(price) AS avg_price, AVG(rating) AS avg_rating, SUM(stock_quantity) AS total_stock "
                "FROM products "
                "GROUP BY category "
                "ORDER BY avg_rating DESC;",
                "Generated Product Category Breakdown with average rating & stock counts."
            )

        # Enterprise Query Pattern 6: Sales by region
        if "region" in q or "revenue by region" in q:
            return (
                "SELECT region, SUM(total_price) AS total_revenue, COUNT(id) AS total_sales, AVG(total_price) AS avg_sale_value "
                "FROM sales "
                "GROUP BY region "
                "ORDER BY total_revenue DESC;",
                "Generated Regional Sales Analytics query."
            )

        # Generic default query
        first_table = list(schema.keys())[0] if schema else "sales"
        return (
            f"SELECT * FROM {first_table} LIMIT 10;",
            f"Generated default sample query on table '{first_table}'."
        )

    def _call_llm_sql_generation(self, user_query: str, linked_schema: Dict[str, Any]) -> str:
        prompt = f"""
You are an expert Enterprise Database Architect and SQL Developer.
Generate a clean, standard SQLite/ANSI SQL query to answer the user query based strictly on the provided schema.

User Query: "{user_query}"

Database Schema:
{json.dumps(linked_schema, indent=2)}

Guidelines:
- Return ONLY the executable SQL query inside a ```sql code block.
- Use explicit column aliases for clarity (e.g., AS total_revenue, AS customer_count).
- Do not output any markdown text outside the sql code block.
"""
        if "gemini" in self.provider and self.api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            with httpx.Client(timeout=12) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
