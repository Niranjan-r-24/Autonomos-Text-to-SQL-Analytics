"""
Natural language explanation and automatic visualization recommendation module.
Translates raw SQL execution results into plain-English summaries and chart specifications.
"""
import re
from typing import List, Dict, Any, Optional


def format_metric_value(val: Any) -> str:
    """Format numeric values cleanly (e.g. 41600.0 -> 41600, 12.5 -> 12.50)."""
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        if isinstance(val, float):
            return f"{val:,.2f}"
        return f"{val:,}"
    return str(val)


def generate_natural_language_answer(
    question: str,
    sql: str,
    columns: List[str],
    rows: List[Dict[str, Any]]
) -> str:
    """
    Produce a grounded, natural-language executive summary strictly from actual returned data.
    Answers in clear, human language rather than raw database field outputs.
    """
    if not rows:
        return f"Query returned 0 results matching your request: '{question}'."

    num_rows = len(rows)
    q_lower = question.lower().strip()

    # 1. Single scalar result (e.g., COUNT(*), SUM(total_amount))
    if num_rows == 1 and len(columns) == 1:
        col = columns[0]
        val = rows[0][col]
        val_clean = format_metric_value(val)

        # Count questions (e.g. "How many customers are in the database?")
        if "how many" in q_lower or "count" in col.lower() or "count" in q_lower:
            m = re.search(r"(?:how many|count (?:of )?|total number of)\s+([a-zA-Z0-9_]+)", q_lower)
            if m:
                entity = m.group(1).rstrip("?")
                if "in the database" in q_lower or "in database" in q_lower:
                    return f"There are {val_clean} {entity} in the database."
                return f"There are {val_clean} {entity}."
            return f"There are {val_clean} records found."

        # Revenue / Total questions
        if "revenue" in q_lower or "revenue" in col.lower():
            return f"Total revenue is {val_clean}."
        if "sum" in col.lower() or "total" in col.lower() or "sales" in q_lower:
            return f"The calculated total is {val_clean}."
        return f"The result is {val_clean}."

    # 2. Single row with multiple metrics (e.g. "Which product generated the highest revenue?")
    if num_rows == 1:
        row = rows[0]

        # Identify entity column (e.g. name, product_name, customer_name, title)
        entity_col = None
        for c in ["name", "product_name", "customer_name", "title", "item", "product", "customer", "user"]:
            if c in row and isinstance(row[c], str) and row[c].strip():
                entity_col = c
                break

        if not entity_col:
            for c in columns:
                if (
                    c.lower() not in {"id", "uuid", "created_at", "updated_at", "status", "date", "month", "year"}
                    and isinstance(row.get(c), str)
                    and str(row.get(c)).strip()
                ):
                    entity_col = c
                    break

        # Identify metric/numeric value column
        metric_col = None
        for c in columns:
            if c != entity_col and c.lower() not in {"id", "customer_id", "product_id", "user_id", "order_id"}:
                if isinstance(row.get(c), (int, float)):
                    if any(term in c.lower() for term in ["revenue", "sales", "amount", "total", "count", "price", "quantity"]):
                        metric_col = c
                        break

        if not metric_col:
            for c in columns:
                if c != entity_col and c.lower() not in {"id", "customer_id", "product_id", "user_id", "order_id"}:
                    if isinstance(row.get(c), (int, float)):
                        metric_col = c
                        break

        if entity_col and metric_col:
            entity_name = row[entity_col]
            raw_val = row[metric_col]
            val_clean = format_metric_value(raw_val)

            # Revenue questions
            if "revenue" in q_lower:
                if any(term in q_lower for term in ["highest", "top", "most", "max", "maximum", "best"]):
                    return f"{entity_name} generated highest revenue with {val_clean}."
                elif any(term in q_lower for term in ["lowest", "least", "min", "minimum"]):
                    return f"{entity_name} generated lowest revenue with {val_clean}."
                return f"{entity_name} generated {val_clean} in revenue."

            # Other superlative questions (highest / top / most / max)
            if any(term in q_lower for term in ["highest", "top", "most", "max", "maximum", "best"]):
                metric_label = metric_col.replace("total_", "").replace("_", " ")
                return f"{entity_name} generated highest {metric_label} with {val_clean}."

            if any(term in q_lower for term in ["lowest", "least", "min", "minimum"]):
                metric_label = metric_col.replace("total_", "").replace("_", " ")
                return f"{entity_name} had lowest {metric_label} with {val_clean}."

            metric_label = metric_col.replace("_", " ")
            return f"{entity_name} has {metric_label} of {val_clean}."

        if entity_col:
            entity_name = row[entity_col]
            other_parts = [f"{c.replace('_', ' ')} is {row[c]}" for c in columns if c != entity_col and c.lower() != "id"]
            if other_parts:
                return f"{entity_name}: {', '.join(other_parts)}."
            return f"Found record for {entity_name}."

        parts = [f"{c.replace('_', ' ')} is {row[c]}" for c in columns if c.lower() != "id"]
        if parts:
            return f"Found matching record: {', '.join(parts)}."
        return "Found 1 matching record."

    # 3. Grouped counts / categories (e.g. "Count orders by status.")
    if num_rows <= 10 and len(columns) == 2:
        cat_col, val_col = columns[0], columns[1]
        if not isinstance(rows[0].get(val_col), (int, float)) and isinstance(rows[0].get(cat_col), (int, float)):
            cat_col, val_col = val_col, cat_col

        if isinstance(rows[0].get(val_col), (int, float)):
            items = []
            for r in rows:
                v = r.get(val_col)
                v_str = format_metric_value(v)
                items.append(f"{v_str} {r.get(cat_col)}")

            if len(items) > 1:
                breakdown_str = ", ".join(items[:-1]) + f", and {items[-1]}"
            else:
                breakdown_str = items[0]

            entity_type = "orders" if "order" in q_lower else ("customers" if "customer" in q_lower else "records")
            if "status" in cat_col.lower() or "status" in q_lower:
                return f"Order status breakdown: {breakdown_str}." if "order" in q_lower else f"Status breakdown: {breakdown_str}."
            if any(term in val_col.lower() for term in ["amount", "revenue", "sales", "price", "quota", "salary", "total", "sum", "avg"]):
                val_label = val_col.replace("total_", "").replace("avg_", "").replace("_", " ")
                return f"{cat_col.replace('_', ' ').title()} breakdown by {val_label}: {breakdown_str}."
            return f"Breakdown by {cat_col.replace('_', ' ')}: {breakdown_str}."

    # 4. Multi-row tabular dataset
    entity_type = "records"
    for word in ["products", "orders", "customers", "payments", "users", "logs", "sales", "quota"]:
        if word in q_lower:
            entity_type = word
            break
    if entity_type == "records":
        for word in ["product", "order", "customer", "payment", "user", "log", "rep"]:
            if word in q_lower:
                entity_type = f"{word}s"
                break

    name_col = next((c for c in ["name", "product_name", "customer_name", "title", "sales_rep", "payment_method"] if c in columns), None)
    if name_col:
        sample_names = [str(r[name_col]) for r in rows[:3] if r.get(name_col)]
        if sample_names:
            if num_rows > len(sample_names):
                return f"Retrieved {num_rows} {entity_type}, including {', '.join(sample_names)}, and others."
            return f"Retrieved {num_rows} {entity_type}: {', '.join(sample_names)}."

    if any(term in q_lower for term in ["monthly", "revenue", "month"]) and "month" in columns:
        first_m = rows[0].get("month", "")
        last_m = rows[-1].get("month", "")
        return f"Retrieved monthly revenue across {num_rows} months spanning {first_m} to {last_m}."

    return f"Retrieved {num_rows} {entity_type} from the database."


