import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.db.database import get_db_schema_info, DB_PATH
from backend.app.db.seed import seed_database
from backend.app.agents.pipeline import TextToSqlPipeline

app = FastAPI(
    title="Enterprise Autonomous Text-to-SQL Analytics API",
    version="1.0.0",
    description="Multi-Agent Text-to-SQL Pipeline with Self-Correction, Dynamic Visualization, and DB Metadata"
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
