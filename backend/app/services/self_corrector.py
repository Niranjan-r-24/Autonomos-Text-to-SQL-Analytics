"""
SQL Self-Correction and Query Healing Service.
Provides an autonomous multi-turn repair loop for SQL generation failures:
1. Catches database driver and execution errors (unknown columns, missing tables, ambiguous columns, syntax errors).
2. Attempts heuristic repair via schema analysis and token matching.
3. If an LLM API key is present, prompts the model with explicit error tracebacks and schema metadata.
4. Maintains audit history of all correction attempts.
"""
import os
import re
import difflib
import logging
import httpx
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("text2sql.self_corrector")


class SelfCorrectionService:
    """Autonomous SQL execution and query self-correction engine."""

    def __init__(self, max_retries: int = 3, api_key: Optional[str] = None, provider: str = "gemini"):
        self.max_retries = max_retries
        self.api_key = api_key or (
            os.getenv("GEMINI_API_KEY") if "gemini" in (provider or "").lower() else os.getenv("OPENAI_API_KEY")
        )
        self.provider = (provider or "gemini").lower()

    def heal_and_execute(
        self,
        initial_sql: str,
        user_question: str,
        schema_info: Dict[str, Any],
        execute_fn: Any
    ) -> Dict[str, Any]:
        """
        Executes SQL and automatically performs self-correction if an error is encountered.

        Args:
            initial_sql: The first SQL statement generated.
            user_question: The original user question.
            schema_info: Structured database schema dictionary.
            execute_fn: Function that safely executes SQL and returns a dict with 'success', 'rows', 'columns', 'error'.

        Returns:
            Dict containing:
                - success (bool)
                - final_sql (str)
                - rows (List[Dict[str, Any]])
                - columns (List[str])
                - row_count (int)
                - attempts (int)
                - correction_history (List[Dict[str, Any]])
                - error (Optional[str])
        """
        current_sql = self._pre_heal_sql(initial_sql, schema_info)
        correction_history: List[Dict[str, Any]] = []

        for attempt in range(1, self.max_retries + 1):
            logger.info("Self-Correction: Execution attempt %d/%d for query: %s", attempt, self.max_retries, current_sql)
            exec_res = execute_fn(current_sql)

            if exec_res.get("success"):
                logger.info("Self-Correction: Success on attempt %d (%d rows returned)", attempt, len(exec_res.get("rows", [])))
                return {
                    "success": True,
                    "final_sql": current_sql,
                    "rows": exec_res.get("rows", []),
                    "columns": exec_res.get("columns", []),
                    "row_count": exec_res.get("row_count", len(exec_res.get("rows", []))),
                    "execution_time_ms": exec_res.get("execution_time_ms", 0.0),
                    "attempts": attempt,
                    "correction_history": correction_history,
                    "error": None
                }

            # Capture failure
            error_msg = exec_res.get("error") or "Unknown database execution error"
            logger.warning("Execution attempt %d failed: %s", attempt, error_msg)

            # Record attempt in history
            correction_history.append({
                "attempt": attempt,
                "failed_sql": current_sql,
                "error": error_msg
            })

            # If retries remain, attempt to heal SQL
            if attempt < self.max_retries:
                healed_sql, strategy = self.heal_sql(
                    failed_sql=current_sql,
                    error_msg=error_msg,
                    user_question=user_question,
                    schema_info=schema_info
                )
                logger.info("Self-Correction: Strategy '%s' yielded healed SQL: %s", strategy, healed_sql)
                correction_history[-1]["healed_sql"] = healed_sql
                correction_history[-1]["strategy"] = strategy
                
                # If healed SQL is identical, break early to prevent infinite identical loop
                if healed_sql.strip() == current_sql.strip():
                    logger.info("Healed SQL is identical to failed SQL; stopping self-correction attempts.")
                    break
                current_sql = healed_sql

        return {
            "success": False,
            "final_sql": current_sql,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "execution_time_ms": exec_res.get("execution_time_ms", 0.0),
            "attempts": len(correction_history),
            "correction_history": correction_history,
            "error": exec_res.get("error") or "Maximum self-correction retries reached without successful execution."
        }

    def _pre_heal_sql(self, sql: str, schema_info: Dict[str, Any]) -> str:
        """Pre-normalizes SQL query against active database schema to prevent common column mismatches."""
        if not schema_info or not sql:
            return sql
        fixed = sql

        if "products" in schema_info:
            p_cols = {c["name"].lower(): c["name"] for c in schema_info["products"].get("columns", [])}
            actual_p_name = next((p_cols[k] for k in ["product_name", "name", "title", "item_name"] if k in p_cols), None)
            if actual_p_name and "name" not in p_cols:
                fixed = re.sub(r"\b(?:p|products)\.name\b", f"p.{actual_p_name}", fixed, flags=re.IGNORECASE)
            actual_p_id = next((p_cols[k] for k in ["product_id", "id", "item_id"] if k in p_cols), None)
            if actual_p_id and "id" not in p_cols:
                fixed = re.sub(r"\b(?:p|products)\.id\b", f"p.{actual_p_id}", fixed, flags=re.IGNORECASE)

        if "customers" in schema_info:
            c_cols = {c["name"].lower(): c["name"] for c in schema_info["customers"].get("columns", [])}
            actual_c_name = next((c_cols[k] for k in ["customer_name", "name", "full_name"] if k in c_cols), None)
            if actual_c_name and "name" not in c_cols:
                fixed = re.sub(r"\b(?:c|customers)\.name\b", f"c.{actual_c_name}", fixed, flags=re.IGNORECASE)
            actual_c_id = next((c_cols[k] for k in ["customer_id", "id", "user_id"] if k in c_cols), None)
            if actual_c_id and "id" not in c_cols:
                fixed = re.sub(r"\b(?:c|customers)\.id\b", f"c.{actual_c_id}", fixed, flags=re.IGNORECASE)

        if "orders" in schema_info:
            o_cols = {c["name"].lower(): c["name"] for c in schema_info["orders"].get("columns", [])}
            actual_o_id = next((o_cols[k] for k in ["order_id", "id"] if k in o_cols), None)
            if actual_o_id and "id" not in o_cols:
                fixed = re.sub(r"\b(?:o|orders)\.id\b", f"o.{actual_o_id}", fixed, flags=re.IGNORECASE)

        if "order_items" in schema_info:
            oi_cols = {c["name"].lower(): c["name"] for c in schema_info["order_items"].get("columns", [])}
            actual_oi_id = next((oi_cols[k] for k in ["order_item_id", "id"] if k in oi_cols), None)
            if actual_oi_id and "id" not in oi_cols:
                fixed = re.sub(r"\b(?:oi|order_items)\.id\b", f"oi.{actual_oi_id}", fixed, flags=re.IGNORECASE)

        fixed = re.sub(r"COUNT\s*\(\s*s\.id\s*\)", "COUNT(*)", fixed, flags=re.IGNORECASE)
        return fixed

    def heal_sql(
        self,
        failed_sql: str,
        error_msg: str,
        user_question: str,
        schema_info: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Repairs failing SQL query using deterministic heuristic rules first,
        falling back to LLM diagnostic repair if available.
        """
        # 1. Deterministic Rule-Based Self-Healing Heuristics (instant and schema-grounded)
        healed_sql, rule_name = self._heuristic_heal(failed_sql, error_msg, schema_info, user_question)
        if healed_sql and healed_sql.strip() != failed_sql.strip():
            healed_sql = self._pre_heal_sql(healed_sql, schema_info)
            return healed_sql, rule_name

        # 2. Try LLM repair if provider key is available
        if self.api_key and self.provider != "fallback":
            try:
                llm_sql = self._heal_with_llm(failed_sql, error_msg, user_question, schema_info)
                if llm_sql:
                    cleaned = self._clean_sql(llm_sql)
                    if cleaned:
                        cleaned = self._pre_heal_sql(cleaned, schema_info)
                        if cleaned != failed_sql:
                            return cleaned, "LLM Diagnostic Repair"
            except Exception as e:
                logger.warning("LLM self-correction call failed: %s", str(e))

        return failed_sql, "No applicable repair heuristic found"

    def _heuristic_heal(
        self,
        failed_sql: str,
        error_msg: str,
        schema_info: Dict[str, Any],
        user_question: str = ""
    ) -> Tuple[str, str]:
        """Applies deterministic regex and schema-aware repairs to failing SQL."""
        err_lower = error_msg.lower()
        fixed = failed_sql

        # Rule 0: Non-existent table - do NOT silently replace with an arbitrary table
        if any(k in err_lower for k in ["no such table", "table", "does not exist"]) and "column" not in err_lower:
            return failed_sql, "Unknown Table: Non-existent table cannot be automatically substituted"

        # Rule 1: Unknown Column -> Find closest matching column in active schema or re-synthesize
        if any(k in err_lower for k in ["no such column", "does not exist", "was not found", "unknown column"]):
            match = re.search(r"(?:no such column:\s*|column\s*['\"]?)([a-zA-Z0-9_\.]+)", error_msg, re.IGNORECASE)
            if match:
                bad_col_raw = match.group(1)
                has_prefix = "." in bad_col_raw
                prefix = bad_col_raw.split(".")[0] if has_prefix else ""
                bad_col = bad_col_raw.split(".")[-1].lower()

                # Map aliases to table names in SQL
                alias_to_table = {}
                for am in re.finditer(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\"]+)\s+(?:AS\s+)?([a-zA-Z0-9_]+)\b", failed_sql, re.IGNORECASE):
                    t_clean = am.group(1).replace('"', '').lower()
                    a_clean = am.group(2).lower()
                    if t_clean in schema_info:
                        alias_to_table[a_clean] = t_clean

                # Determine targeted table and candidate columns
                target_tbl = alias_to_table.get(prefix.lower()) if has_prefix else None
                sql_tables = [t for t in schema_info.keys() if re.search(r"\b" + re.escape(t) + r"\b", failed_sql, re.IGNORECASE)]
                
                if target_tbl and target_tbl in schema_info:
                    candidate_cols = [c["name"] for c in schema_info[target_tbl].get("columns", [])]
                elif sql_tables:
                    candidate_cols = []
                    for t in sql_tables:
                        candidate_cols.extend([c["name"] for c in schema_info[t].get("columns", [])])
                else:
                    candidate_cols = [c["name"] for t in schema_info.values() for c in t.get("columns", [])]

                all_cols = [c["name"] for t in schema_info.values() for c in t.get("columns", [])]

                # Match column
                matches = difflib.get_close_matches(bad_col, candidate_cols, n=1, cutoff=0.5)
                if not matches:
                    matches = [c for c in candidate_cols if bad_col in c.lower() or c.lower() in bad_col]
                if not matches:
                    matches = difflib.get_close_matches(bad_col, all_cols, n=1, cutoff=0.4)
                if not matches:
                    matches = [c for c in all_cols if bad_col in c.lower() or c.lower() in bad_col]

                if matches:
                    best_replacement = matches[0]
                    # If prefixed, keep table prefix intact
                    full_replacement = f"{prefix}.{best_replacement}" if has_prefix else best_replacement
                    fixed = re.sub(r"\b" + re.escape(bad_col_raw) + r"\b", full_replacement, fixed)

                    # Multi-column schema healing: If products or customers table had aliased id/name replaced,
                    # also heal companion id/name columns to avoid secondary failure on next retry
                    if target_tbl == "products" or (has_prefix and prefix.lower() == "p"):
                        p_cols = {c["name"].lower(): c["name"] for c in schema_info.get("products", {}).get("columns", [])}
                        if "product_id" in p_cols and "id" not in p_cols:
                            fixed = re.sub(r"\b(?:p|products)\.id\b", f"{prefix or 'p'}.product_id", fixed)
                        if "product_name" in p_cols and "name" not in p_cols:
                            fixed = re.sub(r"\b(?:p|products)\.name\b", f"{prefix or 'p'}.product_name", fixed)
                    elif target_tbl == "customers" or (has_prefix and prefix.lower() == "c"):
                        c_cols = {c["name"].lower(): c["name"] for c in schema_info.get("customers", {}).get("columns", [])}
                        if "customer_id" in c_cols and "id" not in c_cols:
                            fixed = re.sub(r"\b(?:c|customers)\.id\b", f"{prefix or 'c'}.customer_id", fixed)
                        if "customer_name" in c_cols and "name" not in c_cols:
                            fixed = re.sub(r"\b(?:c|customers)\.name\b", f"{prefix or 'c'}.customer_name", fixed)

                    if fixed != failed_sql:
                        return fixed, f"Schema Alignment: Corrected column '{bad_col_raw}' to '{full_replacement}'"

                # If direct string replacement failed, re-synthesize cleanly
                if schema_info:
                    from backend.app.services.sql_generator import SQLGenerator
                    gen = SQLGenerator()
                    healed_sql, exp = gen._synthesize_dynamic_sql(user_question, schema_info)
                    if healed_sql and healed_sql.strip() != failed_sql.strip():
                        return healed_sql, f"Schema Recovery: Re-synthesized query to resolve missing column '{bad_col_raw}'"

        # Rule 2: Ambiguous Column -> Disambiguate with matching table alias
        if "ambiguous column" in err_lower:
            match = re.search(r"ambiguous column(?:\s*name)?:\s*([a-zA-Z0-9_\.]+)", error_msg, re.IGNORECASE)
            ambig_col = match.group(1).split(".")[-1].lower() if match else None
            
            if ambig_col:
                # Find tables in query that define this column
                for am in re.finditer(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\"]+)\s+(?:AS\s+)?([a-zA-Z0-9_]+)\b", failed_sql, re.IGNORECASE):
                    tbl_name = am.group(1).replace('"', '').lower()
                    alias_name = am.group(2)
                    if tbl_name in schema_info:
                        cols = [c["name"].lower() for c in schema_info[tbl_name].get("columns", [])]
                        if ambig_col in cols:
                            fixed = re.sub(r"(?<![a-zA-Z0-9_\.])" + re.escape(ambig_col) + r"\b", f"{alias_name}.{ambig_col}", fixed)
                            if fixed != failed_sql:
                                return fixed, f"Disambiguation: Added '{alias_name}' alias to ambiguous column '{ambig_col}'"
                            break

            # Fallback re-synthesis if ambiguous column couldn't be cleanly resolved
            if schema_info:
                from backend.app.services.sql_generator import SQLGenerator
                gen = SQLGenerator()
                healed_sql, exp = gen._synthesize_dynamic_sql(user_question, schema_info)
                if healed_sql and healed_sql.strip() != failed_sql.strip():
                    return healed_sql, "Disambiguation Recovery: Re-synthesized query"

        # Rule 3: SQLite GROUP BY or aggregate alias issues
        if "misuse of aggregate" in err_lower or "group by" in err_lower:
            # Try replacing GROUP BY names with ordinal positions or base columns
            fixed = re.sub(r"GROUP BY\s+[a-zA-Z0-9_]+(?:\s*,\s*[a-zA-Z0-9_]+)*", "GROUP BY 1, 2", fixed, flags=re.IGNORECASE)
            if fixed != failed_sql:
                return fixed, "Syntax Repair: Simplified GROUP BY clause"

        # Rule 4: Trailing commas or missing parentheses
        if "syntax error" in err_lower:
            # Remove trailing comma before FROM or WHERE
            fixed = re.sub(r",\s*(FROM|WHERE|GROUP|ORDER)", r" \1", fixed, flags=re.IGNORECASE)
            if fixed != failed_sql:
                return fixed, "Syntax Repair: Removed dangling comma"

        # If unfixable, return the failed SQL honestly without misleading table substitutions
        return failed_sql, "No applicable repair heuristic found"

    def _heal_with_llm(
        self,
        failed_sql: str,
        error_msg: str,
        user_question: str,
        schema_info: Dict[str, Any]
    ) -> Optional[str]:
        """Calls LLM API with diagnostic traceback to generate a corrected SQL query."""
        try:
            from backend.app.services.schema_service import format_schema_for_llm
        except ImportError:
            from app.services.schema_service import format_schema_for_llm

        schema_str = format_schema_for_llm(schema_info)
        prompt = f"""You are an autonomous SQL Self-Correction Agent.
A previously generated SQL query failed with a database error.
Your task is to fix the query so that it executes safely and correctly on the database.

ORIGINAL USER QUESTION: "{user_question}"
FAILED SQL:
{failed_sql}

DATABASE ERROR TRACEBACK:
{error_msg}

DATABASE SCHEMA:
{schema_str}

RULES:
1. Return strictly valid read-only ANSI/SQLite SQL.
2. Fix the specific error mentioned in the traceback (e.g. correct column names, fix joins, resolve ambiguities).
3. Do not include markdown commentary, only the SQL query enclosed in ```sql ... ```.
"""
        if "gemini" in self.provider and self.api_key:
            models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
            for m_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0}
                }
                try:
                    with httpx.Client(timeout=15) as client:
                        res = client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            return data["candidates"][0]["content"]["parts"][0]["text"]
                        elif res.status_code == 404:
                            continue
                except Exception:
                    continue

        elif "openai" in self.provider and self.api_key:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }
            with httpx.Client(timeout=10) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]

        return None

    def _clean_sql(self, raw_sql: str) -> str:
        """Strips markdown fences and whitespaces from SQL."""
        sql = raw_sql.strip()
        sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"^```\s*", "", sql)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()
