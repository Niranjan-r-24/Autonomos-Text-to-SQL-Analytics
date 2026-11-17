"""
Configuration module for Autonomos Text-to-SQL Analytics backend.
Supports shared persistent PostgreSQL (Vercel Postgres, Neon, Supabase, Render)
and persistent SQLite for local development.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

def get_database_url() -> str:
    # Priority list of production database URL environment variables
    candidate_urls = [
        os.getenv("DATABASE_URL"),
        os.getenv("POSTGRES_URL"),
        os.getenv("POSTGRES_PRISMA_URL"),
        os.getenv("POSTGRES_URL_NON_POOLING"),
        os.getenv("NEON_DATABASE_URL"),
        os.getenv("SUPABASE_DATABASE_URL"),
        os.getenv("TURSO_DATABASE_URL"),
    ]

    raw_url = next((u for u in candidate_urls if u and u.strip()), None)

    if not raw_url:
        # Default persistent database path
        default_db_file = BACKEND_DIR / "enterprise_analytics.db"
        raw_url = f"sqlite:///{default_db_file.as_posix()}"

    # Normalize PostgreSQL URL for SQLAlchemy
    # Vercel / Render / Supabase use postgres:// which SQLAlchemy 2.0 requires as postgresql://
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # SQLite relative path resolution
    if raw_url.startswith("sqlite:///") and not raw_url.startswith("sqlite:////"):
        rel_path = raw_url.replace("sqlite:///", "")
        if not os.path.isabs(rel_path):
            resolved_path = (PROJECT_ROOT / rel_path).resolve()
            if not resolved_path.parent.exists() and (BACKEND_DIR / rel_path).parent.exists():
                resolved_path = (BACKEND_DIR / rel_path).resolve()
            return f"sqlite:///{resolved_path.as_posix()}"

    return raw_url

DATABASE_URL = get_database_url()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "gemini" if GEMINI_API_KEY else ("openai" if OPENAI_API_KEY else "schema_fallback"))

MAX_QUERY_LIMIT = int(os.getenv("MAX_QUERY_LIMIT", "1000"))
DEFAULT_QUERY_LIMIT = int(os.getenv("DEFAULT_QUERY_LIMIT", "100"))
QUERY_TIMEOUT_SECONDS = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))
