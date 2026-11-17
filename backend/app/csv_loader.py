"""
Dataset & Document ingestion module.
Handles CSV, TSV, JSON, Excel, PDF, DOCX, TXT, and Markdown upload,
validation, schema inference, dynamic table creation, RAG indexing,
and permanent uploaded file catalog tracking.
"""
import io
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from sqlalchemy import text
from backend.app.db import engine
from backend.app.schema import invalidate_schema_cache
from backend.app.rag import doc_store

RESERVED_SQL_WORDS = {
    "select", "table", "from", "where", "order", "group", "by", "limit", "join",
    "user", "index", "primary", "foreign", "key", "check", "default", "null"
}

def sanitize_identifier(name: str, default_prefix: str = "col") -> str:
    """
    Sanitize a table or column name into a safe, valid SQL identifier.
    """
    cleaned = re.sub(r"[^\w\s]", "", name).strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"{default_prefix}_{cleaned}"
        
    if cleaned in RESERVED_SQL_WORDS:
        cleaned = f"{cleaned}_tbl" if default_prefix == "tbl" else f"{cleaned}_col"
        
    return cleaned

def infer_sql_type(series: pd.Series) -> str:
    """
    Infer SQLite/PostgreSQL compatible data type from pandas Series.
    """
    non_null = series.dropna()
    if non_null.empty:
        return "TEXT"

    # Numeric types
    if pd.api.types.is_integer_dtype(non_null):
        return "INTEGER"
    if pd.api.types.is_float_dtype(non_null):
        return "REAL"
    if pd.api.types.is_bool_dtype(non_null):
        return "INTEGER"

    # Datetime types
    try:
        sample = non_null.iloc[:100]
        pd.to_datetime(sample, format="%Y-%m-%d", errors="raise")
        return "DATE"
    except Exception:
        pass

    try:
        sample = non_null.iloc[:100]
        pd.to_datetime(sample, errors="raise")
        return "TIMESTAMP"
    except Exception:
        pass

    return "TEXT"

def init_uploaded_catalog():
    """Ensure the internal catalog table for uploaded files exists."""
    pk_col = "id INTEGER PRIMARY KEY" if engine.url.drivername.startswith("sqlite") else "id SERIAL PRIMARY KEY"
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS "_uploaded_files_catalog" (
        {pk_col},
        filename TEXT NOT NULL,
        table_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        row_count INTEGER NOT NULL DEFAULT 0,
        column_count INTEGER NOT NULL DEFAULT 0,
        columns_summary TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))

def record_uploaded_file(
    filename: str,
    table_name: str,
    file_type: str,
    row_count: int,
    column_count: int,
    columns_summary: str
):
    """Save metadata of uploaded dataset or document in catalog."""
    init_uploaded_catalog()
    with engine.begin() as conn:
        # Delete prior record for same table if replacing
        conn.execute(
            text('DELETE FROM "_uploaded_files_catalog" WHERE "table_name" = :t OR "filename" = :f'),
            {"t": table_name, "f": filename}
        )
        conn.execute(
            text("""
            INSERT INTO "_uploaded_files_catalog"
            (filename, table_name, file_type, row_count, column_count, columns_summary)
            VALUES (:filename, :table_name, :file_type, :row_count, :column_count, :columns_summary)
            """),
            {
                "filename": filename,
                "table_name": table_name,
                "file_type": file_type,
                "row_count": row_count,
                "column_count": column_count,
                "columns_summary": columns_summary
            }
        )

def get_uploaded_files_catalog() -> List[Dict[str, Any]]:
    """Retrieve all uploaded datasets and documents from catalog."""
    init_uploaded_catalog()
    results = []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text('SELECT id, filename, table_name, file_type, row_count, column_count, columns_summary, uploaded_at FROM "_uploaded_files_catalog" ORDER BY id DESC')
            ).fetchall()
            for r in rows:
                results.append({
                    "id": r[0],
                    "filename": r[1],
                    "table_name": r[2],
                    "file_type": r[3],
                    "row_count": r[4],
                    "column_count": r[5],
                    "columns_summary": r[6],
                    "uploaded_at": str(r[7]) if r[7] else None
                })
    except Exception:
        pass
    return results

