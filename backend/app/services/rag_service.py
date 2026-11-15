"""
Production RAG (Retrieval-Augmented Generation) Service.
Provides enterprise document upload, text extraction (PDF, TXT, MD, JSON, CSV),
recursive chunking, hybrid vector/lexical BM25 retrieval, and cited grounded answers.
"""
from __future__ import annotations

import os
import re
import json
import hashlib
import logging
from io import BytesIO
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("text2sql.rag")

BASE_DIR = Path(__file__).resolve().parents[2]
RAG_DIR = Path(os.getenv("RAG_STORAGE_DIR", BASE_DIR / "rag_store"))
RAG_DIR.mkdir(parents=True, exist_ok=True)


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

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns metadata for all indexed documents."""
        doc_map: Dict[str, int] = {}
        for r in self.records:
            src = r.get("source", "unknown")
            doc_map[src] = doc_map.get(src, 0) + 1
        return [{"filename": src, "chunks": count} for src, count in doc_map.items()]

    @staticmethod
    def recursive_chunks(text: str, size: int = 800, overlap: int = 150) -> List[str]:
        """Splits raw text into cohesive overlapping chunks respecting sentence boundaries."""
        clean_text = re.sub(r"\s+", " ", text).strip()
        chunks: List[str] = []
        cursor = 0
        while cursor < len(clean_text):
            end = min(cursor + size, len(clean_text))
            if end < len(clean_text):
                for marker in (". ", "? ", "! ", "\n", "; ", " "):
                    split = clean_text.rfind(marker, cursor + size // 2, end)
                    if split != -1:
                        end = split + len(marker)
                        break
            chunk = clean_text[cursor:end].strip()
            if chunk:
                chunks.append(chunk)
            cursor = max(end - overlap, cursor + 1)
        return chunks

    def ingest(self, filename: str, content: bytes) -> Dict[str, Any]:
        """
        Extracts, chunks, indexes, and persists a document into the RAG knowledge store.
        """
        text = self._extract_text(filename, content)
        if not text.strip():
            raise ValueError(f"No readable text could be extracted from '{filename}'.")

        doc_hash = hashlib.sha1((filename + str(len(content))).encode()).hexdigest()[:12]
        chunks = self.recursive_chunks(text)
        new_records = [
            {"id": f"{doc_hash}-{i}", "text": chunk, "source": filename, "chunk": i + 1}
            for i, chunk in enumerate(chunks)
        ]

        # Avoid duplicate ingestion of identical files
        existing_ids = {r["id"] for r in self.records}
        unique_records = [r for r in new_records if r["id"] not in existing_ids]

        if unique_records:
            self.records.extend(unique_records)
            records_file = RAG_DIR / "records.json"
            records_file.write_text(json.dumps(self.records, indent=2), encoding="utf-8")

            chroma = self.chroma_collection
            if chroma is not None:
                try:
                    chroma.upsert(
                        ids=[r["id"] for r in unique_records],
                        documents=[r["text"] for r in unique_records],
                        metadatas=[{"source": r["source"], "chunk": r["chunk"]} for r in unique_records]
                    )
                except Exception as e:
                    logger.warning("Chroma upsert notice: %s", e)

        logger.info("Ingested '%s': created %d chunks (%d new)", filename, len(chunks), len(unique_records))
        return {
            "document_id": doc_hash,
            "filename": filename,
            "chunks_created": len(chunks),
            "total_knowledge_chunks": len(self.records)
        }

    def answer(self, query: str, api_key: Optional[str] = None, provider: str = "gemini") -> Dict[str, Any]:
        """
        Performs hybrid retrieval and synthesizes a grounded answer with verified citations.
        """
        if not self.records:
            return {
                "answer": "The knowledge base is currently empty. Please upload documents (.pdf, .txt, .md) to enable RAG retrieval.",
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
        """Lightweight, zero-dependency BM25-style lexical ranking."""
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
        """Enriches conversational context if query is brief."""
        if not self.memory or len(query.split()) > 7:
            return query
        last_turn = self.memory[-1]["query"]
        return f"{query} (referencing: {last_turn})"

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
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
                    with httpx.Client(timeout=8) as client:
                        res = client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

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

        # Deterministic extraction fallback:
        # Extract leading sentences from the top 2 chunks
        primary = ranked_chunks[0]
        sentences = re.split(r"(?<=[.!?])\s+", primary["text"])
        summary = " ".join(sentences[:3]).strip()
        source_note = f" (Referencing: {primary['source']}, Chunk {primary['chunk']})"
        return f"Summary from Knowledge Base: {summary}{source_note}"

    @staticmethod
    def _extract_text(filename: str, content: bytes) -> str:
        """Extracts text from PDF, TXT, MD, JSON, or CSV formats."""
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(content))
                pages_text = [page.extract_text() or "" for page in reader.pages]
                return "\n\n".join(pages_text).strip()
            except Exception as e:
                raise ValueError(f"Could not parse PDF '{filename}': {str(e)}")
        elif ext in [".txt", ".md", ".json", ".csv", ".tsv"]:
            return content.decode("utf-8", errors="ignore")
        else:
            return content.decode("utf-8", errors="ignore")


# Global singleton instance
rag_service = ProductionRAGService()
