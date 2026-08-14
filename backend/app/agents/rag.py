"""Production-oriented retrieval pipeline with safe local fallbacks.

The optional ML dependencies make it run with Chroma, sentence-transformers,
BM25 and a cross-encoder in production.  The lexical fallback keeps document
search usable during local setup or if an embedding model is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, List

RAG_DIR = Path(os.getenv("RAG_STORAGE_DIR", Path(__file__).resolve().parents[2] / "rag_store"))
RAG_DIR.mkdir(parents=True, exist_ok=True)


class ProductionRAG:
    def __init__(self):
        self.memory = deque(maxlen=12)
        self.records: List[Dict[str, Any]] = []
        self._chroma = None
        self._embedder = None
        self._reranker = None
        self._reranker_failed = False
        fallback = RAG_DIR / "records.json"
        if fallback.exists():
            try:
                self.records = json.loads(fallback.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        try:
            import chromadb
            self._chroma = chromadb.PersistentClient(path=str(RAG_DIR / "chroma")).get_or_create_collection("knowledge")
            stored = self._chroma.get(include=["documents", "metadatas"])
            self.records = [{"id": item_id, "text": text, "source": meta["source"], "chunk": meta["chunk"]} for item_id, text, meta in zip(stored["ids"], stored["documents"], stored["metadatas"])] or self.records
        except Exception:
            pass
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
        except Exception:
            pass

    @staticmethod
    def recursive_chunks(text: str, size: int = 900, overlap: int = 160) -> List[str]:
        text = re.sub(r"\s+", " ", text).strip()
        chunks, cursor = [], 0
        while cursor < len(text):
            end = min(cursor + size, len(text))
            if end < len(text):
                for marker in (". ", "? ", "! ", "; ", " "):
                    split = text.rfind(marker, cursor + size // 2, end)
                    if split != -1:
                        end = split + len(marker)
                        break
            chunk = text[cursor:end].strip()
            if chunk:
                chunks.append(chunk)
            cursor = max(end - overlap, cursor + 1)
        return chunks

    def ingest(self, filename: str, content: bytes) -> Dict[str, Any]:
        text = self._extract_text(filename, content)
        if not text.strip():
            raise ValueError("No readable text was found in this document.")
        doc_id = hashlib.sha1((filename + str(len(content))).encode()).hexdigest()[:12]
        chunks = self.recursive_chunks(text)
        records = [{"id": f"{doc_id}-{i}", "text": chunk, "source": filename, "chunk": i + 1} for i, chunk in enumerate(chunks)]
        self.records.extend(records)
        # A lightweight persisted fallback also supports environments without Chroma.
        (RAG_DIR / "records.json").write_text(json.dumps(self.records), encoding="utf-8")
        if self._chroma:
            embeddings = self._embedder.encode([r["text"] for r in records]).tolist() if self._embedder else None
            self._chroma.upsert(ids=[r["id"] for r in records], documents=[r["text"] for r in records], metadatas=[{"source": r["source"], "chunk": r["chunk"]} for r in records], embeddings=embeddings)
        return {"document_id": doc_id, "filename": filename, "chunks": len(chunks)}

    @property
    def has_documents(self) -> bool:
        return bool(self.records)

    def answer(self, query: str) -> Dict[str, Any]:
        rewritten = self._rewrite(query)
        candidates = self._hybrid_search(rewritten)
        ranked = self._rerank(rewritten, candidates)[:5]
        citations = [{"source": r["source"], "chunk": r["chunk"], "excerpt": r["text"][:240] + ("…" if len(r["text"]) > 240 else "")} for r in ranked]
        answer = self._summary(query, ranked)
        self.memory.append({"query": query, "answer": answer})
        return {"answer": answer, "rewritten_query": rewritten, "citations": citations, "retrieved_count": len(ranked)}

    def _hybrid_search(self, query: str) -> List[Dict[str, Any]]:
        lexical = self._bm25(query, self.records)
        semantic: List[Dict[str, Any]] = []
        if self._chroma and self._embedder:
            result = self._chroma.query(query_embeddings=[self._embedder.encode(query).tolist()], n_results=12, include=["documents", "metadatas", "distances"])
            for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
                semantic.append({"text": text, "source": meta["source"], "chunk": meta["chunk"], "score": 1 - distance})
        merged = {(r["source"], r["chunk"], r["text"]): dict(r) for r in lexical}
        for r in semantic:
            key = (r["source"], r["chunk"], r["text"])
            merged[key] = {**merged.get(key, r), "score": merged.get(key, {}).get("score", 0) + r["score"]}
        return sorted(merged.values(), key=lambda item: item.get("score", 0), reverse=True)[:15]

    @staticmethod
    def _bm25(query: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        terms = re.findall(r"\w+", query.lower())
        scored = []
        for record in records:
            counts = Counter(re.findall(r"\w+", record["text"].lower()))
            score = sum(counts[t] / (counts[t] + 1) for t in terms)
            if score:
                scored.append({**record, "score": score})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:12]

    def _rerank(self, query: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            from sentence_transformers import CrossEncoder
            if self._reranker is None and not self._reranker_failed:
                self._reranker = CrossEncoder(os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"))
            if self._reranker is None:
                return records
            scores = self._reranker.predict([(query, r["text"]) for r in records])
            return [r for _, r in sorted(zip(scores, records), key=lambda pair: pair[0], reverse=True)]
        except Exception:
            self._reranker_failed = True
            return records

    def _rewrite(self, query: str) -> str:
        if not self.memory or len(query.split()) > 8:
            return query
        return f"{query} (context: {self.memory[-1]['query']})"

    @staticmethod
    def _summary(query: str, records: List[Dict[str, Any]]) -> str:
        if not records:
            return "I could not find supporting material in the knowledge base. Upload a PDF and try again."
        snippets = " ".join(r["text"] for r in records[:3])
        sentences = re.split(r"(?<=[.!?])\s+", snippets)
        return "Executive summary: " + " ".join(sentences[:3])

    @staticmethod
    def _extract_text(filename: str, content: bytes) -> str:
        if filename.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader
                from io import BytesIO
                return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
            except Exception as exc:
                raise ValueError(f"Unable to read PDF: {exc}")
        return content.decode("utf-8", errors="ignore")


rag_service = ProductionRAG()
