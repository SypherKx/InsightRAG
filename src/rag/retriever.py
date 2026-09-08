"""
Retriever module for RAG pipeline.

Orchestrates retrieval: query embedding, vector search, filtering, ranking.
Returns structured results with relevance scores.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable
import numpy as np

from .models import Document, DocumentChunk, RAGQuery, RAGResponse, RetrievalResult
from .embeddings import EmbeddingGenerator
from .vectorstore import FAISSVectorStore

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    High-level retriever that orchestrates the search pipeline.

    Combines:
    - Query embedding generation
    - Vector similarity search
    - Metadata filtering
    - Result ranking and formatting
    """

    def __init__(self, vector_store: FAISSVectorStore,
                 embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize retriever.

        Args:
            vector_store: Initialized vector store
            embedding_generator: Optional embedding generator (uses store's if None)
        """
        self.vector_store = vector_store
        self.embedding_gen = embedding_generator or vector_store.embedding_gen

    def retrieve(self, query: RAGQuery,
                 load_documents: bool = False) -> RAGResponse:
        """
        Execute a retrieval query.

        Pipeline:
        1. Generate query embedding
        2. Perform vector similarity search
        3. Apply metadata filters
        4. Filter by minimum score
        5. Format results

        Args:
            query: Query parameters
            load_documents: Whether to load full document data for results

        Returns:
            RAGResponse with results

        Raises:
            ValueError: If query invalid or embedding fails
        """
        start_time = time.time()

        try:
            # 1. Generate query embedding (with LRU cache)
            emb_start = time.time()
            query_embedding = self.embedding_gen.generate_single(query.query)
            emb_time_ms = (time.time() - emb_start) * 1000

            # 2. Define filter function based on query filters
            filter_func = self._build_filter(query.filters) if query.filters else None

            # 3. Dense FAISS Search (Candidate Pool: top_k * 3)
            search_start = time.time()
            candidate_k = max(query.top_k * 3, 10)
            dense_results = self.vector_store.search(
                query_embedding,
                k=candidate_k,
                filter_func=filter_func
            )
            dense_time_ms = (time.time() - search_start) * 1000

            # 4. Lexical / Keyword Search (BM25-style token matching)
            lex_start = time.time()
            lexical_results = self._lexical_search(
                query.query,
                k=candidate_k,
                filter_func=filter_func
            )
            lex_time_ms = (time.time() - lex_start) * 1000

            # 5. Reciprocal Rank Fusion (RRF)
            fused_candidates = self._reciprocal_rank_fusion(
                dense_results,
                lexical_results,
                k=60
            )

            # 5.1 Page-Aware Candidate Injection:
            # If user query specifically asks for a page (e.g., 'page 42', 'pg 5'),
            # ensure all chunks from that page are guaranteed in the candidate pool.
            import re
            pm = re.search(r'\b(?:page|pg|p\.?|pno|page\s*no|page\s*number)\s*[:#\-]?\s*(\d+)\b', query.query, re.IGNORECASE)
            target_page = int(pm.group(1)) if pm else (query.filters.get("page_number") if query.filters else None)

            if target_page is not None:
                existing_cids = {c["chunk_id"] for c in fused_candidates}
                page_candidates = []
                for fid, meta_item in getattr(self.vector_store, "metadata", {}).items():
                    m = meta_item.get("metadata", {})
                    p_val = m.get("page_number") or m.get("page")
                    if p_val is not None and int(p_val) == int(target_page):
                        cid = meta_item.get("chunk_id", str(fid))
                        if cid not in existing_cids:
                            page_candidates.append({
                                "faiss_id": fid,
                                "chunk_id": cid,
                                "document_id": meta_item.get("document_id", ""),
                                "org_id": meta_item.get("org_id", ""),
                                "text": meta_item.get("text", ""),
                                "metadata": m,
                                "similarity_score": 1.0,
                                "rrf_score": 1.0,
                            })
                if page_candidates:
                    fused_candidates = page_candidates + fused_candidates

            # 6. Lightweight Semantic Reranking
            rerank_start = time.time()
            reranked_results = self._rerank_candidates(
                query.query,
                fused_candidates,
                top_k=query.top_k,
                min_score=query.min_score
            )
            rerank_time_ms = (time.time() - rerank_start) * 1000

            # 7. Format results with proper ranks
            retrieval_results = self._format_results(
                reranked_results,
                load_documents=load_documents
            )

            # 8. Build response
            query_time = (time.time() - start_time) * 1000
            response = RAGResponse(
                query=query.query,
                results=retrieval_results,
                total_results=len(fused_candidates),
                query_time_ms=query_time,
                metadata={
                    "embedding_time_ms": round(emb_time_ms, 2),
                    "dense_search_time_ms": round(dense_time_ms, 2),
                    "lexical_search_time_ms": round(lex_time_ms, 2),
                    "rerank_time_ms": round(rerank_time_ms, 2),
                    "hybrid_candidates_count": len(fused_candidates),
                    "filters_applied": query.filters if query.filters else None,
                    "top_k_requested": query.top_k,
                    "org_id": query.org_id
                }
            )

            logger.info(
                f"Retrieved {len(retrieval_results)} high-precision results "
                f"from {len(fused_candidates)} hybrid candidates in {query_time:.1f}ms"
            )

            return response

        except Exception as e:
            logger.exception(f"Retrieval failed for query: {query.query}")
            raise

    def _lexical_search(self, query_text: str, k: int = 10,
                        filter_func: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Fast lexical / keyword search across stored document chunks.
        Matches exact terms, numbers, acronyms, and codes.
        """
        import re
        tokens = set(re.findall(r'[a-zA-Z0-9_\-\.]{2,}', query_text.lower()))
        if not tokens:
            return []

        matches = []
        vector_metadata = getattr(self.vector_store, "metadata", {})
        for faiss_id, meta in vector_metadata.items():
            if filter_func and not filter_func(meta):
                continue

            text = meta.get("text", "").lower()
            if not text:
                continue

            # Compute term overlap score
            matched_count = sum(1 for t in tokens if t in text)
            if matched_count > 0:
                score = matched_count / len(tokens)
                matches.append({
                    "faiss_id": faiss_id,
                    "chunk_id": meta.get("chunk_id", str(faiss_id)),
                    "document_id": meta.get("document_id", ""),
                    "org_id": meta.get("org_id", ""),
                    "text": meta.get("text", ""),
                    "metadata": meta.get("metadata", {}),
                    "similarity_score": score
                })

        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches[:k]

    def _reciprocal_rank_fusion(self, dense_results: List[Dict],
                               lexical_results: List[Dict],
                               k: int = 60) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) to merge Dense + Lexical candidate rankings.
        """
        scores: Dict[str, float] = {}
        item_map: Dict[str, Dict] = {}

        # 1. Score Dense Ranks
        for rank, item in enumerate(dense_results):
            cid = item["chunk_id"]
            item_map[cid] = item
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # 2. Score Lexical Ranks
        for rank, item in enumerate(lexical_results):
            cid = item["chunk_id"]
            if cid not in item_map:
                item_map[cid] = item
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

        # 3. Sort by combined RRF score
        fused = []
        for cid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            entry = item_map[cid].copy()
            entry["rrf_score"] = score
            fused.append(entry)

        return fused

    def _rerank_candidates(self, query_text: str, candidate_pool: List[Dict],
                           top_k: int = 4, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Lightweight Semantic Cross-Reranker.
        Computes direct relevance between query and chunk contents to eliminate irrelevant context.
        """
        if not candidate_pool:
            return []

        # If candidates <= top_k, return directly
        if len(candidate_pool) <= top_k:
            return candidate_pool

        try:
            # Batch encode candidate texts and calculate cosine similarities with query
            cand_texts = [c["text"] for c in candidate_pool]
            cand_embs = self.embedding_gen.generate(cand_texts)
            q_emb = self.embedding_gen.generate_single(query_text)
            sims = self.embedding_gen.compute_similarities(q_emb, cand_embs)

            import re
            pm = re.search(r'\b(?:page|pg|p\.?|pno|page\s*no|page\s*number)\s*[:#\-]?\s*(\d+)\b', query_text, re.IGNORECASE)
            t_page = int(pm.group(1)) if pm else None

            for i, c in enumerate(candidate_pool):
                base_score = float(sims[i])
                c_meta = c.get("metadata", {})
                c_page = c_meta.get("page_number") or c_meta.get("page")
                if t_page is not None and c_page is not None and int(c_page) == t_page:
                    base_score += 2.0  # Dominant boost for exact page requested
                c["similarity_score"] = base_score

            candidate_pool.sort(key=lambda x: x["similarity_score"], reverse=True)
            filtered = [c for c in candidate_pool if c["similarity_score"] >= min_score]
            return filtered[:top_k]
        except Exception as e:
            logger.warning(f"Reranking fallback to RRF order: {e}")
            return candidate_pool[:top_k]

    def _build_filter(self, filters: Dict[str, Any]) -> Callable[[Dict], bool]:
        """
        Build a metadata filter function.

        Args:
            filters: Dictionary of metadata key -> expected value(s)

        Returns:
            Filter function that returns True if metadata matches all filters
        """
        def filter_func(metadata: Dict) -> bool:
            for key, expected in filters.items():
                actual = metadata.get(key)

                # Handle list of acceptable values
                if isinstance(expected, list):
                    if actual not in expected:
                        return False
                elif actual != expected:
                    return False

            return True

        return filter_func

    def _format_results(self, raw_results: List[Dict],
                       load_documents: bool = False) -> List[RetrievalResult]:
        """
        Format raw search results into RetrievalResult objects.

        Args:
            raw_results: Raw search results from vector store
            load_documents: Whether to include full document data

        Returns:
            List of RetrievalResult objects
        """
        results = []

        for i, raw in enumerate(raw_results):
            # Build chunk object
            chunk = DocumentChunk(
                id=raw["chunk_id"],
                document_id=raw["document_id"],
                org_id=raw["org_id"],
                chunk_index=0,  # Not stored in metadata, could add if needed
                text=raw["text"],
                metadata=raw["metadata"],
                embedding=None  # Don't return embeddings to save bandwidth
            )

            # Create RetrievalResult
            result = RetrievalResult(
                chunk=chunk,
                similarity_score=raw["similarity_score"],
                rank=i + 1,
                document=None  # Not loaded by default
            )

            results.append(result)

        return results

    def retrieve_with_context(self, query: str, org_id: str, top_k: int = 5,
                             filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Simplified retrieval returning dict format.

        Args:
            query: Query string
            org_id: Organization ID
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            List of result dictionaries with text, score, and metadata
        """
        query_obj = RAGQuery(
            query=query,
            org_id=org_id,
            top_k=top_k,
            filters=filters or {},
            min_score=0.0
        )

        response = self.retrieve(query_obj, load_documents=False)

        # Convert to simple dict format
        simple_results = []
        for result in response.results:
            simple_results.append({
                "text": result.chunk.text,
                "score": float(result.similarity_score),
                "rank": result.rank,
                "chunk_id": result.chunk.id,
                "document_id": result.chunk.document_id,
                "metadata": result.chunk.metadata
            })

        return simple_results

    def search_similar_to_chunk(self, chunk_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Find chunks similar to a specific chunk (by ID).

        Args:
            chunk_id: Source chunk ID
            k: Number of similar chunks

        Returns:
            List of similar chunks with similarity scores
        """
        if chunk_id not in self.vector_store.chunk_id_to_faiss_id:
            logger.warning(f"Chunk ID not found: {chunk_id}")
            return []

        faiss_id = self.vector_store.chunk_id_to_faiss_id[chunk_id]

        # Get embedding from metadata? Not stored there.
        # Would need to reconstruct from index or have separate lookup
        logger.error("Chunk similarity search not implemented without stored embedding")
        return []

    def get_relevant_context(self, anomaly_context: Dict[str, Any],
                            top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Get relevant context based on anomaly metadata.

        Convenience method for root cause/explanation services.

        Args:
            anomaly_context: Dict with anomaly details (metric, dimensions, timestamp, etc.)
            top_k: Number of context chunks

        Returns:
            List of relevant context documents with scores
        """
        # Build query from anomaly context
        query_parts = []

        metric = anomaly_context.get("metric", "")
        if metric:
            query_parts.append(f"metric: {metric}")

        dimensions = anomaly_context.get("dimensions", {})
        for key, value in dimensions.items():
            query_parts.append(f"{key}: {value}")

        anomaly_type = anomaly_context.get("anomaly_type", "")
        if anomaly_type:
            query_parts.append(f"type: {anomaly_type}")

        # Include business question if provided
        question = anomaly_context.get("question", "")
        if question:
            query_parts.append(question)

        query = " ".join(query_parts)

        if not query.strip():
            logger.warning("Empty query from anomaly context")
            return []

        # Build filters: only return docs for this org
        filters = {}
        if "org_id" in anomaly_context:
            filters["org_id"] = anomaly_context["org_id"]

        # Maybe filter by document type based on context?
        # e.g., for metric questions, prefer metric_def or incident docs
        if "document_type" in anomaly_context:
            filters["document_type"] = anomaly_context["document_type"]

        return self.retrieve_with_context(
            query=query,
            org_id=anomaly_context.get("org_id", ""),
            top_k=top_k,
            filters=filters if filters else None
        )


def create_default_retriever(vector_store: Optional[FAISSVectorStore] = None,
                            index_path: Optional[str] = None) -> RAGRetriever:
    """
    Create retriever with default components.

    Args:
        vector_store: Optional existing vector store
        index_path: Path for vector store (creates new if None or not provided)

    Returns:
        Initialized RAGRetriever
    """
    if vector_store is None:
        if index_path:
            vector_store = create_default_vector_store(index_path)
        else:
            # Create in-memory store
            from .embeddings import create_default_embedding_generator
            embedding_gen = create_default_embedding_generator()
            vector_store = FAISSVectorStore(embedding_gen)

    return RAGRetriever(vector_store)
