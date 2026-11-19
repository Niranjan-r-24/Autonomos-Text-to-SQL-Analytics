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
            return f"Breakdown by {cat_col.replace('_', ' ')}: {breakdown_str}."

    # 4. Multi-row tabular dataset
    entity_type = "records"
    for word in ["products", "orders", "customers", "payments", "users", "logs"]:
        if word in q_lower:
            entity_type = word
            break
    if entity_type == "records":
        for word in ["product", "order", "customer", "payment", "user", "log"]:
            if word in q_lower:
                entity_type = f"{word}s"
                break

    name_col = next((c for c in ["name", "product_name", "customer_name", "title"] if c in columns), None)
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
