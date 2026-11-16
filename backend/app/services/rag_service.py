"""
Production RAG (Retrieval-Augmented Generation) Service.
Provides enterprise document upload, text extraction (PDF, DOCX, TXT, MD, JSON, CSV),
recursive chunking, hybrid vector/lexical BM25 retrieval, and cited grounded answers.
"""
from __future__ import annotations

import os
import re
import json
import hashlib
import datetime
import logging
from io import BytesIO
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("text2sql.rag")

RAG_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "how", "many",
    "much", "what", "which", "who", "whom", "this", "that", "these", "those", "can",
    "could", "will", "would", "shall", "should", "may", "might", "must"
}

BASE_DIR = Path(__file__).resolve().parents[2]
RAG_DIR = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "rag_store"))
RAG_DIR.mkdir(parents=True, exist_ok=True)

DOCS_DIR = RAG_DIR / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class ProductionRAGService:
    """Production RAG engine with hybrid search and resilient offline fallback."""

    def __init__(self):
        self.memory = deque(maxlen=10)
        self.records: List[Dict[str, Any]] = []
        self._chroma = None
        self._embedder = None

        # 1. Load persisted records from records.json
        records_path = RAG_DIR / "records.json"
        if records_path.exists():
            try:
                self.records = json.loads(records_path.read_text(encoding="utf-8"))
                logger.info("Loaded %d knowledge records from %s", len(self.records), records_path)
            except Exception as e:
                logger.warning("Failed to load records.json: %s", e)

    @property
    def chroma_collection(self):
        """Lazy loader for persistent Chroma vector store to avoid blocking application startup."""
        if self._chroma is None:
            try:
                import chromadb
                chroma_dir = RAG_DIR / "chroma"
                chroma_dir.mkdir(parents=True, exist_ok=True)
                self._chroma = chromadb.PersistentClient(path=str(chroma_dir)).get_or_create_collection("knowledge")
                stored = self._chroma.get(include=["documents", "metadatas"])
                if stored and stored.get("ids"):
                    loaded = [
                        {"id": i, "text": doc, "source": meta.get("source", "unknown"), "chunk": meta.get("chunk", 1)}
                        for i, doc, meta in zip(stored["ids"], stored["documents"], stored["metadatas"])
                    ]
                    if loaded and not self.records:
                        self.records = loaded
                        logger.info("Loaded %d records from Chroma collection", len(self.records))
            except Exception as e:
                logger.info("Chroma vector store running in offline/memory fallback mode: %s", e)
        return self._chroma

    @property
    def has_documents(self) -> bool:
        return len(self.records) > 0

    def _load_doc_metadata(self) -> Dict[str, Any]:
        """Loads document metadata cache from documents.json."""
        meta_path = RAG_DIR / "documents.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load documents.json: %s", e)
        return {}

    def _save_doc_metadata(self, metadata: Dict[str, Any]) -> None:
        """Persists document metadata cache to documents.json."""
        try:
            meta_path = RAG_DIR / "documents.json"
            meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save documents.json: %s", e)

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns metadata for all indexed documents and their availability."""
        docs_meta = self._load_doc_metadata()
        doc_chunk_map: Dict[str, int] = {}
        for r in self.records:
            src = r.get("source", "unknown")
            doc_chunk_map[src] = doc_chunk_map.get(src, 0) + 1

        result = []
        for filename, count in doc_chunk_map.items():
            meta = docs_meta.get(filename, {})
            file_path = DOCS_DIR / filename
            size = meta.get("size_bytes")
            if size is None and file_path.exists():
                size = file_path.stat().st_size

            result.append({
                "filename": filename,
                "chunks": count,
                "file_type": meta.get("file_type") or os.path.splitext(filename)[1].lower(),
                "size_bytes": size or 0,
                "indexed_at": meta.get("indexed_at") or "Persisted",
                "status": "ready" if count > 0 else "empty"
            })
        return result

    def delete_document(self, filename: str) -> bool:
        """Removes a document and its chunks from records, storage, and Chroma collection."""
        initial_len = len(self.records)
        self.records = [r for r in self.records if r.get("source") != filename]

        # Save updated records.json
        records_file = RAG_DIR / "records.json"
        records_file.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

        # Update metadata
        docs_meta = self._load_doc_metadata()
        if filename in docs_meta:
            del docs_meta[filename]
            self._save_doc_metadata(docs_meta)

        # Delete stored document file
        doc_path = DOCS_DIR / filename
        if doc_path.exists():
            try:
                doc_path.unlink()
            except Exception as e:
                logger.warning("Could not delete stored file %s: %s", filename, e)

        # Remove from Chroma
        chroma = self.chroma_collection
        if chroma is not None:
            try:
                chroma.delete(where={"source": filename})
            except Exception as e:
                logger.warning("Chroma deletion note: %s", e)

        return len(self.records) < initial_len

    @staticmethod
    def recursive_chunks(text: str, size: int = 800, overlap: int = 150) -> List[str]:
        """Splits raw text into cohesive overlapping chunks respecting sentence boundaries."""
        clean_text = text.replace("\r\n", "\n").replace("\r", "\n")
        clean_text = re.sub(r"[ \t]+", " ", clean_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()
        chunks: List[str] = []
        cursor = 0
        while cursor < len(clean_text):
            end = min(cursor + size, len(clean_text))
            if end < len(clean_text):
                for marker in ("\n\n", ". ", "? ", "! ", "\n", "; ", " "):
                    split = clean_text.rfind(marker, cursor + size // 2, end)
                    if split != -1:
                        end = split + len(marker)
                        break
            chunk = clean_text[cursor:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(clean_text):
                break
            cursor = max(end - overlap, cursor + 1)
        return chunks

    def ingest(self, filename: str, content: bytes) -> Dict[str, Any]:
        """
        Extracts, chunks, embeds, indexes, and stores a document (.pdf, .docx, .txt, .md).
        Raises ValueError if text extraction fails, ensuring no false success is reported.
        """
        if not content or len(content) == 0:
            raise ValueError(f"Uploaded file '{filename}' is empty (0 bytes).")

        text = self._extract_text(filename, content)
        if not text or not text.strip():
            raise ValueError(f"No readable text could be extracted from '{filename}'.")

        # Store physical document file in DOCS_DIR
        doc_path = DOCS_DIR / filename
        try:
            doc_path.write_bytes(content)
        except Exception as e:
            logger.warning("Could not persist file to disk %s: %s", filename, e)

        doc_hash = hashlib.sha1((filename + str(len(content))).encode()).hexdigest()[:12]
        chunks = self.recursive_chunks(text)
        if not chunks:
            raise ValueError(f"Document '{filename}' could not be split into meaningful text chunks.")

        new_records = [
            {"id": f"{doc_hash}-{i}", "text": chunk, "source": filename, "chunk": i + 1}
            for i, chunk in enumerate(chunks)
        ]

        # Purge any previous chunks for the same filename to handle updates cleanly
        self.records = [r for r in self.records if r.get("source") != filename]
        self.records.extend(new_records)

        # Persist updated records
        records_file = RAG_DIR / "records.json"
        records_file.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

        # Update Chroma vector index
        chroma = self.chroma_collection
        if chroma is not None:
            try:
                chroma.upsert(
                    ids=[r["id"] for r in new_records],
                    documents=[r["text"] for r in new_records],
                    metadatas=[{"source": r["source"], "chunk": r["chunk"]} for r in new_records]
                )
            except Exception as e:
                logger.warning("Chroma upsert notice: %s", e)

        # Update metadata catalog
        docs_meta = self._load_doc_metadata()
        docs_meta[filename] = {
            "filename": filename,
            "file_type": os.path.splitext(filename)[1].lower(),
            "size_bytes": len(content),
            "chunks_count": len(chunks),
            "indexed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "ready"
        }
        self._save_doc_metadata(docs_meta)

        logger.info("Successfully ingested '%s': created %d chunks", filename, len(chunks))
        return {
            "document_id": doc_hash,
            "filename": filename,
            "chunks_created": len(chunks),
            "total_knowledge_chunks": len(self.records),
            "status": "indexed",
            "message": f"Successfully indexed '{filename}' into document knowledge base ({len(chunks)} chunks created)."
        }

    def answer(self, query: str, api_key: Optional[str] = None, provider: str = "gemini") -> Dict[str, Any]:
        """
        Performs hybrid retrieval and synthesizes a grounded answer with verified citations.
        """
        if not self.records:
            return {
                "answer": "The knowledge base is currently empty. Please upload documents (.pdf, .docx, .txt, .md) to enable RAG retrieval.",
                "citations": [],
                "retrieved_count": 0,
                "rewritten_query": query
            }

        rewritten = self._rewrite(query)
        candidates = self._hybrid_search(rewritten)
        ranked = candidates[:5]

        citations = [
            {
                "source": r["source"],
                "chunk": r["chunk"],
                "score": round(float(r.get("score", 0.0)), 3),
                "excerpt": r["text"][:260] + ("..." if len(r["text"]) > 260 else "")
            }
            for r in ranked
        ]

        # Generate answer with citations
        answer_text = self._synthesize_answer(query, ranked, api_key=api_key, provider=provider)
        self.memory.append({"query": query, "answer": answer_text})

        return {
            "answer": answer_text,
            "rewritten_query": rewritten,
            "citations": citations,
            "retrieved_count": len(ranked)
        }

    def _hybrid_search(self, query: str) -> List[Dict[str, Any]]:
        """Combines BM25 lexical token matching with semantic vector scoring."""
        lexical = self._bm25_search(query, self.records)
        semantic: List[Dict[str, Any]] = []

        chroma = self.chroma_collection
        if chroma is not None:
            try:
                res = chroma.query(query_texts=[query], n_results=min(10, len(self.records)))
                if res and res.get("documents") and res["documents"][0]:
                    docs = res["documents"][0]
                    metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(docs)
                    dists = res["distances"][0] if res.get("distances") else [0.5] * len(docs)
                    for d, m, dist in zip(docs, metas, dists):
                        score = max(0.0, 1.0 - (dist if isinstance(dist, (int, float)) else 0.5))
                        semantic.append({
                            "text": d,
                            "source": m.get("source", "Document"),
                            "chunk": m.get("chunk", 1),
                            "score": score
                        })
            except Exception as e:
                logger.debug("Chroma semantic query fallback: %s", e)

        # Merge lexical and semantic
        merged: Dict[Tuple[str, int], Dict[str, Any]] = {}
        for r in lexical:
            key = (r["source"], r["chunk"])
            merged[key] = dict(r)

        for r in semantic:
            key = (r["source"], r["chunk"])
            if key in merged:
                merged[key]["score"] = merged[key].get("score", 0) + r["score"] * 1.5
            else:
                merged[key] = dict(r)

        sorted_results = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
        return sorted_results[:10]

    @staticmethod
    def _bm25_search(query: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Lightweight, stopword-filtered BM25-style lexical ranking."""
        terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2 and t.lower() not in RAG_STOPWORDS]
        if not terms:
            terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        if not terms:
            return records[:5]

        scored = []
        for r in records:
            text_lower = r["text"].lower()
            counts = Counter(re.findall(r"\w+", text_lower))
            doc_len = len(text_lower.split())
            k1 = 1.5
            b = 0.75
            avg_dl = 120.0

            score = 0.0
            for term in terms:
                f = counts.get(term, 0)
                if f > 0:
                    score += (f * (k1 + 1)) / (f + k1 * (1 - b + b * (doc_len / avg_dl)))
            if score > 0:
                scored.append({**r, "score": score})

        return sorted(scored, key=lambda x: x["score"], reverse=True)[:10]

    def _rewrite(self, query: str) -> str:
        """Enriches conversational context only if query is anaphoric and references past turn."""
        if not self.memory or len(query.split()) > 7:
            return query
        q_tokens = [w.lower() for w in re.findall(r"\w+", query)]
        anaphoric = {"it", "its", "they", "them", "their", "this", "that", "these", "those", "same"}
        if any(w in anaphoric for w in q_tokens):
            last_turn = self.memory[-1]["query"]
            return f"{query} (referencing: {last_turn})"
        return query

    def _synthesize_answer(
        self,
        query: str,
        ranked_chunks: List[Dict[str, Any]],
        api_key: Optional[str] = None,
        provider: str = "gemini"
    ) -> str:
        """Synthesizes an executive grounded answer from top ranked excerpts."""
        if not ranked_chunks:
            return "No matching document excerpts were found for your question."

        # If LLM API key is present, attempt generative answer
        if api_key and provider != "fallback":
            try:
                import httpx
                context_str = "\n\n".join(
                    [f"[Source: {c['source']}, Chunk {c['chunk']}]: {c['text']}" for c in ranked_chunks[:3]]
                )
                prompt = f"""You are an executive knowledge assistant. Answer the user question accurately and concisely using ONLY the provided document context. Cite sources where appropriate.

DOCUMENT CONTEXT:
{context_str}

USER QUESTION:
{query}

EXECUTIVE ANSWER:"""

                if "gemini" in provider.lower():
                    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"]
                    for m_name in models_to_try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
                        try:
                            with httpx.Client(timeout=15) as client:
                                res = client.post(url, json=payload)
                                if res.status_code == 200:
                                    data = res.json()
                                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                                elif res.status_code == 404:
                                    continue
                        except Exception:
                            continue

                elif "openai" in provider.lower():
                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                    with httpx.Client(timeout=8) as client:
                        res = client.post(url, headers=headers, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.warning("LLM RAG synthesis failed, using deterministic extractor: %s", e)

        # High-precision deterministic extraction:
        # Score individual sentences across top ranked chunks against query keywords
        terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2 and t.lower() not in RAG_STOPWORDS]
        if not terms:
            terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]

        scored_sentences = []
        for rc in ranked_chunks[:3]:
            chunk_text = rc["text"]
            s_list = [s.strip() for s in re.split(r"(?<=[.!?])\s+", chunk_text) if s.strip()]
            for s in s_list:
                s_lower = s.lower()
                match_count = sum(1 for t in terms if t in s_lower)
                phrase_boost = 3 if any(f"{terms[i]} {terms[i+1]}" in s_lower for i in range(len(terms)-1)) else 0
                total_s_score = match_count + phrase_boost
                if total_s_score > 0:
                    scored_sentences.append((total_s_score, s, rc["source"], rc["chunk"]))

        if scored_sentences:
            scored_sentences.sort(key=lambda x: x[0], reverse=True)
            top_score, top_s, best_src, best_chk = scored_sentences[0]
            selected = [top_s]
            for sc, s, src, chk in scored_sentences[1:]:
                if src == best_src and chk == best_chk and s not in selected and len(selected) < 2:
                    selected.append(s)
            answer_body = " ".join(selected)
            return f"According to {best_src} (Chunk {best_chk}): {answer_body}"
        else:
            primary = ranked_chunks[0]
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", primary["text"]) if s.strip()]
            summary = " ".join(sentences[:2]).strip()
            return f"According to {primary['source']} (Chunk {primary['chunk']}): {summary}"

    @staticmethod
    def _extract_text(filename: str, content: bytes) -> str:
        """Extracts text from PDF, DOCX, TXT, MD, JSON, or CSV formats."""
        if not content:
            raise ValueError(f"Uploaded file '{filename}' is empty (0 bytes).")

        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(content))
                if len(reader.pages) == 0:
                    raise ValueError(f"PDF '{filename}' contains 0 pages.")
                pages_text = [page.extract_text() or "" for page in reader.pages]
                full_text = "\n\n".join(pages_text).strip()
                if not full_text:
                    raise ValueError(f"No extractable text found in PDF '{filename}'.")
                return full_text
            except Exception as e:
                raise ValueError(f"Could not parse PDF '{filename}': {str(e)}")

        elif ext in [".docx", ".doc"]:
            try:
                import docx
                doc = docx.Document(BytesIO(content))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            paragraphs.append(row_text)
                full_text = "\n\n".join(paragraphs).strip()
                if not full_text:
                    raise ValueError(f"No extractable text found in Word document '{filename}'.")
                return full_text
            except Exception as e:
                raise ValueError(f"Could not parse DOCX '{filename}': {str(e)}")

        elif ext in [".txt", ".md", ".json", ".csv", ".tsv"]:
            # Try utf-8 first, fallback to utf-8-sig or latin-1
            for enc in ["utf-8", "utf-8-sig", "latin-1"]:
                try:
                    decoded = content.decode(enc).strip()
                    if decoded:
                        return decoded
                except UnicodeDecodeError:
                    continue
            raise ValueError(f"Could not decode text file '{filename}' with UTF-8 or Latin-1.")

        else:
            try:
                decoded = content.decode("utf-8", errors="ignore").strip()
                if decoded:
                    return decoded
                raise ValueError(f"Unsupported format '{ext}' for document parsing.")
            except Exception as e:
                raise ValueError(f"Unsupported document format '{ext}': {str(e)}")


# Global singleton instance
rag_service = ProductionRAGService()
