"""
Services package for Text-to-SQL Analytics.
Includes schema inspection, SQL generation with explanations, and safe execution.
"""
from backend.app.services.schema_service import get_db_schema_info, format_schema_for_llm
from backend.app.services.sql_executor import execute_safe_query, validate_safe_sql
from backend.app.services.sql_generator import SQLGenerator
from backend.app.services.pipeline import TextToSqlPipeline

__all__ = [
    "get_db_schema_info",
    "format_schema_for_llm",
    "execute_safe_query",
    "validate_safe_sql",
    "SQLGenerator",
    "TextToSqlPipeline",
]
