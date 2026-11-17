"""
Autonomos Text-to-SQL Analytics Platform - FastAPI Main API
Provides REST endpoints for natural-language queries, manual SQL execution,
dynamic CSV dataset ingestion, schema introspection, RAG intelligence, and history.
"""
import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.config import DEFAULT_PROVIDER
from backend.app.db import engine, execute_raw_sql
from backend.app.seed import seed_benchmark_data
from backend.app.schema import get_database_schema, invalidate_schema_cache
from backend.app.sql_safety import validate_safe_sql, enforce_query_limit, extract_table_references
from backend.app.csv_loader import load_csv_to_table
from backend.app.text2sql import generate_sql_for_question, is_audit_query
from backend.app.nl_insights import generate_natural_language_answer, recommend_chart_config
from backend.app.rag import doc_store
from backend.app.history import record_query_execution, get_query_history, clear_query_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("text2sql.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed initial benchmark data if database is unseeded
    try:
        seed_benchmark_data(force=False)
        logger.info("Database initialized with benchmark dataset.")
    except Exception as e:
        logger.warning("Auto-seed on startup failed: %s", str(e))
    yield
    # Shutdown

app = FastAPI(
    title="Autonomos Text-to-SQL Analytics API",
    version="2.0.0",
    description="Production-ready AI-powered Text-to-SQL Analytics Platform",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Request / Response Models -----------------

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question to query.")
    provider: Optional[str] = Field(None, description="AI provider ('gemini', 'openai', or empty for default).")
    api_key: Optional[str] = Field(None, description="Optional custom API key.")

class ExecuteSqlRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="Raw SQL query to execute safely.")

class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question for document intelligence.")

# ----------------- Health & Status Endpoints -----------------

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Autonomos Text-to-SQL Analytics API"}

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Autonomos Text-to-SQL Analytics API",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "schema": "/api/schema",
            "query": "/api/query",
            "execute_sql": "/api/execute-sql",
            "upload_csv": "/api/upload-csv",
            "history": "/api/history",
            "rag_query": "/api/rag/query",
            "rag_upload": "/api/rag/upload",
            "seed": "/api/db/seed"
        }
    }

# ----------------- Schema Inspection Endpoints -----------------

@app.get("/api/schema")
def get_schema(refresh: bool = False):
    """Inspect active database tables, columns, data types, sample values, and row counts."""
    if refresh:
        invalidate_schema_cache()
    schema = get_database_schema(use_cache=not refresh)
    return {
        "status": "success",
        "tables": schema.get("tables", {}),
        "table_names": schema.get("table_names", []),
        "relationships": schema.get("relationships", [])
    }

# ----------------- CSV Upload & Dataset Management -----------------

