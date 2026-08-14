import io
import os
import re
import sys
import sqlite3
import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.db.database import get_db_schema_info, DB_PATH, BASE_DIR
from backend.app.db.seed import seed_database
from backend.app.agents.pipeline import TextToSqlPipeline
from backend.app.agents.rag import rag_service

app = FastAPI(
    title="Enterprise Autonomous Text-to-SQL Analytics API",
    version="1.0.0",
    description="Multi-Agent Text-to-SQL Pipeline with Self-Correction, Dynamic Visualization, DB Metadata, and Multi-Format File Upload"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database is seeded on startup if db file doesn't exist
@app.on_event("startup")
def startup_event():
    if not os.path.exists(DB_PATH):
        print("📁 Database file missing. Automatically seeding database...")
        seed_database()

class QueryRequest(BaseModel):
    query: str
    api_key: Optional[str] = None
    provider: Optional[str] = "gemini"

class KeyVerifyRequest(BaseModel):
    api_key: str
    provider: Optional[str] = "gemini"

@app.get("/api/health")
def health_check():
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    return {
        "status": "online",
        "database_connected": True,
        "database_path": DB_PATH,
        "llm_providers": {
            "gemini": bool(gemini_key),
            "openai": bool(openai_key),
            "fallback_engine": True
        }
    }

@app.get("/api/schema")
def get_schema():
    try:
        schema = get_db_schema_info()
        return {"success": True, "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/seed")
def trigger_seed():
    try:
        seed_database()
        return {"success": True, "message": "Database successfully re-seeded with fresh enterprise data."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verify-key")
def verify_api_key(req: KeyVerifyRequest):
    key = req.api_key.strip()
    provider = (req.provider or "gemini").lower()

    if not key and provider != "fallback":
        return {"valid": False, "message": "API key cannot be empty."}

    try:
        if "gemini" in provider:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
            payload = {"contents": [{"parts": [{"text": "Respond with OK."}]}]}
            with httpx.Client(timeout=8) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return {
                        "valid": True,
                        "message": "Gemini API key verified successfully! Connected to Gemini 1.5 Flash.",
                        "provider": "Gemini 1.5 Flash"
                    }
                else:
                    err_info = res.json().get("error", {})
                    err_msg = err_info.get("message", f"HTTP {res.status_code} response.")
                    return {"valid": False, "message": f"Gemini verification failed: {err_msg}"}
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
                    return {"valid": False, "message": f"OpenAI verification failed: {err_msg}"}
        else:
            return {
                "valid": True,
                "message": "Deterministic engine selected. High-precision rule-based SQL engine active (No LLM key required).",
                "provider": "Deterministic Engine"
            }
    except Exception as e:
        return {"valid": False, "message": f"API key verification network error: {str(e)}"}

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    base_name = os.path.splitext(filename)[0]
    clean_table_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name).strip('_').lower()
    if not clean_table_name or clean_table_name[0].isdigit():
        clean_table_name = f"dataset_{clean_table_name}"

    contents = await file.read()

    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(contents))
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(contents))
        elif ext == ".json":
            df = pd.read_json(io.BytesIO(contents))
        elif ext in [".tsv", ".txt"]:
            try:
                df = pd.read_csv(io.BytesIO(contents), sep="\t")
            except Exception:
                df = pd.read_csv(io.BytesIO(contents))
        elif ext == ".parquet":
            df = pd.read_parquet(io.BytesIO(contents))
        elif ext in [".db", ".sqlite", ".sqlite3"]:
            temp_db_path = os.path.join(BASE_DIR, f"temp_{clean_table_name}.db")
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
                temp_df = pd.read_sql_query(f"SELECT * FROM `{t_name}`", src_conn)
                temp_df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', str(c).strip().lower()) for c in temp_df.columns]
                clean_t = re.sub(r'[^a-zA-Z0-9_]', '_', t_name).lower()
                temp_df.to_sql(clean_t, dest_conn, if_exists="replace", index=False)
                imported_tables.append(clean_t)

            src_conn.close()
            dest_conn.close()
            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)

            return {
                "success": True,
                "message": f"Successfully imported SQLite database with tables: {', '.join(imported_tables)}.",
                "table_name": imported_tables[0] if imported_tables else clean_table_name,
                "tables_imported": imported_tables,
                "schema": get_db_schema_info()
            }
        elif ext == ".sql":
            sql_text = contents.decode("utf-8", errors="ignore")
            dest_conn = sqlite3.connect(DB_PATH)
            dest_conn.executescript(sql_text)
            dest_conn.commit()
            dest_conn.close()
            return {
                "success": True,
                "message": f"Successfully executed SQL script '{filename}'.",
                "table_name": "uploaded_sql_script",
                "schema": get_db_schema_info()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Supported formats: .csv, .xlsx, .xls, .json, .tsv, .txt, .db, .sqlite, .sql, .parquet"
            )

        # Clean columns and store in SQLite
        df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', str(c).strip().lower()) for c in df.columns]

        dest_conn = sqlite3.connect(DB_PATH)
        df.to_sql(clean_table_name, dest_conn, if_exists="replace", index=False)
        dest_conn.close()

        updated_schema = get_db_schema_info()

        return {
            "success": True,
            "message": f"Successfully created database table '{clean_table_name}' with {len(df)} rows and {len(df.columns)} columns.",
            "table_name": clean_table_name,
            "row_count": len(df),
            "columns": list(df.columns),
            "sample_rows": df.head(3).to_dict(orient="records"),
            "schema": updated_schema
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and import file: {str(e)}")

@app.post("/api/knowledge/upload")
async def upload_knowledge_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Knowledge base ingestion currently accepts PDF files.")
    try:
        return {"success": True, **rag_service.ingest(file.filename, await file.read())}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/query")
def execute_nl_query(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")

    try:
        pipeline = TextToSqlPipeline(api_key=req.api_key, provider=req.provider)
        result = pipeline.run_pipeline(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
