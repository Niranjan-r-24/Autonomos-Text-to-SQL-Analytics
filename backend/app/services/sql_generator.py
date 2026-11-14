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

        # Pattern: Completed Sales Detailed Transactions with Customer and Product Names (Multi-Table 3-Way Join)
        if ("sale" in q or "transaction" in q or "order" in q) and ("customer" in q or "user" in q) and ("product" in q or "item" in q):
            sql = (
                "SELECT s.id, c.name AS customer_name, p.name AS product_name, s.total_price, s.sale_date "
                "FROM sales s "
                "JOIN customers c ON s.customer_id = c.id "
                "JOIN products p ON s.product_id = p.id "
                "WHERE s.status = 'Completed' "
                f"ORDER BY s.sale_date DESC{limit_clause or ' LIMIT 10'};"
            )
            explanation = (
                "Performs a three-table join across sales, customers, and products to list completed "
                "transaction records with customer and product names."
            )
            return sql, explanation

        # Pattern: Customer Spending by Product Category (Multi-Table 3-Way Join)
        if ("customer" in q or "plan" in q) and ("category" in q or "product category" in q) and ("spent" in q or "spending" in q or "revenue" in q or "sales" in q):
            sql = (
                "SELECT c.plan, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS sales_count "
                "FROM sales s "
                "JOIN customers c ON s.customer_id = c.id "
                "JOIN products p ON s.product_id = p.id "
                "WHERE s.status = 'Completed' "
                "GROUP BY c.plan, p.category "
                "ORDER BY total_revenue DESC;"
            )
            explanation = (
                "Performs a three-table join between sales, customers, and products to aggregate "
                "total revenue and transaction count by customer plan and product category."
            )
            return sql, explanation

        # Pattern: Average Order Value per Customer Plan (Multi-Table Join)
        if "plan" in q and ("order value" in q or "average order" in q or "avg order" in q or ("order" in q and ("average" in q or "avg" in q)) or "aov" in q):
            sql = (
                "SELECT c.plan, COUNT(s.id) AS order_count, AVG(s.total_price) AS avg_order_value, SUM(s.total_price) AS total_spent "
                "FROM sales s "
                "JOIN customers c ON s.customer_id = c.id "
                "WHERE s.status = 'Completed' "
                "GROUP BY c.plan "
                "ORDER BY avg_order_value DESC;"
            )
            explanation = (
                "Joins sales and customers by plan to calculate order count, average order value, "
                "and total spending per subscription tier."
            )
            return sql, explanation

        # Pattern: Products by Units Sold / Quantity
        if (("unit" in q and ("sold" in q or "sale" in q)) or "quantity" in q or "volume" in q or "sold" in q) and ("product" in q or "item" in q or "top" in q or "bottom" in q or "lowest" in q or "highest" in q) and not ("inventory" in q or "stock" in q):
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

        # Pattern: Products by Revenue / Sales or Default Benchmark Ranking
        if ("product" in q or "item" in q) and ("revenue" in q or "sales" in q or ("rank" in q and not "price" in q and not "rating" in q and not "stock" in q) or (is_highest and not "price" in q and not "rating" in q and not "stock" in q and not "unit" in q) or (is_lowest and not "price" in q and not "rating" in q and not "stock" in q and not "unit" in q)):
            is_unspecified_metric = not any(k in q for k in ["revenue", "sales", "price", "profit", "order"])
            sql = (
                f"SELECT p.name AS product_name, p.category, SUM(s.total_price) AS total_revenue, COUNT(s.id) AS total_orders "
                f"FROM sales s JOIN products p ON s.product_id = p.id "
                f"WHERE s.status = 'Completed' "
                f"GROUP BY p.id, p.name, p.category "
                f"ORDER BY total_revenue {direction}{limit_clause};"
            )
            if is_unspecified_metric:
                explanation = (
                    f"Defaulted to total revenue as the primary ranking benchmark since no metric was specified; "
                    f"aggregates completed sales for {rank_label} products in {direction_word} order (can also rank by quantity sold, order count, or customer rating)."
                )
            else:
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
            is_postgres = (engine is not None and getattr(engine, "dialect", None) is not None and engine.dialect.name == "postgresql")
            month_expr = "TO_CHAR(sale_date, 'YYYY-MM')" if is_postgres else "strftime('%Y-%m', sale_date)"
            sql = (
                f"SELECT {month_expr} AS sales_month, region, SUM(total_price) AS monthly_revenue, COUNT(id) AS total_transactions "
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
        if any(k in q for k in ["audit", "audit_log", "audit_logs", "security", "ip_address"]) or ("log" in q and not "catalog" in q) or ("fail" in q and ("event" in q or "log" in q)):
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
        return self._synthesize_dynamic_sql(user_question, schema_info)

    def _synthesize_dynamic_sql(self, user_question: str, schema_info: Dict[str, Any]) -> Tuple[str, str]:
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

        # 2. Multi-Factor Table Resolution
        scores = {}
        for tbl_name, meta in schema_info.items():
            tbl_clean = tbl_name.lower()
            score = 0
            
            # Exact or token match
            if tbl_clean in q_tokens or tbl_clean in q:
                score += 150
            elif tbl_clean.rstrip("s") in q_tokens or (tbl_clean + "s") in q_tokens:
                score += 100
            elif any(part in q_tokens for part in tbl_clean.split("_") if len(part) > 2):
                score += 40
            
            # Column token matches
            cols = meta.get("columns", [])
            for c in cols:
                c_name = c["name"].lower()
                if c_name in q_tokens:
                    score += 35
                elif c_name.replace("_", " ") in q:
                    score += 30
                elif len(c_name) > 3 and c_name in q:
                    score += 20
            
            # Sample row value matches
            for row in meta.get("sample_rows", []):
                for val in row.values():
                    if isinstance(val, str) and len(val) >= 3:
                        v_lower = val.lower()
                        if v_lower in q_tokens or v_lower in q:
                            score += 25
                            break
            
            # Penalize audit_logs if no security/audit terms
            if tbl_clean == "audit_logs" and not any(k in q for k in ["audit", "log", "security", "ip", "fail"]):
                score -= 100
                
            scores[tbl_name] = score

        if len(schema_info) == 1:
            target_table = list(schema_info.keys())[0]
        else:
            best_tbl = max(scores, key=scores.get)
            if scores[best_tbl] > 0:
                target_table = best_tbl
            else:
                non_audit = [t for t in schema_info.keys() if t != "audit_logs"]
                target_table = non_audit[0] if non_audit else list(schema_info.keys())[0]

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

        # 4. Metric Column Selection
        mentioned_num = [c for c in numeric_cols if c.lower() in q or c.lower().replace("_", " ") in q]
        if mentioned_num:
            metric_col = mentioned_num[0]
        elif numeric_cols:
            pref = ["salary", "total_price", "price", "revenue", "amount", "total_spent", "spent", "quantity", "stock_quantity", "stock", "rating", "units", "score", "cost", "credits", "value"]
            metric_col = next((c for p in pref for c in numeric_cols if p in c.lower()), numeric_cols[0])
        else:
            metric_col = None

        # 5. Dimension / Group By Detection
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

        if not group_col:
            # Check if any descriptive categorical column appears in q alongside aggregation intent
            if any(k in q for k in ["average", "avg", "mean", "total", "sum", "count", "how many", "distribution", "breakdown"]):
                candidate_text = [c for c in text_cols if not (c.lower() == "id" or c.lower().endswith("_id"))]
                for c in candidate_text:
                    c_l = c.lower()
                    if c_l in q_tokens or c_l.rstrip("s") in q_tokens or c_l in q:
                        group_col = c
                        break

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

        where_clause = f" WHERE {' AND '.join(where_filters)}" if where_filters else ""

        # Aggregation intent
        is_avg = any(k in q for k in ["average", "avg", "mean"])
        is_sum = any(k in q for k in ["total", "sum", "overall", "how much"])
        is_count = any(k in q for k in ["count", "how many", "number of"])
        is_max = any(k in q for k in ["highest", "max", "maximum", "greatest"]) and not has_explicit_limit
        is_min = any(k in q for k in ["lowest", "min", "minimum", "least", "cheapest"]) and not has_explicit_limit

        # Branch 1: Group By Query
        if group_col:
            if is_avg and metric_col:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            elif is_sum and metric_col:
                agg_fn, agg_alias = f'SUM("{metric_col}")', f'total_{metric_col}'
            elif is_max and metric_col:
                agg_fn, agg_alias = f'MAX("{metric_col}")', f'max_{metric_col}'
            elif is_min and metric_col:
                agg_fn, agg_alias = f'MIN("{metric_col}")', f'min_{metric_col}'
            elif metric_col and not is_count:
                agg_fn, agg_alias = f'AVG("{metric_col}")', f'avg_{metric_col}'
            else:
                agg_fn, agg_alias = 'COUNT(*)', 'total_count'

            l_clause = f" LIMIT {limit_val}" if has_explicit_limit else ""
            sql = f'SELECT "{group_col}", {agg_fn} AS {agg_alias} FROM "{target_table}"{where_clause} GROUP BY "{group_col}" ORDER BY {agg_alias} {direction}{l_clause};'
            explanation = f"Groups the '{target_table}' table by '{group_col}', computing {agg_alias.replace('_', ' ')} sorted in {direction_word} order."
            return sql, explanation

        # Branch 2: Single Scalar Aggregate (No Group By, No explicit limit > 1)
        if (is_avg or is_sum or is_count or is_max or is_min) and not (has_explicit_limit and limit_val > 1):
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
            preferred_disp = ["name", "emp_name", "customer_name", "product_name", "title", "department", "dept", "category", "country", "plan", "role", "email"]
            disp = [c for c in preferred_disp if c in all_cols]
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
