"""
Comprehensive Test Suite for Document Upload Functionality (PDF, DOCX, TXT)
and Dynamic Natural Language Answers in Text-to-SQL Analytics.
"""
import io
import docx
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.rag_service import rag_service
from backend.app.services.pipeline import TextToSqlPipeline

client = TestClient(app)


def make_simple_pdf(text_str: str) -> bytes:
    """Creates a minimal valid PDF byte string with embedded text for testing."""
    stream_content = f"BT /F1 12 Tf 50 500 Td ({text_str}) Tj ET"
    stream_bytes = stream_content.encode("latin1")
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n"
        + stream_bytes + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000370 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n449\n%%EOF"
    )


class TestDocumentUploadAndRAG:
    """Tests storing, processing, chunking, embedding, indexing, and citations for PDF, DOCX, and TXT files."""

    def test_txt_document_upload_and_indexing(self):
        """Verifies TXT document upload via API, text extraction, chunking, and indexing."""
        content = b"Cybersecurity Directive 2026: Mandatory multi-factor authentication for all cloud infrastructure."
        res = client.post(
            "/api/rag/upload",
            files={"file": ("cyber_directive.txt", content, "text/plain")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["filename"] == "cyber_directive.txt"
        assert data["chunks_created"] >= 1
        assert "documents" in data

    def test_docx_document_upload_and_indexing(self):
        """Verifies DOCX document upload, paragraph extraction, chunking, and persistence."""
        doc = docx.Document()
        doc.add_paragraph("Travel Reimbursement Policy: Daily meal allowance is capped at $75 per day.")
        doc.add_paragraph("All international travel requires prior authorization from the department director.")
        bio = io.BytesIO()
        doc.save(bio)
        docx_bytes = bio.getvalue()

        res = client.post(
            "/api/rag/upload",
            files={"file": ("travel_policy.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["filename"] == "travel_policy.docx"
        assert data["chunks_created"] >= 1

    def test_pdf_document_upload_and_indexing(self):
        """Verifies PDF document upload, page extraction, chunking, and persistence."""
        pdf_bytes = make_simple_pdf("Data Retention Policy: Customer audit logs must be retained for 7 years.")
        res = client.post(
            "/api/rag/upload",
            files={"file": ("retention_policy.pdf", pdf_bytes, "application/pdf")}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["filename"] == "retention_policy.pdf"
        assert data["chunks_created"] >= 1

    def test_empty_document_upload_fails_cleanly(self):
        """Verifies that an empty (0 bytes) document upload fails with 400 and NEVER displays success."""
        res = client.post(
            "/api/rag/upload",
            files={"file": ("empty_file.txt", b"", "text/plain")}
        )
        assert res.status_code == 400
        assert "empty" in res.json().get("detail", "").lower()

    def test_unsupported_document_format_fails(self):
        """Verifies that unsupported file formats return 400 error."""
        res = client.post(
            "/api/rag/upload",
            files={"file": ("script.exe", b"binary_data", "application/octet-stream")}
        )
        assert res.status_code == 400

    def test_list_rag_documents_availability(self):
        """Verifies that GET /api/rag/documents accurately lists document availability."""
        res = client.get("/api/rag/documents")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "documents" in data
        assert data["document_count"] >= 1

        doc_names = [d["filename"] for d in data["documents"]]
        assert "travel_policy.docx" in doc_names
        assert "cyber_directive.txt" in doc_names

    def test_document_question_answering_and_citations(self):
        """Verifies asking questions based on uploaded documents returns answers with verified citations."""
        res = client.post(
            "/api/rag/query",
            json={"query": "What is the daily meal allowance in the travel policy?", "provider": "fallback"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "travel_policy.docx" in str(data) or "meal" in str(data["answer"]).lower()
        assert len(data["citations"]) > 0

        first_cite = data["citations"][0]
        assert "source" in first_cite
        assert "chunk" in first_cite
        assert "excerpt" in first_cite

    def test_pipeline_routes_document_questions_to_rag(self):
        """Verifies pipeline intent router forwards document questions to RAG with verified citations."""
        pipeline = TextToSqlPipeline(provider="fallback")
        result = pipeline.run("According to the travel policy, what is the daily allowance?")
        assert result["success"] is True
        assert result["route"] == "rag"
        assert result["insights"]["direct_answer"] is not None
        assert len(result["citations"]) > 0
        assert result["insights"]["status"] == "success"


class TestNaturalLanguageAnswersAndTableAccuracy:
    """Tests dynamic NL answers, eliminating default audit_logs, and querying uploaded CSVs."""

    def test_customer_count_never_queries_audit_logs(self):
        """Requirement 1 & 3: 'How many customers are in the database?' must query customers, NOT audit_logs."""
        pipeline = TextToSqlPipeline(provider="fallback")
        result = pipeline.run("How many customers are in the database?")

        assert result["success"] is True
        sql = result["sql"].lower()
        assert "customers" in sql
        assert "audit_logs" not in sql
        assert result["insights"]["direct_answer"] is not None
        assert "customers" in result["insights"]["direct_answer"].lower()
        assert "40" in result["insights"]["direct_answer"]

    def test_top_product_nl_answer(self):
        """Verifies dynamic NL answer identifies top performing product."""
        pipeline = TextToSqlPipeline(provider="fallback")
        result = pipeline.run("What is the top performing product by revenue?")

        assert result["success"] is True
        assert "audit_logs" not in result["sql"].lower()
        answer = result["insights"]["direct_answer"]
        assert answer is not None
        assert any(k in answer.lower() for k in ["top-performing", "highest", "apex cloud ai platform"])

    def test_upload_csv_and_query_dynamically(self):
        """Verifies uploading a custom CSV and querying it against the uploaded table."""
        csv_data = b"car_model,brand,price,mileage\nModel S,Tesla,79990,15000\nCivic,Honda,25000,45000\nMustang,Ford,55000,22000\nCorolla,Toyota,22000,60000\n"
        upload_res = client.post(
            "/api/upload",
            files={"file": ("fleet_inventory.csv", csv_data, "text/csv")}
        )
        assert upload_res.status_code == 200
        tbl = upload_res.json()["table_name"]
        assert tbl == "fleet_inventory"

        # Query custom uploaded table
        query_res = client.post(
            "/api/query",
            json={"query": "Show cars from fleet_inventory ordered by price descending", "active_table": tbl, "provider": "fallback"}
        )
        assert query_res.status_code == 200
        qdata = query_res.json()
        assert qdata["success"] is True
        assert "fleet_inventory" in qdata["sql"].lower()
        assert "audit_logs" not in qdata["sql"].lower()
        assert len(qdata["rows"]) == 4
        assert qdata["rows"][0]["car_model"] == "Model S"
        assert qdata["insights"]["direct_answer"] is not None

    def test_empty_results_handled_gracefully(self):
        """Verifies empty query results return status 'empty' without falling back to unrelated tables."""
        pipeline = TextToSqlPipeline(provider="fallback")
        result = pipeline.run("SELECT * FROM customers WHERE id = 999999;")

        assert result["success"] is True
        assert result["row_count"] == 0
        assert result["insights"]["status"] == "empty"
        assert "no matching records" in result["insights"]["direct_answer"].lower()
