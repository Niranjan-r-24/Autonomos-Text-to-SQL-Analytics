"""
Autonomos Text-to-SQL Analytics Platform - FastAPI Main API
Provides REST endpoints for natural-language queries, manual SQL execution,
dynamic CSV dataset ingestion, schema introspection, RAG intelligence, and history.
"""
import re
import time
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, status, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.config import DEFAULT_PROVIDER
from backend.app.db import engine, execute_raw_sql
from backend.app.seed import seed_benchmark_data
from backend.app.schema import get_database_schema, invalidate_schema_cache
from backend.app.sql_safety import validate_safe_sql, enforce_query_limit, extract_table_references
from backend.app.csv_loader import load_csv_to_table, load_document_to_table
from backend.app.datasets import list_datasets, find_dataset_by_name, find_dataset_by_id
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msgs = [
        f"{e.get('msg', 'Invalid input')} for field '{'.'.join(str(l) for l in e.get('loc', []))}'"
        for e in errors
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "detail": "; ".join(error_msgs)}
    )

# ----------------- Request / Response Models -----------------

class QueryRequest(BaseModel):
    question: Optional[str] = Field(None, description="Natural language question to query.")
    query: Optional[str] = Field(None, description="Alias for question.")
    table_name: Optional[str] = Field(None, alias="tableName", description="Target dataset table name.")
    dataset_id: Optional[str] = Field(None, alias="datasetId", description="Target dataset ID.")
    provider: Optional[str] = Field(None, description="AI provider ('gemini', 'openai', or empty for default).")
    api_key: Optional[str] = Field(None, description="Optional custom API key.")

    class Config:
        populate_by_name = True

    def get_question(self) -> str:
        q = (self.question or self.query or "").strip()
        if not q:
            raise ValueError("Field required: 'question' or 'query' must be provided.")
        return q

class ExecuteSqlRequest(BaseModel):
    sql: Optional[str] = Field(None, description="Raw SQL query to execute safely.")
    query: Optional[str] = Field(None, description="Alias for sql.")

    def get_sql(self) -> str:
        s = (self.sql or self.query or "").strip()
        if not s:
            raise ValueError("Field required: 'sql' must be provided.")
        return s

class RagQueryRequest(BaseModel):
    query: Optional[str] = Field(None, description="Natural language question for document intelligence.")
    question: Optional[str] = Field(None, description="Alias for query.")

    def get_query(self) -> str:
        q = (self.query or self.question or "").strip()
        if not q:
            raise ValueError("Field required: 'query' or 'question' must be provided.")
        return q

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
            "datasets": "/api/datasets",
            "query": "/api/query",
            "execute_sql": "/api/execute-sql",
            "upload_csv": "/api/upload-csv",
            "history": "/api/history",
            "rag_query": "/api/rag/query",
            "rag_upload": "/api/rag/upload",
            "seed": "/api/db/seed"
        }
    }

# ----------------- Schema & Datasets Inspection Endpoints -----------------

@app.get("/api/datasets")
def get_datasets_endpoint(response: Response):
    """Retrieve all persistent registered datasets."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return {
        "status": "success",
        "datasets": list_datasets()
    }

@app.get("/api/schema")
def get_schema(response: Response, refresh: bool = False):
    """Inspect active database tables, columns, data types, sample values, row counts, and persistent datasets."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    if refresh:
        invalidate_schema_cache()
    schema = get_database_schema(use_cache=not refresh)

    # Format indexed documents from doc_store
    indexed_docs = [
        {"doc_id": doc_id, "filename": info.get("filename", "document"), "length": info.get("length", 0)}
        for doc_id, info in doc_store.documents.items()
    ]

    return {
        "status": "success",
        "tables": schema.get("tables", {}),
        "table_names": schema.get("table_names", []),
        "relationships": schema.get("relationships", []),
        "uploaded_files": schema.get("uploaded_files", []),
        "datasets": schema.get("datasets", list_datasets()),
        "indexed_documents": indexed_docs
    }

# ----------------- CSV Upload & Dataset Management -----------------