def extract_text_from_file(file_bytes: bytes, filename: Optional[str] = None) -> str:
    """
    Extract readable text from documents (.docx, .pdf, .txt, .md, .json, etc.).
    """
    fname = (filename or "").lower()

    # 1. Word Document (.docx) via native standard library zip/xml parser
    if fname.endswith((".docx", ".doc")):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                xml_data = z.read("word/document.xml")
                tree = ET.fromstring(xml_data)
                paragraphs = []
                for p in tree.iter():
                    if p.tag.endswith("}p"):
                        p_text = "".join(t.text for t in p.iter() if t.tag.endswith("}t") and t.text)
                        if p_text.strip():
                            paragraphs.append(p_text.strip())
                if paragraphs:
                    return "\n\n".join(paragraphs)
        except Exception:
            pass

        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            if paragraphs:
                return "\n\n".join(paragraphs)
        except Exception:
            pass

    # 2. PDF Document (.pdf) via pypdf or stream extractor
    if fname.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [p.extract_text() or "" for p in reader.pages]
            full_pdf_text = "\n\n".join(t.strip() for t in pages if t.strip())
            if full_pdf_text.strip():
                return full_pdf_text
        except Exception:
            pass

        try:
            streams = re.findall(rb"\((.*?)\)Tj", file_bytes)
            if streams:
                return "\n".join(s.decode("latin1", errors="ignore") for s in streams if s)
        except Exception:
            pass

    # 3. Standard text decoding with multiple encodings
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            decoded = file_bytes.decode(enc)
            if decoded.strip():
                return decoded
        except Exception:
            continue

    return file_bytes.decode("utf-8", errors="replace")

def load_document_to_table(
    file_bytes: bytes,
    table_name: str,
    filename: str,
    replace_existing: bool = True
) -> Dict[str, Any]:
    """
    Convert a text document (PDF, DOCX, TXT, MD) into a structured SQL database table
    and simultaneously index it in RAG intelligence.
    """
    text_content = extract_text_from_file(file_bytes, filename)
    if not text_content.strip():
        raise ValueError(f"No extractable text content found in document '{filename}'.")

    # Split into sections or paragraphs
    raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text_content) if p.strip()]
    if not raw_paras:
        raw_paras = [text_content.strip()]

    sections = []
    for idx, para in enumerate(raw_paras, start=1):
        # Derive a short title from the first 50 chars of paragraph
        first_line = para.split("\n")[0].strip()
        title = first_line[:60] if len(first_line) > 5 else f"Section {idx}"
        sections.append({
            "section_number": idx,
            "title": title,
            "content": para,
            "word_count": len(para.split()),
            "file_name": filename
        })

    df = pd.DataFrame(sections)
    sanitized_table = sanitize_identifier(table_name, default_prefix="doc")

    # Table schema definition
    pk_def = "_row_id INTEGER PRIMARY KEY" if engine.url.drivername.startswith("sqlite") else "_row_id SERIAL PRIMARY KEY"
    create_sql = f"""
    CREATE TABLE "{sanitized_table}" (
        {pk_def},
        "section_number" INTEGER,
        "title" TEXT,
        "content" TEXT,
        "word_count" INTEGER,
        "file_name" TEXT
    );
    """

    with engine.begin() as conn:
        if replace_existing:
            cascade = " CASCADE" if not engine.url.drivername.startswith("sqlite") else ""
            conn.execute(text(f'DROP TABLE IF EXISTS "{sanitized_table}"{cascade};'))
        conn.execute(text(create_sql))

    # Insert data
    df.to_sql(
        name=sanitized_table,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=500
    )

    # Index into RAG Document Intelligence
    doc_id = f"doc_{sanitized_table}_{int(time.time())}"
    rag_res = doc_store.add_document(doc_id, filename, text_content)

    # Record in catalog
    col_summary = "section_number, title, content, word_count, file_name"
    record_uploaded_file(
        filename=filename,
        table_name=sanitized_table,
        file_type="document",
        row_count=len(df),
        column_count=5,
        columns_summary=col_summary
    )

    # Invalidate schema cache so schema inspector catches table immediately
    invalidate_schema_cache()

    col_info = [
        {"name": "section_number", "type": "INTEGER"},
        {"name": "title", "type": "TEXT"},
        {"name": "content", "type": "TEXT"},
        {"name": "word_count", "type": "INTEGER"},
        {"name": "file_name", "type": "TEXT"}
    ]

    return {
        "status": "success",
        "file_type": "document",
        "table_name": sanitized_table,
        "row_count": len(df),
        "columns": col_info,
        "rag_chunks": rag_res.get("total_chunks", 0),
        "filename": filename
    }

