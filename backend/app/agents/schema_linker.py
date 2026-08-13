import json
import os
import httpx
from typing import Dict, Any, List

class SchemaLinkerAgent:
    """
    Schema Linking Agent:
    Extracts core entities, metrics, filters, and joins from natural language queries
    and links them to the exact database schema tables and columns.
    """
    def __init__(self, api_key: str = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider.lower()

    def run(self, user_query: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identifies relevant tables and columns from schema_info based on user_query.
        Returns linked schema summary + agent thought logs.
        """
        thought_log = []
        thought_log.append(f"🔍 Analyzing user intent: '{user_query}'")

        # Basic deterministic fallback logic for common enterprise intents if offline or key missing
        target_tables = []
        query_lower = user_query.lower()

        if any(w in query_lower for w in ["product", "revenue", "item", "top", "selling", "stock", "rating", "category"]):
            target_tables.append("products")
        if any(w in query_lower for w in ["sale", "revenue", "order", "monthly", "trend", "transaction", "region"]):
            target_tables.append("sales")
        if any(w in query_lower for w in ["customer", "client", "user", "plan", "country", "spent"]):
            target_tables.append("customers")
        if any(w in query_lower for w in ["audit", "log", "security", "login", "event", "ip", "action", "fail"]):
            target_tables.append("audit_logs")

        if not target_tables:
            target_tables = list(schema_info.keys())

        # If LLM API Key is provided, call Gemini or OpenAI for deeper semantic schema linking
        if self.api_key:
            try:
                llm_res = self._call_llm_schema_linking(user_query, schema_info)
                if llm_res and "tables" in llm_res:
                    target_tables = llm_res["tables"]
                    thought_log.append(f"🧠 LLM Schema Linking confidence: HIGH. Mapped to: {', '.join(target_tables)}")
                    return {
                        "relevant_tables": target_tables,
                        "linked_schema": {t: schema_info[t] for t in target_tables if t in schema_info},
                        "reasoning": llm_res.get("reasoning", "Mapped entities via semantic schema matching."),
                        "thought_log": thought_log
                    }
            except Exception as e:
                thought_log.append(f"⚠️ LLM call fallback due to: {str(e)}")

        thought_log.append(f"✅ Schema Linking completed. Selected tables: {', '.join(target_tables)}")
        return {
            "relevant_tables": target_tables,
            "linked_schema": {t: schema_info[t] for t in target_tables if t in schema_info},
            "reasoning": f"Identified core business entities matching '{user_query}'. Filtered schema from {len(schema_info)} tables down to {len(target_tables)}.",
            "thought_log": thought_log
        }

    def _call_llm_schema_linking(self, user_query: str, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
Given the database schema below and user query:
User Query: "{user_query}"

Schema:
{json.dumps(schema_info, indent=2)}

Respond with JSON format only:
{{
  "tables": ["table1", "table2"],
  "reasoning": "Explanation of why these tables and columns are required for the query."
}}
"""
        # Quick API call using standard httpx for maximum reliability
        if "gemini" in self.provider and self.api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            with httpx.Client(timeout=10) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    clean_text = text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text)
        return None
