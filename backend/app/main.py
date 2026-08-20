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
    from backend.app.db.database import DB_PATH, DATA_DIR, engine
    from backend.app.db.seed import seed_database
    from backend.app.services.schema_service import get_db_schema_info
    from backend.app.services.sql_executor import execute_safe_query
    from backend.app.services.pipeline import TextToSqlPipeline
except ImportError:
    from app.db.database import DB_PATH, DATA_DIR, engine
    from app.db.seed import seed_database
    from app.services.schema_service import get_db_schema_info
    from app.services.sql_executor import execute_safe_query
    from app.services.pipeline import TextToSqlPipeline

app = FastAPI(
    title="Text-to-SQL Analytics API",
    version="2.0.0",
    description="Clean, secure, and beginner-friendly Text-to-SQL Analytics backend."
)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-seed database if it doesn't exist
@app.on_event("startup")
def startup_event():
    if not os.path.exists(DB_PATH):
        logger.info("Database file not found at %s. Seeding sample database...", DB_PATH)
        seed_database()
    else:
        logger.info("Connected to database at %s", DB_PATH)


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


class ExecuteSqlRequest(BaseModel):
    sql: str = Field(..., description="Raw SQL query to execute safely")


class KeyVerifyRequest(BaseModel):
    api_key: str = Field(..., description="API key to verify")
    provider: Optional[str] = Field("gemini", description="LLM provider: gemini or openai")


@app.get("/api/health")
def health_check():
    """Health check endpoint returning connection status and active configuration."""
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    openai_key_set = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "database_connected": True,
        "database_path": DB_PATH,
        "providers": {
            "gemini": gemini_key_set,
            "openai": openai_key_set,
            "deterministic_engine": True
        }
    }


@app.get("/api/schema")
def get_schema():
    """Returns structured schema definitions (tables, columns, types, sample data) for all database tables."""
    try:
        schema = get_db_schema_info()
        return {"success": True, "schema": schema}
    except Exception as e:
        logger.error("Failed to retrieve schema: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
def trigger_seed():
    """Re-seeds the database with standard enterprise sample tables."""
    try:
        seed_database()
        schema = get_db_schema_info()
        return {
            "success": True,
            "message": "Database successfully re-seeded with fresh sample data.",
            "schema": schema
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
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
            with httpx.Client(timeout=8) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return {
                        "valid": True,
                        "message": "Gemini API key verified successfully! Connected to Gemini 1.5 Flash.",
                        "provider": "Google Gemini 1.5 Flash"
                    }
                else:
                    err_info = res.json().get("error", {})
                    err_msg = err_info.get("message", f"HTTP {res.status_code} response.")
                    return {"valid": False, "message": f"Gemini key verification failed: {err_msg}"}
                    
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

    try:
        pipeline = TextToSqlPipeline(api_key=req.api_key, provider=req.provider)
        result = pipeline.run(req.query.strip())
        return result
    except Exception as e:
        logger.error("Pipeline execution error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/api/execute-sql")
def execute_custom_sql(req: ExecuteSqlRequest):
    """
    Allows safe direct execution of a user-edited SQL query.
    Enforces read-only SELECT security checks.
    """
    if not req.sql.strip():
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")

    result = execute_safe_query(req.sql.strip())
    return result


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
    base_name = os.path.splitext(filename)[0]
    
    # Generate clean SQL-compliant table name
    clean_table_name = re.sub(r"[^a-zA-Z0-9_]", "_", base_name).strip("_").lower()
    if not clean_table_name or clean_table_name[0].isdigit():
        clean_table_name = f"dataset_{clean_table_name}"

    contents = await file.read()

    try:
        # 1. SQLite Database (.db, .sqlite, .sqlite3)
        if ext in [".db", ".sqlite", ".sqlite3"]:
            temp_db_path = os.path.join(DATA_DIR, f"temp_{clean_table_name}.db")
            with open(temp_db_path, "wb") as f:
                f.write(contents)

            src_conn = sqlite3.connect(temp_db_path)
            dest_conn = sqlite3.connect(DB_PATH)

            cursor = src_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = cursor.fetchall()

            imported_tables = []
            for t in tables:
                t_name = t[0]
                temp_df = pd.read_sql_query(f'SELECT * FROM "{t_name}"', src_conn)
                temp_df.columns = [re.sub(r"[^a-zA-Z0-9_]", "_", str(c).strip().lower()) for c in temp_df.columns]
                clean_t = re.sub(r"[^a-zA-Z0-9_]", "_", t_name).lower()
                temp_df.to_sql(clean_t, dest_conn, if_exists="replace", index=False)
                imported_tables.append(clean_t)

            src_conn.close()
            dest_conn.close()
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

            updated_schema = get_db_schema_info()
            primary_table = imported_tables[0] if imported_tables else clean_table_name
            return {
                "success": True,
                "message": f"Successfully imported SQLite database with table(s): {', '.join(imported_tables)}.",
                "table_name": primary_table,
                "tables_imported": imported_tables,
                "schema": updated_schema
            }

        # 2. SQL Dump Script (.sql)
        elif ext == ".sql":
            sql_text = contents.decode("utf-8", errors="ignore")
            dest_conn = sqlite3.connect(DB_PATH)
            dest_conn.executescript(sql_text)
            dest_conn.commit()
            dest_conn.close()

            updated_schema = get_db_schema_info()
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
            try:
                df = pd.read_csv(io.BytesIO(contents), sep="\t")
                if len(df.columns) <= 1:
                    df = pd.read_csv(io.BytesIO(contents), sep=None, engine="python")
            except Exception:
                df = pd.read_csv(io.BytesIO(contents))

        # 7. Apache Parquet (.parquet)
        elif ext == ".parquet":
            df = pd.read_parquet(io.BytesIO(contents))

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Supported formats: .csv, .xlsx, .xls, .json, .db, .sqlite, .sql, .txt, .tsv, .parquet"
            )

        # Standardize column names
        df.columns = [re.sub(r"[^a-zA-Z0-9_]", "_", str(c).strip().lower()) for c in df.columns]

        # Save to SQLite via SQLAlchemy engine
        with engine.begin() as conn:
            df.to_sql(clean_table_name, conn, if_exists="replace", index=False)

        updated_schema = get_db_schema_info()
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/")
def root():
    return {
        "status": "running",
        "message": "Autonomous Text-to-SQL Analytics API is live"
    }