def is_id_or_non_metric_column(col_name: str) -> bool:
    """Detect whether a column name represents an identifier, postal code, or non-metric code."""
    c = col_name.lower().strip()
    if c in {"id", "_id", "_row_id", "row_id", "uuid", "guid", "index"}:
        return True
    if c.endswith("_id") or c.startswith("id_"):
        return True
    if c in {"zip", "zip_code", "postal_code", "phone", "phone_number", "ssn", "pin", "code", "file_name"}:
        return True
    return False


def is_numeric_value(val: Any) -> bool:
    """Check if value is genuine numeric and not a boolean."""
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str) and val.strip():
        try:
            float(val.strip())
            return True
        except ValueError:
            return False
    return False


def is_temporal_column(col_name: str, sample_vals: List[Any]) -> bool:
    """Determine whether column represents time/date."""
    c = col_name.lower().strip()
    # If column clearly names a metric (e.g. monthly_amount, daily_sales, yearly_revenue), it is a metric, not a date!
    if any(m in c for m in ["amount", "revenue", "sales", "count", "total", "avg", "price", "quota", "cost", "profit", "salary", "quantity"]):
        return False
    if any(t in c for t in ["date", "month", "year", "day", "time", "quarter", "period", "timestamp", "created_at"]):
        return True
    date_patterns = [
        re.compile(r"^\d{4}-\d{2}-\d{2}"),
        re.compile(r"^\d{4}-\d{2}$"),
        re.compile(r"^\d{2}/\d{2}/\d{4}"),
        re.compile(r"^\d{4}$")
    ]
    str_vals = [str(v).strip() for v in sample_vals if v is not None and str(v).strip()]
    if not str_vals:
        return False
    matches = sum(1 for v in str_vals if any(p.match(v) for p in date_patterns))
    return matches >= len(str_vals) * 0.7


