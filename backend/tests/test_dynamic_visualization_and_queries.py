"""
Test suite validating dynamic SQL generation, dataset isolation,
dynamic chart recommendation (Line, Pie, Bar, None), and absence of stale or hardcoded data.
Verifies at least 5 different questions against the same uploaded CSV.
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def generate_ecommerce_csv() -> bytes:
    """Generate an ecommerce CSV dataset with dates, categories, methods, status, and amounts."""
    header = "order_id,customer_name,category,order_date,status,payment_method,amount,quantity"
    rows = [
        "101,Alice Smith,Electronics,2024-01-15,completed,credit_card,1200.00,1",
        "102,Bob Jones,Clothing,2024-01-20,completed,paypal,150.50,2",
        "103,Charlie Brown,Home & Kitchen,2024-02-05,pending,credit_card,320.00,1",
        "104,Diana Prince,Electronics,2024-02-14,completed,apple_pay,850.00,1",
        "105,Evan Wright,Books,2024-02-28,completed,stripe,45.00,3",
        "106,Fiona Gallagher,Clothing,2024-03-02,refunded,paypal,210.00,1",
        "107,George Clark,Home & Kitchen,2024-03-10,completed,wire_transfer,540.00,2",
        "108,Hannah Abbott,Electronics,2024-03-18,completed,credit_card,650.00,1",
        "109,Ian Malcolm,Books,2024-04-05,completed,stripe,95.00,2",
        "110,Julia Roberts,Clothing,2024-04-12,pending,apple_pay,310.00,2",
        "111,Kevin Bacon,Electronics,2024-04-22,completed,wire_transfer,1400.00,1",
        "112,Laura Croft,Home & Kitchen,2024-05-01,completed,credit_card,420.00,1"
    ]
    return (f"{header}\n" + "\n".join(rows)).encode("utf-8")


@pytest.fixture(scope="module")
def uploaded_dataset():
    client = TestClient(app)
    csv_bytes = generate_ecommerce_csv()
    tbl_name = "test_ecommerce_store"

    res = client.post(
        "/api/upload",
        files={"file": ("ecommerce_data.csv", csv_bytes, "text/csv")},
        data={"table_name": tbl_name}
    )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    return {
        "client": client,
        "table_name": data["tableName"],
        "dataset_id": data["datasetId"],
        "row_count": data["row_count"]
    }


def test_q1_aggregation_category_breakdown(uploaded_dataset):
    """
    Question 1: Aggregation across categories.
    Should produce Bar chart grouped by category, distinct SQL with GROUP BY and SUM.
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    q = f"Total amount by category in {tbl}"
    res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    sql = data["sql"].lower()
    assert "group by" in sql
    assert "category" in sql
    assert "amount" in sql

    # Verify rows
    rows = data["rows"]
    assert len(rows) >= 3
    cats = {r["category"] for r in rows}
    assert "Electronics" in cats
    assert "Clothing" in cats

    # Verify dynamic chart selection: Bar chart
    chart = data["chart"]
    assert chart is not None
    assert chart["recommended"] is True
    assert chart["chart_type"] == "bar"
    assert chart["x_axis_key"] == "category"
    assert "total_amount" in chart["y_axis_keys"]
    assert "Category" in chart["title"]


