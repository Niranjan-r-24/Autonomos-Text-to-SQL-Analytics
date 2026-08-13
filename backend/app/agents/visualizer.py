from typing import Dict, Any, List

class VisualizationAgent:
    """
    Visualization Agent:
    Analyzes query result structure, data types, cardinality, and temporal dimensions
    to automatically determine the optimal chart configuration (Bar, Line, Pie, Area, Table)
    and maps X/Y axis bindings.
    """
    def run(self, columns: List[str], rows: List[Dict[str, Any]], user_query: str) -> Dict[str, Any]:
        thought_log = []
        thought_log.append("📊 Analyzing result structure & data types for dynamic visual rendering...")

        if not rows or not columns:
            thought_log.append("⚠️ Empty dataset. Defaulting to raw table layout.")
            return {
                "chart_type": "table",
                "x_axis": None,
                "y_axes": [],
                "title": "Query Results (Table View)",
                "thought_log": thought_log
            }

        # Analyze column data characteristics
        sample_row = rows[0]
        numeric_cols = []
        string_cols = []
        date_cols = []

        for col in columns:
            val = sample_row.get(col)
            col_lower = col.lower()

            if any(k in col_lower for k in ["date", "time", "month", "year", "day"]):
                date_cols.append(col)
            elif isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).isdigit()):
                # Exclude ID columns from y-axis numbers unless it's explicitly a metric
                if not col_lower.endswith("_id") and col_lower != "id":
                    numeric_cols.append(col)
                else:
                    string_cols.append(col)
            else:
                string_cols.append(col)

        chart_type = "bar"
        x_axis = string_cols[0] if string_cols else (date_cols[0] if date_cols else columns[0])
        y_axes = numeric_cols if numeric_cols else [c for c in columns if c != x_axis][:2]

        # 1. Temporal data -> Line or Area Chart
        if date_cols:
            x_axis = date_cols[0]
            chart_type = "line" if len(rows) > 6 else "area"
            thought_log.append(f"📈 Detected temporal axis '{x_axis}'. Recommended visualization: {chart_type.upper()} chart.")

        # 2. Categorical distribution with <= 6 items -> Pie / Donut Chart
        elif len(rows) <= 6 and numeric_cols and string_cols and any(k in user_query.lower() for k in ["share", "distribution", "breakdown", "plan", "percent", "proportion"]):
            chart_type = "pie"
            thought_log.append(f"🥧 Detected proportional distribution ({len(rows)} categories). Recommended visualization: PIE chart.")

        # 3. Aggregated comparison -> Bar Chart
        elif numeric_cols and (string_cols or date_cols):
            chart_type = "bar"
            thought_log.append(f"📊 Detected category metrics ({x_axis} vs {', '.join(y_axes)}). Recommended visualization: BAR chart.")

        # 4. Fallback to Table view if no numerical metric found
        else:
            chart_type = "table"
            thought_log.append("📋 Result contains non-numeric structural data. Recommended visualization: TABLE view.")

        return {
            "chart_type": chart_type,
            "x_axis": x_axis,
            "y_axes": y_axes,
            "title": f"Analytics: {user_query.capitalize()}",
            "thought_log": thought_log
        }
