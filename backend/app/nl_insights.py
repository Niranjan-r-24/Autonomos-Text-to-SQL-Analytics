"""
Natural language explanation and automatic visualization recommendation module.
Translates raw SQL execution results into plain-English summaries and chart specifications.
"""
from typing import List, Dict, Any, Optional

def generate_natural_language_answer(
    question: str,
    sql: str,
    columns: List[str],
    rows: List[Dict[str, Any]]
) -> str:
    """
    Produce a grounded, factual natural-language summary strictly from actual returned data.
    """
    if not rows:
        return f"Query returned 0 results matching your request: '{question}'."

    num_rows = len(rows)

    # 1. Single scalar result (e.g., COUNT(*), SUM(total_amount))
    if num_rows == 1 and len(columns) == 1:
        col = columns[0]
        val = rows[0][col]
        if isinstance(val, (int, float)):
            formatted_val = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
            if "count" in col.lower() or "how many" in question.lower():
                return f"Total count found: {formatted_val}."
            if "revenue" in question.lower() or "sum" in col.lower() or "total" in col.lower():
                return f"Calculated total: ${formatted_val}."
            return f"Result: {formatted_val}."
        return f"Result: {val}."

    # 2. Single row with multiple metrics (e.g. highest revenue product)
    if num_rows == 1:
        parts = [f"{col}: {val}" for col, val in rows[0].items()]
        return f"Top result found: {', '.join(parts)}."

    # 3. Grouped counts / categories (e.g. status breakdowns)
    if num_rows <= 10 and len(columns) == 2:
        cat_col, val_col = columns[0], columns[1]
        # Identify which is numeric
        if isinstance(rows[0][val_col], (int, float)):
            breakdown = [f"{r[cat_col]} ({r[val_col]:,})" if isinstance(r[val_col], int) else f"{r[cat_col]} ({r[val_col]:,.2f})" for r in rows]
            return f"Breakdown by {cat_col}: " + ", ".join(breakdown) + "."

    # 4. Multi-row tabular dataset
    return (
        f"Retrieved {num_rows} rows based on your query. "
        f"Fields included: {', '.join(columns)}."
    )

def recommend_chart_config(
    columns: List[str],
    rows: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Examine column types and cardinality to recommend the most insightful chart.
    Supports 'bar', 'line', and 'pie'.
    """
    if not rows or len(rows) < 2 or len(columns) < 2:
        return None

    # Identify string/category column and numeric column
    first_row = rows[0]
    string_cols = [c for c in columns if isinstance(first_row.get(c), str)]
    numeric_cols = [c for c in columns if isinstance(first_row.get(c), (int, float))]

    if not numeric_cols:
        return None

    # If there's a categorical column
    x_axis = string_cols[0] if string_cols else columns[0]
    y_axes = numeric_cols

    # Determine if x_axis represents time or dates
    is_time_series = any(term in x_axis.lower() for term in ["date", "month", "year", "day", "time"])
    
    if is_time_series:
        chart_type = "line"
    elif len(rows) <= 5 and len(y_axes) == 1:
        # Small category count works great for pie or bar
        chart_type = "pie"
    else:
        chart_type = "bar"

    return {
        "recommended": True,
        "chart_type": chart_type,
        "x_axis_key": x_axis,
        "y_axis_keys": y_axes,
        "title": f"{y_axes[0].replace('_', ' ').title()} by {x_axis.replace('_', ' ').title()}"
    }
