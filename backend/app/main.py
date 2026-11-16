"""
Enterprise Text-to-SQL Analytics API.
FastAPI application exposing endpoints for natural language querying, safe SQL execution,
database schema inspection, LLM configuration, and multi-format dataset uploads (.CSV, .XLSX, .XLS, .JSON, .DB, .SQLITE, .SQL, .TXT, .TSV, .PARQUET).
"""
import io
import os
import re
import sys
import json
import sqlite3
import logging
import httpx
import pandas as pd
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("text2sql.api")

# Add project root and backend dir to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))
except ImportError:
    pass

from sqlalchemy import text

try:
    from backend.app.db.database import DB_PATH, DATA_DIR, engine
    from backend.app.db.seed import seed_database
    from backend.app.services.schema_service import get_db_schema_info, clear_schema_cache
    from backend.app.services.sql_executor import execute_safe_query
    from backend.app.services.pipeline import TextToSqlPipeline
    from backend.app.services.insights_service import BusinessInsightsInterpreter
    from backend.app.services.rag_service import rag_service
except ImportError:
    from app.db.database import DB_PATH, DATA_DIR, engine
    from app.db.seed import seed_database
    from app.services.schema_service import get_db_schema_info, clear_schema_cache
    from app.services.sql_executor import execute_safe_query
    from app.services.pipeline import TextToSqlPipeline
    from app.services.insights_service import BusinessInsightsInterpreter
    from app.services.rag_service import rag_service

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(DB_PATH):
        logger.info("Database file not found at %s. Seeding sample database...", DB_PATH)
        seed_database()
    else:
        logger.info("Connected to database at %s", DB_PATH)
    yield