def parse_bytes_to_dataframe(file_bytes: bytes, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Robust multi-format dataset parser for tabular datasets.
    Supports CSV, TSV, JSON, Excel (.xlsx, .xls), and delimited text.
    """
    fname = (filename or "").lower()

    # 1. Excel files
    if fname.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))

    # 2. JSON files
    if fname.endswith(".json") or file_bytes.strip().startswith((b"[", b"{")):
        try:
            return pd.read_json(io.BytesIO(file_bytes))
        except Exception:
            try:
                import json
                data = json.loads(file_bytes.decode("utf-8", errors="replace"))
                if isinstance(data, list):
                    return pd.json_normalize(data)
                elif isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            return pd.json_normalize(v)
                    return pd.json_normalize([data])
            except Exception:
                pass

    # 3. Delimited text (CSV, TSV, semicolon, pipe)
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        for sep in [None, ",", "\t", ";", "|"]:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, engine="python", encoding=encoding)
                if not df.empty and len(df.columns) > 1:
                    return df
            except Exception:
                continue

    raise ValueError("File is not a tabular delimited dataset.")

def load_csv_to_table(
    file_bytes: bytes,
    table_name: str,
    filename: Optional[str] = None,
    replace_existing: bool = True
) -> Dict[str, Any]:
    """
    Universal file ingestion handler:
    - Tabular files (CSV, TSV, Excel, JSON) -> Typed tabular SQL table.
    - Document files (PDF, DOCX, TXT, MD) -> Structured document SQL table + RAG indexing.
    Always records in _uploaded_files_catalog and invalidates schema cache.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    fname = (filename or "dataset.csv").lower()
    base_name = filename.rsplit(".", 1)[0] if filename and "." in filename else (table_name or "dataset")
    target_table = table_name or base_name

    # Check if document format
    if fname.endswith((".pdf", ".docx", ".doc", ".md", ".txt")):
        # Check if it might be a CSV disguised as TXT
        is_tabular = False
        try:
            df = parse_bytes_to_dataframe(file_bytes, filename=filename)
            if len(df.columns) > 1 and len(df) > 0:
                is_tabular = True
        except Exception:
            is_tabular = False

        if not is_tabular or fname.endswith((".pdf", ".docx", ".doc")):
            return load_document_to_table(
                file_bytes=file_bytes,
                table_name=target_table,
                filename=filename or "document.txt",
                replace_existing=replace_existing
            )

    # Parse tabular dataset
    try:
        df = parse_bytes_to_dataframe(file_bytes, filename=filename)
    except Exception:
        # Fallback to document table
        return load_document_to_table(
            file_bytes=file_bytes,
            table_name=target_table,
            filename=filename or "document.txt",
            replace_existing=replace_existing
        )

    if df.empty or len(df.columns) == 0:
        raise ValueError("Uploaded dataset contains no valid rows or columns.")

    sanitized_table = sanitize_identifier(target_table, default_prefix="ds")

    # Sanitize column names
    seen_cols = set()
    col_mapping = {}
    col_types = []

    for orig_col in df.columns:
        s_col = sanitize_identifier(str(orig_col), default_prefix="c")
        base_col = s_col
        counter = 1
        while s_col in seen_cols:
            s_col = f"{base_col}_{counter}"
            counter += 1
        seen_cols.add(s_col)
        col_mapping[orig_col] = s_col

        sql_type = infer_sql_type(df[orig_col])
        col_types.append((s_col, sql_type))

    df_renamed = df.rename(columns=col_mapping)

    # Primary key and table definition
    pk_def = "_row_id INTEGER PRIMARY KEY" if engine.url.drivername.startswith("sqlite") else "_row_id SERIAL PRIMARY KEY"
    cols_def = [f'"{col}" {stype}' for col, stype in col_types]
    create_sql = f'CREATE TABLE "{sanitized_table}" (\n  {pk_def},\n  ' + ",\n  ".join(cols_def) + "\n);"

    with engine.begin() as conn:
        if replace_existing:
            cascade = " CASCADE" if not engine.url.drivername.startswith("sqlite") else ""
            conn.execute(text(f'DROP TABLE IF EXISTS "{sanitized_table}"{cascade};'))
        conn.execute(text(create_sql))

    # Write data
    df_renamed.to_sql(
        name=sanitized_table,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000
    )

    # Record in uploaded files catalog
    col_summary = ", ".join(c[0] for c in col_types[:8])
    record_uploaded_file(
        filename=filename or f"{sanitized_table}.csv",
        table_name=sanitized_table,
        file_type="dataset",
        row_count=len(df),
        column_count=len(col_types),
        columns_summary=col_summary
    )

    # Invalidate schema cache
    invalidate_schema_cache()

    return {
        "status": "success",
        "file_type": "dataset",
        "table_name": sanitized_table,
        "row_count": len(df),
        "columns": [{"name": c[0], "type": c[1]} for c in col_types],
        "filename": filename or f"{sanitized_table}.csv"
    }