def test_q2_status_distribution_pie_chart(uploaded_dataset):
    """
    Question 2: Status distribution with small cardinality (3 statuses: completed, pending, refunded).
    Should produce Pie chart grouped by status.
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    q = f"Count {tbl} by status"
    res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    sql = data["sql"].lower()
    assert "group by" in sql
    assert "status" in sql

    rows = data["rows"]
    assert len(rows) == 3
    statuses = {r["status"] for r in rows}
    assert "completed" in statuses
    assert "pending" in statuses
    assert "refunded" in statuses

    # Verify dynamic chart selection: Pie chart for small status distribution
    chart = data["chart"]
    assert chart is not None
    assert chart["recommended"] is True
    assert chart["chart_type"] == "pie"
    assert chart["x_axis_key"] == "status"
    assert "count" in chart["y_axis_keys"]
    assert "Status" in chart["title"]


def test_q3_time_series_line_chart(uploaded_dataset):
    """
    Question 3: Monthly trend over time.
    Should produce Line chart with chronological month grouping.
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    q = f"Show monthly amount in {tbl}"
    res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    sql = data["sql"].lower()
    assert "strftime" in sql or "month" in sql
    assert "group by" in sql

    rows = data["rows"]
    assert len(rows) >= 3
    months = [r["month"] for r in rows]
    assert months == sorted(months)  # Chronological order

    # Verify dynamic chart selection: Line chart
    chart = data["chart"]
    assert chart is not None
    assert chart["recommended"] is True
    assert chart["chart_type"] == "line"
    assert chart["x_axis_key"] == "month"
    assert "Over Time" in chart["title"]


def test_q4_superlative_ranking_no_fabricated_chart(uploaded_dataset):
    """
    Question 4: Superlative / single-row top answer.
    Should produce single row with highest amount, and NO fabricated chart (Requirement 8).
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    q = f"Which category has highest amount in {tbl}?"
    res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    sql = data["sql"].lower()
    assert "order by" in sql
    assert "limit 1" in sql or data["row_count"] == 1

    # Single row result
    assert len(data["rows"]) == 1
    top_cat = data["rows"][0]["category"]
    assert top_cat == "Electronics"

    # Requirement 8: Single-row superlative MUST NOT fabricate a chart
    assert data["chart"] is None

    # Natural-language answer includes entity and value
    assert "Electronics" in data["answer"]
    assert "highest" in data["answer"].lower()


def test_q5_scalar_count_no_fabricated_chart(uploaded_dataset):
    """
    Question 5: Scalar aggregate count question.
    Should return single count value, and NO fabricated chart (Requirement 8).
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    q = f"How many orders are in {tbl}?"
    res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    sql = data["sql"].lower()
    assert "count" in sql

    assert len(data["rows"]) == 1
    val = list(data["rows"][0].values())[0]
    assert val == 12

    # Requirement 8: Single scalar MUST NOT fabricate a chart
    assert data["chart"] is None
    assert "12" in data["answer"]


def test_q6_raw_table_scan_no_fabricated_chart(uploaded_dataset):
    """
    Question 6: Show all records in uploaded dataset.
    Should return full tabular records, and NO fabricated multi-bar ID chart.
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    q = f"Show all {tbl}"
    res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["row_count"] == 12
    assert len(data["rows"]) == 12

    # Verify no chart is forced for high-column raw table dumps
    assert data["chart"] is None


def test_distinct_queries_produce_distinct_charts_and_sqls(uploaded_dataset):
    """
    Cross-validation: run 5 questions against same CSV sequentially and assert:
    - Each generates a different SQL query.
    - Each produces a different chart type or config.
    - Results are never identical/hardcoded.
    """
    client = uploaded_dataset["client"]
    tbl = uploaded_dataset["table_name"]
    did = uploaded_dataset["dataset_id"]

    questions = [
        f"Total amount by category in {tbl}",
        f"Count {tbl} by status",
        f"Show monthly amount in {tbl}",
        f"Which category has highest amount in {tbl}?",
        f"How many orders are in {tbl}?"
    ]

    sqls = []
    charts = []
    answers = []

    for q in questions:
        res = client.post("/api/query", json={"question": q, "tableName": tbl, "datasetId": did})
        assert res.status_code == 200
        d = res.json()
        assert d["status"] == "success"
        sqls.append(d["sql"])
        charts.append(d["chart"]["chart_type"] if d["chart"] else "none")
        answers.append(d["answer"])

    # 1. Assert all 5 SQL queries are distinct
    assert len(set(sqls)) == 5, f"Expected 5 distinct SQL queries, got: {sqls}"

    # 2. Assert chart types include bar, pie, line, and none
    assert "bar" in charts
    assert "pie" in charts
    assert "line" in charts
    assert "none" in charts

    # 3. Assert explanations are distinct
    assert len(set(answers)) == 5