app = FastAPI(
    title="Text-to-SQL Analytics API",
    version="2.0.0",
    description="Clean, secure, and beginner-friendly Text-to-SQL Analytics backend.",
    lifespan=lifespan
)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint for status check."""
    return {
        "status": "online",
        "service": "Autonomos Text-to-SQL Analytics API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/health")
def health():
    """Alias for health check."""
    return health_check()


class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question to translate into SQL")
    api_key: Optional[str] = Field(None, description="Optional LLM API Key (Gemini or OpenAI)")
    provider: Optional[str] = Field("gemini", description="LLM provider: gemini, openai, or fallback")
    active_table: Optional[str] = Field(None, description="Optional active table name to prioritize")


class ExecuteSqlRequest(BaseModel):
    sql: str = Field(..., description="Raw SQL query to execute safely")
    question: Optional[str] = Field("Custom SQL Execution", description="Optional natural language question or description")
    api_key: Optional[str] = Field(None, description="Optional LLM API Key")
    provider: Optional[str] = Field("gemini", description="LLM provider: gemini, openai, or fallback")



class KeyVerifyRequest(BaseModel):
    api_key: str = Field(..., description="API key to verify")
    provider: Optional[str] = Field("gemini", description="LLM provider: gemini or openai")


class RagQueryRequest(BaseModel):
    query: str = Field(..., description="Document or knowledge question")
    api_key: Optional[str] = Field(None, description="Optional LLM API Key")
    provider: Optional[str] = Field("gemini", description="LLM provider: gemini, openai, or fallback")


@app.get("/api/health")
def health_check():
    """Health check endpoint returning connection status and active configuration."""
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    openai_key_set = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "database_connected": True,
        "database_path": DB_PATH,
        "dialect": engine.dialect.name,
        "providers": {
            "gemini": gemini_key_set,
            "openai": openai_key_set,
            "deterministic_engine": True
        },
        "rag_store": {
            "indexed_documents": len(rag_service.list_documents()),
            "total_chunks": len(rag_service.records),
            "status": "ready" if rag_service.has_documents else "empty"
        }
    }


@app.get("/api/schema")
def get_schema():
    """Returns structured schema definitions (tables, columns, types, sample data) for all database tables."""
    try:
        schema = get_db_schema_info()
        # Filter out internal audit_logs and sqlite system tables from API response
        clean_schema = {k: v for k, v in schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
        return {"success": True, "schema": clean_schema}
    except Exception as e:
        logger.error("Failed to retrieve schema: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
def trigger_seed():
    """Re-seeds the database with standard enterprise sample tables."""
    try:
        seed_database()
        clear_schema_cache()
        schema = get_db_schema_info(force_refresh=True)
        clean_schema = {k: v for k, v in schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
        return {
            "success": True,
            "message": "Database successfully re-seeded with fresh sample data.",
            "schema": clean_schema
        }
    except Exception as e:
        logger.error("Failed to re-seed database: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/verify-key")
def verify_api_key(req: KeyVerifyRequest):
    """Verifies that the provided Gemini or OpenAI API key is active and functional."""
    key = req.api_key.strip()
    provider = (req.provider or "gemini").lower()

    if not key and provider != "fallback":
        return {"valid": False, "message": "API key cannot be empty."}

    try:
        if "gemini" in provider:
            models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
            last_err = "Verification failed."
            for m_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={key}"
                payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
                try:
                    with httpx.Client(timeout=15) as client:
                        res = client.post(url, json=payload)
                        if res.status_code == 200:
                            return {
                                "valid": True,
                                "message": f"Gemini API key verified successfully! Connected to {m_name}.",
                                "provider": f"Google Gemini ({m_name})"
                            }
                        elif res.status_code == 404:
                            continue
                        else:
                            err_info = res.json().get("error", {})
                            last_err = err_info.get("message", f"HTTP {res.status_code}")
                            break
                except Exception as ex:
                    last_err = str(ex)
                    continue
            return {"valid": False, "message": f"Gemini key verification failed: {last_err}"}
                    
        elif "openai" in provider:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }
            with httpx.Client(timeout=8) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    return {
                        "valid": True,
                        "message": "OpenAI API key verified successfully! Connected to GPT-4o.",
                        "provider": "OpenAI GPT-4o"
                    }
                else:
                    err_info = res.json().get("error", {})
                    err_msg = err_info.get("message", f"HTTP {res.status_code} response.")
                    return {"valid": False, "message": f"OpenAI key verification failed: {err_msg}"}
        else:
            return {
                "valid": True,
                "message": "Deterministic offline engine active. No external API key required.",
                "provider": "Deterministic Engine"
            }
    except Exception as e:
        logger.error("API key verification network error: %s", str(e))
        return {"valid": False, "message": f"Verification network error: {str(e)}"}


@app.post("/api/query")
def process_nl_query(req: QueryRequest):
    """
    Main Text-to-SQL endpoint:
    Processes natural language question -> Generates SQL & explanation -> Executes safely -> Returns results.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")
    if re.search(r"\b(?:audit|audit_logs?|security\s+logs?)\b", req.query, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Audit logs are internal and are not available in the analytics application.")

    try:
        pipeline = TextToSqlPipeline(api_key=req.api_key, provider=req.provider)
        result = pipeline.run(req.query.strip(), active_table=req.active_table)
        return result
    except Exception as e:
        logger.error("Pipeline execution error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/execute-sql")
def execute_custom_sql(req: ExecuteSqlRequest):
    """
    Allows safe direct execution of a user-edited SQL query.
    Enforces read-only SELECT security checks and interprets results into business insights.
    """
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")
    if re.search(r"\b(?:audit_logs?|security_logs?)\b", req.sql, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Audit logs are internal and are not available in the analytics application.")

    result = execute_safe_query(req.sql.strip())
    if result.get("success"):
        pipeline = TextToSqlPipeline(api_key=req.api_key, provider=req.provider or "gemini")
        visualization = pipeline._infer_visualization(
            columns=result.get("columns", []),
            rows=result.get("rows", []),
            user_question=req.question or "Custom SQL Execution"
        )
        result["visualization"] = visualization

        interpreter = BusinessInsightsInterpreter(api_key=req.api_key, provider=req.provider or "gemini")
        insights = interpreter.interpret(
            question=req.question or "Custom SQL Execution",
            sql_query=req.sql.strip(),
            columns=result.get("columns", []),
            rows=result.get("rows", []),
            error=result.get("error")
        )
        result["insights"] = insights
    return result



def resolve_clean_table_name(filename: str) -> str:
    """
    Normalizes dataset filenames into clean, standard SQL table names.
    Automatically handles browser duplicate suffixes like (1), _1, copy, etc.,
    and maps only exact canonical sample-dataset names to standard relational
    tables. User-defined names such as ``customer_test`` are preserved.
    """
    base_name = os.path.splitext(filename)[0]
    raw = re.sub(r"[\s_\-\(\)]+\d+[\)\_]?$", "", base_name, flags=re.IGNORECASE).strip()
    raw = re.sub(r"[\s_\-]+copy\b", "", raw, flags=re.IGNORECASE).strip()
    raw_lower = raw.lower().replace("-", "_").replace(" ", "_")

    if raw_lower in ("customer", "customers"):
        return "customers"
    if raw_lower in ("product", "products"):
        return "products"
    if raw_lower in ("order_item", "order_items", "orderitem", "orderitems"):
        return "order_items"
    if raw_lower in ("order", "orders"):
        return "orders"
    if raw_lower in ("payment", "payments"):
        return "payments"
    if raw_lower in ("ticket", "tickets", "support_ticket", "support_tickets"):
        return "support_tickets"
    if raw_lower in ("employee", "employees"):
        return "employees"
    if raw_lower in ("sale", "sales"):
        return "sales"

    clean = re.sub(r"[^a-zA-Z0-9_]", "_", raw).strip("_").lower()
    if not clean or clean[0].isdigit():
        clean = f"dataset_{clean}"
    return clean


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Uploads custom datasets in all major formats:
    - .CSV (Comma Separated)
    - .XLSX / .XLS (Excel Workbooks)
    - .JSON (JSON Records or Key-Value)
    - .DB / .SQLITE / .SQLITE3 (SQLite Database file with multiple tables)
    - .SQL (SQL DDL/DML script)
    - .TXT / .TSV (Tab or Delimited text)
    - .PARQUET (Apache Parquet)
    
    Automatically imports the table(s) into SQLite and updates the schema for instant querying.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    clean_table_name = resolve_clean_table_name(filename)

    contents = await file.read()

    try:
        # 1. SQLite Database (.db, .sqlite, .sqlite3)
        if ext in [".db", ".sqlite", ".sqlite3"]:
            temp_db_path = os.path.join(DATA_DIR, f"temp_{clean_table_name}.db")
            with open(temp_db_path, "wb") as f:
                f.write(contents)

            src_conn = sqlite3.connect(temp_db_path)
            cursor = src_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = cursor.fetchall()

            imported_tables = []
            for t in tables:
                t_name = t[0]
                temp_df = pd.read_sql_query(f'SELECT * FROM "{t_name}"', src_conn)
                temp_df.columns = [re.sub(r"[^a-zA-Z0-9_]", "_", str(c).strip().lower()) for c in temp_df.columns]
                clean_t = re.sub(r"[^a-zA-Z0-9_]", "_", t_name).lower()
                with engine.begin() as conn:
                    temp_df.to_sql(clean_t, conn, if_exists="replace", index=False)
                imported_tables.append(clean_t)

            src_conn.close()
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

            clear_schema_cache()
            raw_schema = get_db_schema_info(force_refresh=True)
            updated_schema = {k: v for k, v in raw_schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
            primary_table = imported_tables[0] if imported_tables else clean_table_name
            return {
                "success": True,
                "message": f"Successfully imported database with table(s): {', '.join(imported_tables)}.",
                "table_name": primary_table,
                "tables_imported": imported_tables,
                "schema": updated_schema
            }

        # 2. SQL Dump Script (.sql)
        elif ext == ".sql":
            sql_text = contents.decode("utf-8", errors="ignore")
            if engine.dialect.name == "sqlite":
                dest_conn = sqlite3.connect(DB_PATH)
                dest_conn.executescript(sql_text)
                dest_conn.commit()
                dest_conn.close()
            else:
                with engine.begin() as conn:
                    for stmt in sql_text.split(";"):
                        if stmt.strip():
                            conn.execute(text(stmt.strip()))

            clear_schema_cache()
            raw_schema = get_db_schema_info(force_refresh=True)
            updated_schema = {k: v for k, v in raw_schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
            return {
                "success": True,
                "message": f"Successfully executed SQL script '{filename}'.",
                "table_name": clean_table_name,
                "schema": updated_schema
            }

        # 3. CSV (.csv)
        elif ext == ".csv":
            df = pd.read_csv(io.BytesIO(contents))

        # 4. Excel (.xlsx, .xls)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(contents))

        # 5. JSON (.json)
        elif ext == ".json":
            try:
                df = pd.read_json(io.BytesIO(contents))
            except Exception:
                data = json.loads(contents.decode("utf-8", errors="ignore"))
                if isinstance(data, list):
                    df = pd.json_normalize(data)
                elif isinstance(data, dict):
                    list_keys = [k for k, v in data.items() if isinstance(v, list)]
                    if list_keys:
                        df = pd.json_normalize(data[list_keys[0]])
                    else:
                        df = pd.json_normalize([data])
                else:
                    raise ValueError("JSON format could not be normalized into tabular rows.")

        # 6. Tab-Separated / Text (.tsv, .txt)
        elif ext in [".tsv", ".txt"]:
            # Differentiate between structured tabular data (TSV/CSV) and prose text documents
            is_tabular = False
            try:
                sample_text = contents[:4096].decode("utf-8", errors="ignore")
                lines = [l for l in sample_text.splitlines() if l.strip()]
                if len(lines) >= 2:
                    for delim in ["\t", ",", "|", ";"]:
                        c1 = len(lines[0].split(delim))
                        c2 = len(lines[1].split(delim))
                        if c1 > 1 and c1 == c2:
                            is_tabular = True
                            break
            except Exception:
                is_tabular = False

            if is_tabular or ext == ".tsv":
                try:
                    df = pd.read_csv(io.BytesIO(contents), sep="\t" if ext == ".tsv" else None, engine="python")
                except Exception:
                    df = pd.read_csv(io.BytesIO(contents))
            else:
                # Ingest unstructured text document into RAG knowledge store
                rag_info = rag_service.ingest(filename, contents)
                raw_schema = get_db_schema_info(force_refresh=True)
                clean_s = {k: v for k, v in raw_schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
                return {
                    "success": True,
                    "message": f"Successfully indexed '{filename}' into document knowledge base ({rag_info['chunks_created']} chunks created).",
                    "table_name": "knowledge_base",
                    "type": "document",
                    "rag_info": rag_info,
                    "documents": rag_service.list_documents(),
                    "schema": clean_s
                }

        # 7. Apache Parquet (.parquet)
        elif ext == ".parquet":
            df = pd.read_parquet(io.BytesIO(contents))

        # 8. Document Knowledge Base (.pdf, .docx, .doc, .md) for RAG
        elif ext in [".pdf", ".docx", ".doc", ".md"]:
            rag_info = rag_service.ingest(filename, contents)
            raw_schema = get_db_schema_info(force_refresh=True)
            clean_s = {k: v for k, v in raw_schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
            return {
                "success": True,
                "message": f"Successfully indexed '{filename}' into document knowledge base ({rag_info['chunks_created']} chunks created).",
                "table_name": "knowledge_base",
                "type": "document",
                "rag_info": rag_info,
                "documents": rag_service.list_documents(),
                "schema": clean_s
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Supported formats: .csv, .xlsx, .xls, .json, .db, .sqlite, .sql, .txt, .tsv, .parquet, .pdf, .docx, .md"
            )

        # Standardize column names (handle numeric-only headers and SQL identifier safety)
        if all(str(c).strip().isdigit() for c in df.columns):
            if "ticket" in clean_table_name:
                default_ticket_cols = ["ticket_id", "customer_id", "order_id", "issue", "priority", "status", "created_at"]
                if len(df.columns) == len(default_ticket_cols):
                    df.columns = default_ticket_cols
                else:
                    df.columns = [f"col_{c}" for c in df.columns]
            else:
                df.columns = [f"col_{c}" for c in df.columns]
        else:
            cleaned_cols = []
            for c in df.columns:
                c_str = re.sub(r"[^a-zA-Z0-9_]", "_", str(c).strip().lower()).strip("_")
                if not c_str or c_str[0].isdigit():
                    c_str = f"col_{c_str}"
                cleaned_cols.append(c_str)
            df.columns = cleaned_cols

        # Save to database engine via SQLAlchemy engine
        with engine.begin() as conn:
            df.to_sql(clean_table_name, conn, if_exists="replace", index=False)

        clear_schema_cache()
        raw_schema = get_db_schema_info(force_refresh=True)
        updated_schema = {k: v for k, v in raw_schema.items() if k.lower() not in ("audit_logs", "sqlite_sequence")}
        logger.info("Imported table '%s' with %d rows and %d columns", clean_table_name, len(df), len(df.columns))

        return {
            "success": True,
            "message": f"Successfully created database table '{clean_table_name}' with {len(df)} rows and {len(df.columns)} columns.",
            "table_name": clean_table_name,
            "row_count": len(df),
            "columns": list(df.columns),
            "schema": updated_schema
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Dataset upload failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process and import file: {str(e)}")


@app.post("/api/rag/upload")
async def upload_rag_document(file: UploadFile = File(...)):
    """Uploads document (.pdf, .docx, .doc, .txt, .md) and chunks/indexes it into the RAG knowledge store."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".pdf", ".docx", ".doc", ".txt", ".md", ".json", ".csv", ".tsv"]
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document format '{ext}'. Supported formats: .pdf, .docx, .txt, .md"
        )

    contents = await file.read()
    if not contents or len(contents) == 0:
        raise HTTPException(status_code=400, detail=f"File '{file.filename}' is empty (0 bytes).")

    try:
        res = rag_service.ingest(file.filename, contents)
        return {
            "success": True,
            **res,
            "documents": rag_service.list_documents()
        }
    except ValueError as ve:
        logger.error("RAG document processing error for '%s': %s", file.filename, str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("RAG document upload failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to process and index document: {str(e)}")


@app.post("/api/rag/query")
def query_rag_knowledge(req: RagQueryRequest):
    """Queries the document knowledge base using hybrid retrieval and returns answer with citations."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        res = rag_service.answer(req.query.strip(), api_key=req.api_key, provider=req.provider or "gemini")
        return {"success": True, "query": req.query, **res}
    except Exception as e:
        logger.error("RAG query failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@app.get("/api/rag/documents")
def list_rag_documents():
    """Lists indexed documents and chunk statistics."""
    try:
        docs = rag_service.list_documents()
        return {
            "success": True,
            "document_count": len(docs),
            "total_chunks": len(rag_service.records),
            "documents": docs
        }
    except Exception as e:
        logger.error("Failed to list RAG documents: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/documents/{filename:path}")
def delete_rag_document(filename: str):
    """Deletes an indexed document from RAG knowledge store."""
    try:
        deleted = rag_service.delete_document(filename)
        return {
            "success": deleted,
            "message": f"Document '{filename}' {'deleted' if deleted else 'not found'}.",
            "documents": rag_service.list_documents()
        }
    except Exception as e:
        logger.error("Failed to delete document '%s': %s", filename, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
