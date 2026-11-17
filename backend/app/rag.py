"""
Independent RAG Document Intelligence module.
Provides document uploading, chunking, retrieval, grounded question answering, and citations.
Strictly decoupled from structured SQL generation to prevent interference.
"""
import re
import math
from typing import List, Dict, Any, Optional

class DocumentStore:
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []

    def clear(self):
        self.documents.clear()
        self.chunks.clear()

    def add_document(self, doc_id: str, filename: str, content: str, chunk_size: int = 400) -> Dict[str, Any]:
        """
        Store a document, split into overlapping chunks, and index it for retrieval.
        """
        self.documents[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "length": len(content)
        }

        # Simple sentence-aware chunking
        words = content.split()
        doc_chunks = []
        step = max(50, chunk_size - 100)
        
        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size]
            if not chunk_words:
                break
            chunk_text = " ".join(chunk_words)
            chunk_obj = {
                "chunk_id": f"{doc_id}_c{len(doc_chunks) + 1}",
                "doc_id": doc_id,
                "filename": filename,
                "text": chunk_text
            }
            doc_chunks.append(chunk_obj)
            self.chunks.append(chunk_obj)

        return {
            "doc_id": doc_id,
            "filename": filename,
            "total_chunks": len(doc_chunks)
        }

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Rank chunks using lexical term matching (TF-IDF approximation).
        """
        if not self.chunks or not query.strip():
            return []

        query_terms = [re.sub(r"[^\w]", "", w.lower()) for w in query.split() if len(w) > 2]
        if not query_terms:
            return []

        scored_chunks = []
        for c in self.chunks:
            chunk_text_lower = c["text"].lower()
            score = 0.0
            matched_terms = []
            
            for term in query_terms:
                count = chunk_text_lower.count(term)
                if count > 0:
                    score += 1.0 + math.log(count + 1)
                    matched_terms.append(term)

            if score > 0:
                scored_chunks.append({
                    "chunk_id": c["chunk_id"],
                    "filename": c["filename"],
                    "text": c["text"],
                    "score": round(score, 3),
                    "matched_terms": matched_terms
                })

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Retrieve chunks, synthesize grounded response, and provide citations.
        """
        retrieved = self.search(query, top_k=3)
        if not retrieved:
            return {
                "answer": "No relevant documents or passages found matching your query.",
                "citations": [],
                "retrieved_count": 0
            }

        citations = []
        for r in retrieved:
            citations.append({
                "source": r["filename"],
                "chunk_id": r["chunk_id"],
                "relevance_score": r["score"],
                "excerpt": r["text"][:150] + "..." if len(r["text"]) > 150 else r["text"]
            })

        # Synthesize grounded answer
        top_excerpt = retrieved[0]["text"]
        summary = f"Based on {retrieved[0]['filename']}: {top_excerpt[:300]}..."

        return {
            "answer": summary,
            "citations": citations,
            "retrieved_count": len(retrieved)
        }

# Global singleton instance for app runtime
doc_store = DocumentStore()