@app.post("/api/upload")
@app.post("/api/upload-csv")
async def upload_csv(
    response: Response,
    file: UploadFile = File(...),
    table_name: Optional[str] = Form(None)
):
    """
    Universal dataset and document ingestion endpoint.
    - If tabular (CSV, TSV, JSON, Excel): creates typed SQL table and commits canonical `datasets` metadata.
    - If document (PDF, DOCX, TXT, MD): creates document SQL table and indexes for RAG.
    Returns canonical datasetId and tableName.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    filename = file.filename or "uploaded_file"
    content = await file.read()
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    target_table = table_name or base_name

    try:
        res = load_csv_to_table(content, target_table, filename=filename, replace_existing=True)
        invalidate_schema_cache()
        fresh_schema = get_database_schema(use_cache=False)
        return {
            "status": "success",
            "type": res.get("file_type", "dataset"),
            "message": f"File '{filename}' ingested and table '{res['table_name']}' created successfully.",
            "dataset": res,
            "datasetId": res.get("dataset_id"),
            "dataset_id": res.get("dataset_id"),
            "tableName": res["table_name"],
            "table_name": res["table_name"],
            "row_count": res["row_count"],
            "columns": res["columns"],
            "active_tables": fresh_schema.get("table_names", []),
            "datasets": list_datasets(),
            "schema": fresh_schema
        }
    except Exception as parse_err:
        logger.error("File ingestion error for '%s': %s", filename, str(parse_err))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to ingest file '{filename}': {str(parse_err)}"
        )

# ----------------- Text-to-SQL Analytics Pipeline -----------------

@app.post("/api/query")
async def process_natural_language_query(req: QueryRequest):
    """
    End-to-end schema-first Text-to-SQL analytics pipeline.
    Resolves canonical table from persistent datasets metadata.
    Rejects unknown/missing requested tables with 422.
    Never falls back to unrelated tables like audit_logs.
    """
    start_time = time.perf_counter()
    try:
        question = req.get_question()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Resolve target table from datasetId / tableName if provided
    target_table = (req.table_name or "").strip()
    if req.dataset_id and not target_table:
        ds = find_dataset_by_id(req.dataset_id)
        if ds:
            target_table = ds["table_name"]
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dataset table with id '{req.dataset_id}' is unavailable; no query executed."
            )

    current_schema = get_database_schema(use_cache=True)
    known_tables = set(t.lower() for t in current_schema.get("table_names", []))
    for ds in list_datasets():
        known_tables.add(ds["table_name"].lower())

    # If target_table was explicitly passed, validate that it exists
    if target_table:
        clean_target = target_table.lower()
        ds_match = find_dataset_by_name(clean_target)
        if ds_match:
            target_table = ds_match["table_name"]
        elif clean_target in known_tables:
            target_table = clean_target
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dataset table {target_table} is unavailable; no query executed."
            )
    else:
        # Check if question explicitly mentions a registered dataset
        for ds in list_datasets():
            tbl = ds["table_name"]
            if re.search(rf"\b{re.escape(tbl)}\b", question, re.IGNORECASE):
                target_table = tbl
                break

    # Self-heal benchmark schema if audit_logs is asked for but missing
    if is_audit_query(question):
        if "audit_logs" not in known_tables:
            seed_benchmark_data(force=False)
            invalidate_schema_cache()
            current_schema = get_database_schema(use_cache=False)
            known_tables = set(t.lower() for t in current_schema.get("table_names", []))

    # Direct safe SQL execution shortcut if input is already a raw SELECT/WITH query
    trimmed = question.strip().rstrip(";")
    if re.match(r"^(SELECT|WITH)\b", trimmed, re.IGNORECASE):
        is_safe, safety_err = validate_safe_sql(trimmed)
        if is_safe:
            ref_tables = extract_table_references(trimmed)
            if "audit_logs" in ref_tables and "audit_logs" not in known_tables and is_audit_query(question):
                seed_benchmark_data(force=False)
                invalidate_schema_cache()
                current_schema = get_database_schema(use_cache=False)
                known_tables = set(t.lower() for t in current_schema.get("table_names", []))

            if ref_tables and all(t.lower() in known_tables for t in ref_tables):
                safe_sql = enforce_query_limit(trimmed)
                try:
                    columns, rows, exec_ms = execute_raw_sql(safe_sql)
                    total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    nl_answer = generate_natural_language_answer("Direct SQL Query", safe_sql, columns, rows)
                    chart_cfg = recommend_chart_config(columns, rows, question=question, sql=safe_sql)
                    record_query_execution(
                        question=question,
                        sql=safe_sql,
                        status="success",
                        duration_ms=total_duration_ms,
                        row_count=len(rows),
                        provider="direct_sql"
                    )
                    return {
                        "status": "success",
                        "question": question,
                        "sql": safe_sql,
                        "columns": columns,
                        "rows": rows,
                        "row_count": len(rows),
                        "execution_time_ms": total_duration_ms,
                        "database_time_ms": exec_ms,
                        "answer": nl_answer,
                        "chart": chart_cfg,
                        "provider": "direct_sql"
                    }
                except Exception as e:
                    logger.warning("Direct SQL shortcut failed, falling back to Text2SQL: %s", str(e))
    
    # 1 & 2 & 3: Generate SQL via schema-first engine
    sql, provider_used, error = await generate_sql_for_question(
        question=question,
        provider=req.provider,
        api_key=req.api_key,
        target_table=target_table
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
        if (req.table_name or req.dataset_id) and "is unavailable" in error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error
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
    chart_cfg = recommend_chart_config(columns, rows, question=question, sql=sql)

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
    try:
        raw_sql = req.get_sql()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Safety validation
    is_safe, safety_err = validate_safe_sql(raw_sql)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=safety_err)

    # Schema reference validation with cache refreshing and self-healing
    schema_info = get_database_schema(use_cache=True)
    all_known_tables = set(t.lower() for t in schema_info.get("table_names", []))
    referenced_tables = extract_table_references(raw_sql)

    for ref_tbl in referenced_tables:
        if ref_tbl not in all_known_tables:
            # Refresh schema cache
            schema_info = get_database_schema(use_cache=False)
            all_known_tables = set(t.lower() for t in schema_info.get("table_names", []))
            if ref_tbl == "audit_logs" and "audit_logs" not in all_known_tables:
                seed_benchmark_data(force=False)
                invalidate_schema_cache()
                schema_info = get_database_schema(use_cache=False)
                all_known_tables = set(t.lower() for t in schema_info.get("table_names", []))

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
    chart_cfg = recommend_chart_config(columns, rows, question="Manual SQL Execution", sql=safe_sql)

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
        "question": "Manual SQL Execution",
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
@app.post("/api/upload-document")
async def upload_rag_document(
    response: Response,
    file: UploadFile = File(...)
):
    """
    Upload and index document for semantic RAG retrieval and schema tracking.
    Maintains strict independence from SQL query generation while reflecting in schema explorer.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    filename = file.filename or "document.txt"
    content = await file.read()
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

    try:
        from backend.app.csv_loader import extract_text_from_file, record_uploaded_file
        text_content = extract_text_from_file(content, filename)
        doc_id = f"doc_{base_name}_{int(time.time())}"
        rag_res = doc_store.add_document(doc_id, filename, text_content)

        # Record in uploaded files catalog as document
        try:
            record_uploaded_file(
                filename=filename,
                table_name=f"doc_{base_name}",
                file_type="document",
                row_count=rag_res.get("total_chunks", 1),
                column_count=1,
                columns_summary="text passages"
            )
        except Exception:
            pass

        invalidate_schema_cache()
        fresh_schema = get_database_schema(use_cache=False)

        return {
            "status": "success",
            "message": f"Document '{filename}' indexed for RAG retrieval ({rag_res.get('total_chunks', 1)} passages).",
            "data": rag_res,
            "filename": filename,
            "schema": fresh_schema
        }
    except Exception as e:
        logger.error("Document indexing error for '%s': %s", filename, str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process and index document '{filename}': {str(e)}"
        )

@app.post("/api/rag/query")
def query_rag_documents(req: RagQueryRequest):
    """Retrieve grounded answers and citations from indexed documents."""
    try:
        query_text = req.get_query()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    result = doc_store.answer_query(query_text)
    return {
        "status": "success",
        "query": query_text,
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
