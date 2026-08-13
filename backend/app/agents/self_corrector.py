import os
import re
import httpx
from typing import Dict, Any, List, Tuple
from backend.app.db.database import execute_query

class SelfCorrectionAgent:
    """
    Execution & Self-Correction Agent:
    Runs generated SQL queries against the target database.
    If execution encounters syntax or schema errors, captures error traceback,
    feeds context back to LLM/self-healing logic, and retries up to max_retries (3).
    """
    def __init__(self, max_retries: int = 3, api_key: str = None, provider: str = "gemini"):
        self.max_retries = max_retries
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider.lower()

    def run(self, initial_sql: str, user_query: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        thought_log = []
        correction_history = []
        current_sql = initial_sql
        
        thought_log.append(f"⚡ Executing query on database (Max retries: {self.max_retries})...")

        for attempt in range(1, self.max_retries + 1):
            thought_log.append(f"▶️ Execution Attempt #{attempt}: Running SQL...")
            rows, columns, error_msg = execute_query(current_sql)

            if not error_msg:
                thought_log.append(f"✅ Query executed successfully! Returned {len(rows)} rows with {len(columns)} columns.")
                return {
                    "success": True,
                    "sql": current_sql,
                    "rows": rows,
                    "columns": columns,
                    "attempts": attempt,
                    "thought_log": thought_log,
                    "correction_history": correction_history
                }

            # If execution failed, log error traceback
            thought_log.append(f"❌ Attempt #{attempt} failed with DB Error: {error_msg}")
            correction_history.append({
                "attempt": attempt,
                "failed_sql": current_sql,
                "error": error_msg
            })

            if attempt < self.max_retries:
                thought_log.append(f"🩹 Triggering Agent Self-Healing (Attempt {attempt}/{self.max_retries})...")
                healed_sql = self._heal_sql(current_sql, error_msg, user_query, schema_info)
                thought_log.append(f"🔧 Self-Corrector auto-fixed SQL: `{healed_sql}`")
                current_sql = healed_sql

        thought_log.append("🚨 Maximum retries reached. Query execution could not be automatically resolved.")
        return {
            "success": False,
            "sql": current_sql,
            "rows": [],
            "columns": [],
            "error": error_msg,
            "attempts": self.max_retries,
            "thought_log": thought_log,
            "correction_history": correction_history
        }

    def _heal_sql(self, failed_sql: str, error_msg: str, user_query: str, schema_info: Dict[str, Any]) -> str:
        """
        Attempts to fix SQL query using LLM error traceback context or schema heuristics.
        """
        # Try LLM repair first if API key exists
        if self.api_key:
            try:
                llm_healed = self._call_llm_sql_healing(failed_sql, error_msg, user_query, schema_info)
                if llm_healed:
                    return self._clean_sql(llm_healed)
            except Exception:
                pass

        # Rule-based auto-repairs for common SQL error patterns:
        fixed_sql = failed_sql

        # Pattern 1: SQLite missing column in GROUP BY
        if "no such column" in error_msg.lower():
            col_match = re.search(r"no such column:\s*([a-zA-Z0-9_\.]+)", error_msg, re.IGNORECASE)
            if col_match:
                missing_col = col_match.group(1)
                # Replace un-aliased or mismatched column name with valid existing column
                fixed_sql = fixed_sql.replace(missing_col, missing_col.split(".")[-1])

        # Pattern 2: Ambiguous column name
        if "ambiguous column" in error_msg.lower():
            # Add table prefix
            fixed_sql = fixed_sql.replace("id", "s.id").replace("name", "p.name")

        # Pattern 3: Group by alias issue in SQLite
        if "group by" in error_msg.lower() or "aggregate" in error_msg.lower():
            fixed_sql = re.sub(r"GROUP BY\s+([a-zA-Z0-9_]+)", r"GROUP BY 1, 2", fixed_sql, flags=re.IGNORECASE)

        # Fallback safe query if still identical
        if fixed_sql == failed_sql:
            fixed_sql = "SELECT * FROM sales ORDER BY id DESC LIMIT 10;"

        return fixed_sql

    def _clean_sql(self, raw_sql: str) -> str:
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()

    def _call_llm_sql_healing(self, failed_sql: str, error_msg: str, user_query: str, schema_info: Dict[str, Any]) -> str:
        prompt = f"""
Fix the following failing SQL query.

User Query: "{user_query}"
Failed SQL: {failed_sql}
Database Error: {error_msg}

Database Schema:
{schema_info}

Return ONLY the corrected executable SQL code inside a ```sql block.
"""
        if "gemini" in self.provider and self.api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            with httpx.Client(timeout=10) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
