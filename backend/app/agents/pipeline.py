import time
import os
from typing import Dict, Any, Generator, List
from backend.app.db.database import get_db_schema_info
from backend.app.agents.schema_linker import SchemaLinkerAgent
from backend.app.agents.sql_generator import SQLGeneratorAgent
from backend.app.agents.self_corrector import SelfCorrectionAgent
from backend.app.agents.visualizer import VisualizationAgent

class TextToSqlPipeline:
    """
    Autonomous Multi-Agent Text-to-SQL Pipeline:
    Orchestrates Schema Linker -> SQL Generator -> Self-Corrector -> Data Visualizer.
    """
    def __init__(self, api_key: str = None, provider: str = "gemini"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider

    def run_pipeline(self, user_query: str) -> Dict[str, Any]:
        start_time = time.time()
        agent_steps = []

        # Step 0: DB Schema Extraction
        db_schema = get_db_schema_info()

        # Step 1: Schema Linker Agent
        t1 = time.time()
        schema_agent = SchemaLinkerAgent(api_key=self.api_key, provider=self.provider)
        schema_res = schema_agent.run(user_query, db_schema)
        schema_time = round(time.time() - t1, 3)

        agent_steps.append({
            "agent_id": "schema_linker",
            "agent_name": "Schema Linking Agent",
            "status": "COMPLETED",
            "execution_time_sec": schema_time,
            "output_summary": f"Linked {len(schema_res['relevant_tables'])} tables ({', '.join(schema_res['relevant_tables'])})",
            "thought_logs": schema_res["thought_log"],
            "data": {
                "relevant_tables": schema_res["relevant_tables"],
                "reasoning": schema_res["reasoning"]
            }
        })

        # Step 2: SQL Generator Agent
        t2 = time.time()
        sql_agent = SQLGeneratorAgent(api_key=self.api_key, provider=self.provider)
        sql_res = sql_agent.run(user_query, schema_res["linked_schema"])
        sql_time = round(time.time() - t2, 3)

        agent_steps.append({
            "agent_id": "sql_generator",
            "agent_name": "SQL Generator Agent",
            "status": "COMPLETED",
            "execution_time_sec": sql_time,
            "output_summary": f"Generated ANSI SQL via {sql_res.get('generated_by', 'LLM')}",
            "thought_logs": sql_res["thought_log"],
            "data": {
                "generated_sql": sql_res["sql"]
            }
        })

        # Step 3: Execution & Self-Correction Agent
        t3 = time.time()
        corrector_agent = SelfCorrectionAgent(max_retries=3, api_key=self.api_key, provider=self.provider)
        exec_res = corrector_agent.run(sql_res["sql"], user_query, schema_res["linked_schema"])
        exec_time = round(time.time() - t3, 3)

        status_str = "COMPLETED" if exec_res["success"] else "FAILED"
        agent_steps.append({
            "agent_id": "self_corrector",
            "agent_name": "Execution & Self-Corrector Agent",
            "status": status_str,
            "execution_time_sec": exec_time,
            "output_summary": f"Query Executed (Attempts: {exec_res['attempts']}/3, Rows: {len(exec_res['rows'])})",
            "thought_logs": exec_res["thought_log"],
            "data": {
                "final_sql": exec_res["sql"],
                "attempts": exec_res["attempts"],
                "correction_history": exec_res.get("correction_history", [])
            }
        })

        # Step 4: Visualization Agent
        t4 = time.time()
        vis_agent = VisualizationAgent()
        vis_res = vis_agent.run(exec_res["columns"], exec_res["rows"], user_query)
        vis_time = round(time.time() - t4, 3)

        agent_steps.append({
            "agent_id": "visualizer",
            "agent_name": "Visualization Agent",
            "status": "COMPLETED",
            "execution_time_sec": vis_time,
            "output_summary": f"Selected Chart Type: {vis_res['chart_type'].upper()}",
            "thought_logs": vis_res["thought_log"],
            "data": {
                "chart_type": vis_res["chart_type"],
                "x_axis": vis_res["x_axis"],
                "y_axes": vis_res["y_axes"],
                "title": vis_res["title"]
            }
        })

        total_time = round(time.time() - start_time, 3)

        return {
            "query": user_query,
            "success": exec_res["success"],
            "sql": exec_res["sql"],
            "rows": exec_res["rows"],
            "columns": exec_res["columns"],
            "total_execution_time_sec": total_time,
            "visualization": {
                "chart_type": vis_res["chart_type"],
                "x_axis": vis_res["x_axis"],
                "y_axes": vis_res["y_axes"],
                "title": vis_res["title"]
            },
            "agent_steps": agent_steps
        }
