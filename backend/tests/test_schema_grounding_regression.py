"""Regression coverage for live-schema grounding in the NL-to-SQL path."""

from backend.app.services.pipeline import TextToSqlPipeline
from backend.app.services.schema_service import get_db_schema_info
from backend.app.services.sql_executor import execute_safe_query, validate_sql_against_live_schema


def test_llm_sql_omitting_requested_table_is_rejected(monkeypatch):
    """A schema-valid audit query cannot answer a customer question."""
    pipeline = TextToSqlPipeline(provider="gemini", api_key="test-key")
    monkeypatch.setattr(
        pipeline.generator,
        "_generate_with_llm",
        lambda *_args, **_kwargs: ("SELECT * FROM audit_logs LIMIT 10", "Wrong dataset"),
    )

    sql, _explanation, generated_by = pipeline.generator.generate(
        "How many customers are in the database?", get_db_schema_info(force_refresh=True)
    )

    assert generated_by == "Deterministic Analytics Engine"
    assert "customers" in sql.lower()
    assert "audit_logs" not in sql.lower()


def test_live_schema_preflight_rejects_unknown_table_and_column():
    valid, error = validate_sql_against_live_schema("SELECT imaginary_column FROM customers")
    assert valid is False
    assert "Column" in (error or "")

    valid, error = validate_sql_against_live_schema("SELECT * FROM imaginary_table")
    assert valid is False
    assert "Table" in (error or "")


def test_invalid_table_question_returns_schema_error_without_substitution():
    result = TextToSqlPipeline(provider="fallback").run("Show rows from imaginary_table")
    assert result["success"] is False
    assert result["sql"] == ""
    assert "Table 'imaginary_table' does not exist" in (result["error"] or "")


def test_required_ecommerce_questions_use_live_rows():
    pipeline = TextToSqlPipeline(provider="fallback")
    expectations = [
        ("Customer count", "customers", 1, 12),
        ("First 10 products", "products", 8, None),
        ("All orders", "orders", 30, None),
    ]
    for question, table, row_count, scalar in expectations:
        result = pipeline.run(question)
        assert result["success"] is True
        assert table in result["sql"].lower()
        assert result["row_count"] == row_count
        if scalar is not None:
            assert next(iter(result["rows"][0].values())) == scalar


def test_dynamic_all_request_does_not_become_ten_row_preview():
    pipeline = TextToSqlPipeline(provider="fallback")
    schema = get_db_schema_info(force_refresh=True)
    sql, _ = pipeline.generator._synthesize_dynamic_sql("show all orders", schema, target_table="orders")
    result = pipeline.corrector.heal_and_execute(sql, "show all orders", schema, execute_safe_query)
    assert "LIMIT" not in sql.upper()
    assert result["success"] is True
    assert result["row_count"] == 30

