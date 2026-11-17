"""
Configuration module for Autonomos Text-to-SQL Analytics backend.
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

raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'enterprise_analytics.db'}")
if raw_db_url.startswith("sqlite:///") and not raw_db_url.startswith("sqlite:////"):
    rel_path = raw_db_url.replace("sqlite:///", "")
    if not os.path.isabs(rel_path):
        resolved_path = (PROJECT_ROOT / rel_path).resolve()
        if not resolved_path.parent.exists() and (BACKEND_DIR / rel_path).parent.exists():
            resolved_path = (BACKEND_DIR / rel_path).resolve()
        DATABASE_URL = f"sqlite:///{resolved_path.as_posix()}"
    else:
        DATABASE_URL = raw_db_url
else:
    DATABASE_URL = raw_db_url
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "gemini" if GEMINI_API_KEY else ("openai" if OPENAI_API_KEY else "schema_fallback"))

MAX_QUERY_LIMIT = int(os.getenv("MAX_QUERY_LIMIT", "1000"))
DEFAULT_QUERY_LIMIT = int(os.getenv("DEFAULT_QUERY_LIMIT", "100"))
QUERY_TIMEOUT_SECONDS = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))