def recommend_chart_config(
    columns: List[str],
    rows: List[Dict[str, Any]],
    question: Optional[str] = None,
    sql: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Examine returned SQL result data to recommend an appropriate, dynamic chart.
    Supports 'bar', 'line', and 'pie' visualizations.
    Guarantees no chart is recommended for single scalars or raw multi-column entity dumps.
    """
    # 1. Minimum dimensions check: at least 2 rows and 2 columns
    if not rows or len(rows) < 2 or not columns or len(columns) < 2:
        return None

    sample_rows = rows[:15]

    # 2. Inspect column data types across sample rows
    valid_metric_cols = []
    text_or_cat_cols = []
    temporal_cols = []

    for c in columns:
        vals = [r.get(c) for r in sample_rows if r.get(c) is not None]
        if not vals:
            continue

        num_count = sum(1 for v in vals if is_numeric_value(v))
        is_num = (num_count / len(vals)) >= 0.7

        if is_temporal_column(c, vals):
            temporal_cols.append(c)
        elif is_num and not is_id_or_non_metric_column(c):
            valid_metric_cols.append(c)
        elif not is_id_or_non_metric_column(c):
            text_or_cat_cols.append(c)

    # 3. Requirement 8: If no genuine numeric metric to plot, do not fabricate a chart
    if not valid_metric_cols:
        return None

    # 4. Filter out raw multi-column table dumps (e.g. SELECT * FROM table with 5+ mixed columns)
    # Aggregation queries usually produce 2 to 4 columns.
    sql_upper = (sql or "").upper()
    has_group_by = "GROUP BY" in sql_upper
    if len(columns) > 4 and not has_group_by:
        # High-cardinality raw table dumps belong in the tabular view, not a chart
        return None

    # 5. Determine X-axis and Y-axis keys
    if temporal_cols:
        x_axis = temporal_cols[0]
    elif text_or_cat_cols:
        x_axis = text_or_cat_cols[0]
    else:
        # Fall back to first non-metric column, or first column
        candidate = [c for c in columns if c not in valid_metric_cols]
        x_axis = candidate[0] if candidate else columns[0]

    y_axes = [c for c in valid_metric_cols if c != x_axis]
    if not y_axes:
        return None

    # 6. Dynamically select chart type based on data characteristics
    is_time_series = x_axis in temporal_cols or is_temporal_column(x_axis, [r.get(x_axis) for r in sample_rows])
    q_lower = (question or "").lower()

    if is_time_series:
        chart_type = "line"
    elif (
        len(rows) <= 4
        and len(y_axes) == 1
        and (
            any(w in q_lower for w in ["status", "share", "proportion", "distribution", "breakdown", "pie"])
            or "status" in x_axis.lower()
        )
    ):
        # Small category proportion/distribution works best as pie
        chart_type = "pie"
    else:
        # Comparison across categories or metrics works best as bar
        chart_type = "bar"

    # 7. Formulate a clean, dynamic title
    metric_title = y_axes[0].replace("_", " ").title()
    group_title = x_axis.replace("_", " ").title()

    if chart_type == "line":
        chart_title = f"{metric_title} Trend Over Time"
    elif chart_type == "pie":
        chart_title = f"{metric_title} Breakdown by {group_title}"
    else:
        if len(y_axes) > 1:
            chart_title = f"{', '.join(k.replace('_', ' ').title() for k in y_axes)} by {group_title}"
        else:
            chart_title = f"{metric_title} by {group_title}"

    return {
        "recommended": True,
        "chart_type": chart_type,
        "x_axis_key": x_axis,
        "y_axis_keys": y_axes,
        "title": chart_title
    }
