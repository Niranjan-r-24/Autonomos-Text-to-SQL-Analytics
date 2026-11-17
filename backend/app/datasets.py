"""
Persistent datasets catalog module.
Maintains the canonical `datasets` table in the shared database across all routes and serverless invocations.
Schema: dataset_id, table_name, source_file_name, columns_json, row_count, created_at.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from backend.app.db import engine

logger = logging.getLogger("text2sql.datasets")

def init_datasets_table():
    """Ensure the canonical `datasets` metadata table exists in the shared database."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS "datasets" (
        dataset_id VARCHAR(100) PRIMARY KEY,
        table_name VARCHAR(100) NOT NULL UNIQUE,
        source_file_name VARCHAR(255) NOT NULL,
        columns_json TEXT NOT NULL,
        row_count INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(create_sql))
    except Exception as e:
        logger.error("Failed to initialize datasets table: %s", str(e))

def save_dataset_metadata(
    dataset_id: str,
    table_name: str,
    source_file_name: str,
    columns: List[Dict[str, Any]],
    row_count: int
) -> Dict[str, Any]:
    """
    Persist dataset metadata into the shared `datasets` table.
    Overwrites previous record if the table is being replaced.
    """
    init_datasets_table()
    cols_json = json.dumps(columns)

    with engine.begin() as conn:
        # Delete existing metadata for this table_name if replacing
        conn.execute(
            text('DELETE FROM "datasets" WHERE LOWER("table_name") = LOWER(:tbl)'),
            {"tbl": table_name}
        )
        # Insert canonical record
        conn.execute(
            text("""
            INSERT INTO "datasets" (dataset_id, table_name, source_file_name, columns_json, row_count)
            VALUES (:did, :tbl, :src, :cols, :cnt)
            """),
            {
                "did": dataset_id,
                "tbl": table_name,
                "src": source_file_name,
                "cols": cols_json,
                "cnt": row_count
            }
        )

    return {
        "dataset_id": dataset_id,
        "datasetId": dataset_id,
        "table_name": table_name,
        "tableName": table_name,
        "source_file_name": source_file_name,
        "columns_json": cols_json,
        "columns": columns,
        "row_count": row_count
    }

def list_datasets() -> List[Dict[str, Any]]:
    """
    Retrieve all registered datasets from the persistent `datasets` table.
    """
    init_datasets_table()
    datasets = []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text('SELECT dataset_id, table_name, source_file_name, columns_json, row_count, created_at FROM "datasets" ORDER BY created_at DESC')
            ).fetchall()
            for r in rows:
                try:
                    cols = json.loads(r[3]) if r[3] else []
                except Exception:
                    cols = []
                datasets.append({
                    "dataset_id": str(r[0]),
                    "datasetId": str(r[0]),
                    "table_name": str(r[1]),
                    "tableName": str(r[1]),
                    "source_file_name": str(r[2]),
                    "columns_json": str(r[3]),
                    "columns": cols,
                    "row_count": int(r[4]),
                    "created_at": str(r[5]) if r[5] else None
                })
    except Exception as e:
        logger.warning("Could not list datasets: %s", str(e))

    return datasets

def find_dataset_by_name(table_name: str) -> Optional[Dict[str, Any]]:
    """
    Lookup a dataset by table name (case-insensitive) in the persistent `datasets` table.
    """
    init_datasets_table()
    clean_name = table_name.lower().strip()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text('SELECT dataset_id, table_name, source_file_name, columns_json, row_count, created_at FROM "datasets" WHERE LOWER("table_name") = :tbl LIMIT 1'),
                {"tbl": clean_name}
            ).fetchone()
            if row:
                try:
                    cols = json.loads(row[3]) if row[3] else []
                except Exception:
                    cols = []
                return {
                    "dataset_id": str(row[0]),
                    "datasetId": str(row[0]),
                    "table_name": str(row[1]),
                    "tableName": str(row[1]),
                    "source_file_name": str(row[2]),
                    "columns_json": str(row[3]),
                    "columns": cols,
                    "row_count": int(row[4]),
                    "created_at": str(row[5]) if row[5] else None
                }
    except Exception as e:
        logger.warning("find_dataset_by_name error: %s", str(e))
    return None

def find_dataset_by_id(dataset_id: str) -> Optional[Dict[str, Any]]:
    """
    Lookup a dataset by dataset_id in the persistent `datasets` table.
    """
    init_datasets_table()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text('SELECT dataset_id, table_name, source_file_name, columns_json, row_count, created_at FROM "datasets" WHERE "dataset_id" = :did LIMIT 1'),
                {"did": dataset_id}
            ).fetchone()
            if row:
                try:
                    cols = json.loads(row[3]) if row[3] else []
                except Exception:
                    cols = []
                return {
                    "dataset_id": str(row[0]),
                    "datasetId": str(row[0]),
                    "table_name": str(row[1]),
                    "tableName": str(row[1]),
                    "source_file_name": str(row[2]),
                    "columns_json": str(row[3]),
                    "columns": cols,
                    "row_count": int(row[4]),
                    "created_at": str(row[5]) if row[5] else None
                }
    except Exception as e:
        logger.warning("find_dataset_by_id error: %s", str(e))
    return None
