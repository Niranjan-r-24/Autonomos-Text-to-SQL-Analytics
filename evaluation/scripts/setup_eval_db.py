"""
Setup Isolated Evaluation Database.
Copies the canonical enterprise database to an isolated location for evaluation runs,
ensuring zero mutations to production data and 100% reproducible execution results.
"""
import os
import shutil
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE_DB = os.path.join(BASE_DIR, "backend", "enterprise_analytics.db")
TARGET_DB = os.path.join(BASE_DIR, "evaluation", "data", "eval_enterprise.db")

def setup_evaluation_db():
    os.makedirs(os.path.dirname(TARGET_DB), exist_ok=True)
    if os.path.exists(SOURCE_DB):
        shutil.copy2(SOURCE_DB, TARGET_DB)
        print(f"[SETUP] Copied production database from '{SOURCE_DB}' to '{TARGET_DB}'.")
    else:
        raise FileNotFoundError(f"Source database not found at {SOURCE_DB}")

    # Verify tables
    conn = sqlite3.connect(TARGET_DB)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall()]
    print(f"[SETUP] Verified tables in evaluation database ({len(tables)} tables): {tables}")
    
    table_counts = {}
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        table_counts[t] = cur.fetchone()[0]
    print(f"[SETUP] Table row counts: {table_counts}")
    conn.close()
    return TARGET_DB

if __name__ == "__main__":
    setup_evaluation_db()
