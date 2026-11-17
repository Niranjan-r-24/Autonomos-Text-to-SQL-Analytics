"""
Query history and execution audit tracking module.
"""
import time
from typing import List, Dict, Any

_history_log: List[Dict[str, Any]] = []

def record_query_execution(
    question: str,
    sql: str,
    status: str,
    duration_ms: float,
    row_count: int,
    provider: str,
    error: str = None
) -> Dict[str, Any]:
    """Record a query execution entry."""
    entry = {
        "id": len(_history_log) + 1,
        "question": question,
        "sql": sql,
        "status": status,
        "duration_ms": duration_ms,
        "row_count": row_count,
        "provider": provider,
        "error": error,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # Keep latest 100 queries
    _history_log.insert(0, entry)
    if len(_history_log) > 100:
        _history_log.pop()
    return entry

def get_query_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recorded query history."""
    return _history_log[:limit]

def clear_query_history():
    """Clear query history."""
    _history_log.clear()