@app.post("/api/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None)
):
    """
    Upload a CSV file, dynamically infer types, create a database table,
    and refresh the schema cache immediately.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported for dataset upload."
        )

    content = await file.read()
    target_table = table_name or file.filename.rsplit(".", 1)[0]

    try:
        res = load_csv_to_table(content, target_table, replace_existing=True)
        # Fetch fresh schema
        fresh_schema = get_database_schema(use_cache=False)
        return {
            "status": "success",
            "message": f"Dataset uploaded and table '{res['table_name']}' created successfully.",
            "dataset": res,
            "active_tables": fresh_schema.get("table_names", [])
        }
    except Exception as e:
        logger.error("CSV upload error: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# ----------------- Text-to-SQL Analytics Pipeline -----------------

@app.post("/api/query")
async def process_natural_language_query(req: QueryRequest):
    """
    End-to-end schema-first Text-to-SQL analytics pipeline.
    1. Retrieve schema
    2. Understand intent and select tables
    3. Generate SQL query
    4. Validate SQL safety and table references
    5. Execute query on actual database
    6. Generate grounded natural-language answer
    7. Recommend chart visualization
    8. Record execution in history
    """
    start_time = time.perf_counter()
    question = req.question.strip()
    
    # 1 & 2 & 3: Generate SQL via schema-first engine
    sql, provider_used, error = await generate_sql_for_question(
        question=question,
        provider=req.provider,
        api_key=req.api_key
    )

    if error:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        record_query_execution(
            question=question,
            sql="",
            status="error",
            duration_ms=duration_ms,
            row_count=0,
            provider=provider_used,
            error=error
        )
        return {
            "status": "error",
            "question": question,
            "sql": "",
            "error": error,
            "provider": provider_used,
            "execution_time_ms": duration_ms
        }

    # 4: Validate SQL safety
    is_safe, safety_err = validate_safe_sql(sql)
    if not is_safe:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        record_query_execution(
            question=question,
            sql=sql,
            status="blocked",
            duration_ms=duration_ms,
            row_count=0,
            provider=provider_used,
            error=safety_err
        )
        return {
            "status": "blocked",
            "question": question,
            "sql": sql,
            "error": safety_err,
            "provider": provider_used,
            "execution_time_ms": duration_ms
        }

    # 5: Execute query on database
    try:
        columns, rows, exec_ms = execute_raw_sql(sql)
    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_msg = f"Database execution error: {str(e)}"
        record_query_execution(
            question=question,
            sql=sql,
            status="execution_error",
            duration_ms=duration_ms,
            row_count=0,
            provider=provider_used,
            error=err_msg
        )
        return {
            "status": "execution_error",
            "question": question,
            "sql": sql,
            "error": err_msg,
            "provider": provider_used,
            "execution_time_ms": duration_ms
        }

    total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 6: Generate natural-language answer
    nl_answer = generate_natural_language_answer(question, sql, columns, rows)

    # 7: Recommend chart
    chart_cfg = recommend_chart_config(columns, rows)

    # 8: Record query in history
    record_query_execution(
        question=question,
        sql=sql,
        status="success",
        duration_ms=total_duration_ms,
        row_count=len(rows),
        provider=provider_used
    )

    return {
        "status": "success",
        "question": question,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "execution_time_ms": total_duration_ms,
        "database_time_ms": exec_ms,
        "answer": nl_answer,
        "chart": chart_cfg,
        "provider": provider_used
    }

# ----------------- Manual SQL Execution -----------------

@app.post("/api/execute-sql")
def execute_manual_sql(req: ExecuteSqlRequest):
    """
    Execute user-provided SQL query safely.
    Validates read-only permissions, checks table references, executes query,
    and returns tabular results with chart recommendations.
    """
    start_time = time.perf_counter()
    raw_sql = req.sql.strip()

    # Safety validation
    is_safe, safety_err = validate_safe_sql(raw_sql)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=safety_err)

    # Schema reference validation
    schema_info = get_database_schema(use_cache=True)
    all_known_tables = set(t.lower() for t in schema_info.get("table_names", []))
    referenced_tables = extract_table_references(raw_sql)

    for ref_tbl in referenced_tables:
        if ref_tbl not in all_known_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table '{ref_tbl}' does not exist in active database schema."
            )

    safe_sql = enforce_query_limit(raw_sql)

    try:
        columns, rows, exec_ms = execute_raw_sql(safe_sql)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SQL execution failed: {str(e)}"
        )

    total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    nl_answer = generate_natural_language_answer("Manual Query", safe_sql, columns, rows)
    chart_cfg = recommend_chart_config(columns, rows)

    record_query_execution(
        question="Manual SQL Execution",
        sql=safe_sql,
        status="success",
        duration_ms=total_duration_ms,
        row_count=len(rows),
        provider="manual"
    )

    return {
        "status": "success",
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "execution_time_ms": total_duration_ms,
        "database_time_ms": exec_ms,
        "answer": nl_answer,
        "chart": chart_cfg
    }

# ----------------- Query History Endpoints -----------------

@app.get("/api/history")
def fetch_history(limit: int = Query(50, ge=1, le=100)):
    return {
        "status": "success",
        "history": get_query_history(limit=limit)
    }

@app.delete("/api/history")
def clear_history():
    clear_query_history()
    return {"status": "success", "message": "Query history cleared."}

# ----------------- RAG Document Intelligence Endpoints -----------------

@app.post("/api/rag/upload")
async def upload_rag_document(file: UploadFile = File(...)):
    """Upload document for independent RAG retrieval."""
    content = await file.read()
    try:
        text_content = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File decoding failed: {str(e)}")

    doc_id = f"doc_{file.filename.split('.')[0]}_{int(time.time())}"
    res = doc_store.add_document(doc_id, file.filename, text_content)
    return {
        "status": "success",
        "message": f"Document '{file.filename}' indexed for RAG retrieval.",
        "data": res
    }

@app.post("/api/rag/query")
def query_rag_documents(req: RagQueryRequest):
    """Retrieve grounded answers and citations from indexed documents."""
    result = doc_store.answer_query(req.query)
    return {
        "status": "success",
        "query": req.query,
        "answer": result["answer"],
        "citations": result["citations"],
        "retrieved_count": result["retrieved_count"]
    }

# ----------------- Database Seeding & Maintenance -----------------

@app.post("/api/db/seed")
def seed_database_endpoint(force: bool = True):
    """Seed or reseed the database with benchmark enterprise dataset."""
    result = seed_benchmark_data(force=force)
    invalidate_schema_cache()
    fresh_schema = get_database_schema(use_cache=False)
    return {
        "status": "success",
        "seed_info": result,
        "active_tables": fresh_schema.get("table_names", [])
    }
