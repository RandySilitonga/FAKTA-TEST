"""
FAKTA - Hybrid Evidence Retriever
BM25 (keyword) + embedding (semantic) search over local evidence database.
"""

import os
import json
import hashlib
from typing import List, Dict, Optional
from pathlib import Path


class HybridRetriever:
    """
    Hybrid BM25 + embedding search for evidence retrieval.

    Uses:
    - BM25 for keyword matching (fast, interpretable)
    - ChromaDB + sentence-transformers for semantic similarity
    - Merged and ranked results with source credibility boost
    """

    def __init__(self, chroma_path: str = "data/evidence/chroma_db"):
        self.bm25 = None
        self.bm25_corpus = []
        self.bm25_docs = []

        # Credibility weights by tier
        self.tier_weights = {1: 1.0, 2: 0.9, 3: 0.75, 4: 0.4}

        # Cache
        self._cache: Dict[str, List[Dict]] = {}

        # Initialize components
        self._init_chroma(chroma_path)
        self._init_encoder()

    def _init_chroma(self, chroma_path: str):
        """Initialize ChromaDB persistent client."""
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name="indonesian_evidence",
                metadata={"hnsw:space": "cosine"},
            )
            print(f"[Retriever] ChromaDB initialized at {chroma_path}")
            print(f"[Retriever] Collection has {self.collection.count()} documents")
        except Exception as e:
            print(f"[Retriever] ChromaDB init failed: {e}")
            self.collection = None

    def _init_encoder(self):
        """Initialize sentence transformer for embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            print("[Retriever] Sentence encoder initialized")
        except Exception as e:
            print(f"[Retriever] Encoder init failed: {e}")
            self.encoder = None

    def add_document(self, doc_id: str, text: str, metadata: Dict):
        """
        Add a document to the evidence database.

        Args:
            doc_id: Unique document ID
            text: Document text content
            metadata: Dict with source, source_tier, url, title, date_published, etc.
        """
        if self.collection is None:
            return

        if self.encoder is None:
            return

        embedding = self.encoder.encode(text).tolist()

        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id],
        )

        # Add to BM25 index
        self._add_to_bm25(doc_id, text, metadata)

    def _add_to_bm25(self, doc_id: str, text: str, metadata: Dict):
        """Add document to BM25 index."""
        try:
            from rank_bm25 import BM25Okapi
            tokens = self._tokenize(text)
            self.bm25_corpus.append(tokens)
            self.bm25_docs.append({
                "id": doc_id,
                "text": text,
                **metadata,
            })
            self.bm25 = BM25Okapi(self.bm25_corpus)
        except Exception as e:
            print(f"[Retriever] BM25 add failed: {e}")

    def search(self, query: str, top_k: int = 5, use_cache: bool = True) -> List[Dict]:
        """
        Hybrid BM25 + embedding search.

        Args:
            query: Search query (claim text or keywords)
            top_k: Number of results to return
            use_cache: Whether to check cache first

        Returns:
            List of evidence dicts sorted by relevance
        """
        # Check cache
        if use_cache:
            cache_key = hashlib.md5(query.encode()).hexdigest()
            if cache_key in self._cache:
                return self._cache[cache_key]

        # BM25 search
        bm25_results = self._bm25_search(query, top_k * 2)

        # Embedding search
        embedding_results = self._embedding_search(query, top_k * 2)

        # Merge and rank
        merged = self._merge_and_rank(bm25_results, embedding_results, alpha=0.4)

        # Sort by final score
        merged.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        results = merged[:top_k]

        # Compute derived fields
        for r in results:
            r["relevance_score"] = r.get("final_score", 0.0)
            r["source_credibility"] = self.tier_weights.get(
                r.get("source_tier", 4), 0.4
            )

        # Cache
        if use_cache:
            cache_key = hashlib.md5(query.encode()).hexdigest()
            self._cache[cache_key] = results

        return results

    def _bm25_search(self, query: str, top_k: int) -> List[Dict]:
        """BM25 keyword search."""
        if not self.bm25 or not self.bm25_corpus:
            return []

        try:
            tokens = self._tokenize(query)
            scores = self.bm25.get_scores(tokens)

            # Get top_k indices
            import numpy as np
            top_indices = np.array(scores).argsort()[-top_k:][::-1]

            results = []
            max_score = max(scores) if max(scores) > 0 else 1.0

            for idx in top_indices:
                if scores[idx] > 0 and idx < len(self.bm25_docs):
                    results.append({
                        "doc_id": self.bm25_docs[idx].get("id", ""),
                        "bm25_score": scores[idx] / max_score,
                        "semantic_score": 0.0,
                        **self.bm25_docs[idx],
                    })

            return results
        except Exception as e:
            print(f"[Retriever] BM25 search error: {e}")
            return []

    def _embedding_search(self, query: str, top_k: int) -> List[Dict]:
        """Embedding-based semantic search via ChromaDB."""
        if self.collection is None or self.encoder is None:
            return []

        try:
            query_embedding = self.encoder.encode(query).tolist()

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            evidence_results = []
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                semantic_score = 1.0 - distance
                evidence_results.append({
                    "doc_id": metadata.get("id", ""),
                    "bm25_score": 0.0,
                    "semantic_score": semantic_score,
                    "text": doc,
                    **metadata,
                })

            return evidence_results
        except Exception as e:
            print(f"[Retriever] Embedding search error: {e}")
            return []

    def _merge_and_rank(self, bm25: List[Dict], embedding: List[Dict], alpha: float = 0.4) -> List[Dict]:
        """
        Merge BM25 and embedding results.
        alpha=0.4 means 40% BM25 + 60% embedding.
        """
        all_docs = {}

        for r in bm25:
            doc_id = r.get("doc_id", "")
            all_docs[doc_id] = r

        for r in embedding:
            doc_id = r.get("doc_id", "")
            if doc_id in all_docs:
                all_docs[doc_id]["semantic_score"] = r["semantic_score"]
            else:
                all_docs[doc_id] = r

        # Compute hybrid score
        for doc_id, r in all_docs.items():
            r["hybrid_score"] = alpha * r["bm25_score"] + (1 - alpha) * r["semantic_score"]
            credibility = self.tier_weights.get(r.get("source_tier", 4), 0.4)
            r["final_score"] = r["hybrid_score"] * credibility

        return list(all_docs.values())

    def _tokenize(self, text: str) -> List[str]:
        """Simple word-level tokenization for BM25."""
        import re
        text = text.lower()
        return re.findall(r'\b\w+\b', text)

    def clear_cache(self):
        """Clear search cache."""
        self._cache.clear()

    def get_stats(self) -> Dict:
        """Get database statistics."""
        return {
            "chroma_count": self.collection.count() if self.collection else 0,
            "bm25_count": len(self.bm25_corpus),
        }


if __name__ == "__main__":
    retriever = HybridRetriever()

    # Add sample documents
    sample_docs = [
        {
            "doc_id": "doc1",
            "text": "BPOM menyatakan bahwa matcha aman dikonsumsi dalam jumlah normal. Tidak ada bukti bahwa matcha menyebabkan gagal ginjal.",
            "metadata": {"source": "BPOM", "source_tier": 2, "url": "https://bpom.go.id/...", "title": "Keamanan Matcha"},
        },
        {
            "doc_id": "doc2",
            "text": "BMKG mencatat gempa magnitudo 5.2 di Maluku pada 15 Januari 2025. Tidak berpotensi tsunami.",
            "metadata": {"source": "BMKG", "source_tier": 2, "url": "https://bmkg.go.id/...", "title": "Gempa Maluku"},
        },
    ]

    for doc in sample_docs:
        retriever.add_document(doc["doc_id"], doc["text"], doc["metadata"])

    # Search
    results = retriever.search("matcha gagal ginjal")
    print(f"\nSearch results for 'matcha gagal ginjal':")
    for r in results:
        print(f"  [{r.get('source')}] score={r.get('final_score', 0):.3f} - {r.get('text', '')[:80]}...")

    print(f"\nDatabase stats: {retriever.get_stats()}")
