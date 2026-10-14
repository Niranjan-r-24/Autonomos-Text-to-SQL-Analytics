"""
Text-to-SQL Pipeline Orchestrator.
Coordinates the end-to-end workflow:
User Question -> Retrieve Schema -> Generate SQL & Explanation -> Safely Execute Query -> Recommend Visualization.
"""
import time
import logging
from typing import Optional, Dict, Any, List
try:
    from backend.app.services.schema_service import get_db_schema_info
    from backend.app.services.sql_generator import SQLGenerator
    from backend.app.services.sql_executor import execute_safe_query
    from backend.app.services.insights_service import BusinessInsightsInterpreter
except ImportError:
    from app.services.schema_service import get_db_schema_info
    from app.services.sql_generator import SQLGenerator
    from app.services.sql_executor import execute_safe_query
    from app.services.insights_service import BusinessInsightsInterpreter

logger = logging.getLogger("text2sql.pipeline")

class TextToSqlPipeline:
    """Orchestrates the conversion of natural language questions to safe SQL execution and visualization."""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "gemini"):
        self.api_key = api_key
        self.provider = provider
        self.generator = SQLGenerator(api_key=api_key, provider=provider)
        self.interpreter = BusinessInsightsInterpreter(api_key=api_key, provider=provider)


    def run(self, user_question: str) -> Dict[str, Any]:
        """
        Executes the full Text-to-SQL pipeline for a user question.
        
        Returns:
            Dict containing:
                - question (str)
                - success (bool)
                - sql (str)
                - explanation (str)
                - generated_by (str)
                - rows (List[Dict[str, Any]])
                - columns (List[str])
                - row_count (int)
                - execution_time_sec (float)
                - visualization (Dict[str, Any])
                - error (Optional[str])
        """
        start_time = time.time()
        logger.info("Pipeline started for question: '%s'", user_question)

        # 1. Retrieve current database schema
        schema_info = get_db_schema_info()

        # 2. Generate SQL and natural language explanation
        sql_query, explanation, generated_by = self.generator.generate(user_question, schema_info)

        # 3. Safely execute the query
        exec_result = execute_safe_query(sql_query)

        # 4. Interpret execution results into human-readable business insights
        insights = self.interpreter.interpret(
            question=user_question,
            sql_query=sql_query,
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            error=exec_result.get("error")
        )

        # 5. Infer optimal visualization settings
        visualization = self._infer_visualization(
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            user_question=user_question
        )

        total_duration_sec = round(time.time() - start_time, 3)
        logger.info(
            "Pipeline completed in %.3fs: success=%s, rows=%d, error=%s",
            total_duration_sec, exec_result["success"], exec_result["row_count"], exec_result["error"]
        )

        return {
            "question": user_question,
            "success": exec_result["success"],
            "sql": sql_query,
            "explanation": explanation,
            "generated_by": generated_by,
            "insights": insights,
            "rows": exec_result["rows"],
            "columns": exec_result["columns"],
            "row_count": exec_result["row_count"],
            "execution_time_sec": total_duration_sec,
            "sql_execution_time_ms": exec_result["execution_time_ms"],
            "visualization": visualization,
            "error": exec_result["error"]
        }

    def _infer_visualization(self, columns: List[str], rows: List[Dict[str, Any]], user_question: str) -> Dict[str, Any]:
        """
        Recommends one appropriate default chart type, axes, metric labels, and ranking order.
        - Bar chart for rankings and categorical comparisons (with explicit highest/lowest order labeling).
        - Line chart for time-series trends.
        - Pie chart for proportions with few categories (<= 6 rows).
        - Table for detailed records or unsuitable chart data.
        """
        if not rows or not columns:
            return {
                "chart_type": "table",
                "x_axis": "",
                "y_axes": [],
                "title": f"Results for: {user_question}",
                "ranking_order": "none",
                "metric_label": "Value"
            }

        sample_row = rows[0]
        numeric_cols = []
        string_cols = []
        date_cols = []

        for col in columns:
            val = sample_row.get(col)
            col_lower = col.lower()

            if any(k in col_lower for k in ["date", "time", "month", "year", "day"]):
                date_cols.append(col)
            elif isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "", 1).isdigit()):
                if not col_lower.endswith("_id") and col_lower != "id":
                    numeric_cols.append(col)
                else:
                    string_cols.append(col)
            else:
                string_cols.append(col)

        x_axis = string_cols[0] if string_cols else (date_cols[0] if date_cols else columns[0])
        y_axes = numeric_cols if numeric_cols else [c for c in columns if c != x_axis][:2]
        primary_metric_label = y_axes[0].replace("_", " ").title() if y_axes else "Value"

        q_lower = user_question.lower()
        is_lowest = any(k in q_lower for k in [
            "lowest", "bottom", "least", "worst", "cheapest", "smallest", "ascending", "asc", "min", "minimum", "fewest"
        ])
        is_highest = any(k in q_lower for k in [
            "top", "highest", "most", "best", "greatest", "largest", "expensive", "descending", "desc", "max", "maximum"
        ])

        # Determine ranking direction
        ranking_order = "none"
        if numeric_cols and (is_lowest or is_highest or "sort" in q_lower or "rank" in q_lower or "order by" in q_lower):
            if len(rows) > 1:
                first_v = float(rows[0].get(numeric_cols[0], 0) or 0)
                last_v = float(rows[-1].get(numeric_cols[0], 0) or 0)
                if first_v < last_v:
                    ranking_order = "asc"
                elif first_v > last_v:
                    ranking_order = "desc"
                else:
                    ranking_order = "asc" if is_lowest else "desc"
            else:
                ranking_order = "asc" if is_lowest else "desc"

        # 1. Temporal data -> Line Chart
        if date_cols:
            x_axis = date_cols[0]
            chart_type = "line"
            title = f"{primary_metric_label} Over Time"
        # 2. Proportion or small categorical distribution -> Pie Chart (<= 6 rows)
        elif len(rows) <= 6 and numeric_cols and any(k in q_lower for k in ["distribution", "share", "plan", "proportion", "breakdown"]):
            chart_type = "pie"
            title = f"{primary_metric_label} Distribution by {x_axis.replace('_', ' ').title()}"
        # 3. Rankings and categorical comparisons -> Bar Chart
        elif numeric_cols:
            chart_type = "bar"
            if ranking_order == "asc":
                title = f"Lowest {len(rows)} by {primary_metric_label} (Ascending Order)"
            elif ranking_order == "desc":
                title = f"Top {len(rows)} by {primary_metric_label} (Descending Order)"
            else:
                title = f"{primary_metric_label} Comparison"
        else:
            chart_type = "table"
            title = f"Data Records for: {user_question}"

        return {
            "chart_type": chart_type,
            "x_axis": x_axis,
            "y_axes": y_axes,
            "title": title,
            "ranking_order": ranking_order,
            "metric_label": primary_metric_label
        }
