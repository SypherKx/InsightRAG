"""
Vector store module using FAISS.

Manages FAISS indices for similarity search.
Supports incremental additions and persistence.
Uses inner product (cosine similarity with normalized vectors).
"""

import os
import pickle
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not installed. Install with: pip install faiss-cpu or faiss-gpu")

from .models import DocumentChunk
from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store for document embeddings.

    Features:
    - Cosine similarity search (using inner product with L2-normalized vectors)
    - Incremental document additions
    - Index persistence to disk
    - Metadata storage alongside vectors
    - Thread-safe operations with reentrant lock
    - Atomic writes and rollback protection
    """

    def __init__(self, embedding_generator: EmbeddingGenerator,
                 index_path: Optional[str] = None):
        """
        Initialize vector store.

        Args:
            embedding_generator: Embedding generator instance
            index_path: Optional path to load/save FAISS index

        Raises:
            ImportError: If FAISS not available
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is required. Install with: pip install faiss-cpu or faiss-gpu")

        self.embedding_gen = embedding_generator
        self.index_path = index_path
        self.dimension = embedding_generator.dimension
        self._lock = threading.RLock()

        # FAISS index (IndexFlatIP for inner product/cosine similarity)
        self.index: Optional[faiss.Index] = None

        # Metadata storage: maps internal FAISS ID to chunk data
        self.metadata: Dict[int, Dict[str, Any]] = {}

        # Mapping from external chunk_id to internal FAISS ID
        self.chunk_id_to_faiss_id: Dict[str, int] = {}

        # Statistics
        self.total_vectors = 0
        self._next_id = 0

        # Try to load existing index
        faiss_file = f"{index_path}.faiss" if index_path else None
        meta_file = f"{index_path}.meta" if index_path else None
        if index_path and ((faiss_file and os.path.exists(faiss_file) and meta_file and os.path.exists(meta_file)) or os.path.exists(index_path)):
            self.load(index_path)
        else:
            self._init_index()

    def _init_index(self):
        """Initialize a new FAISS index."""
        # Use IndexFlatIP for cosine similarity with normalized vectors
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = {}
        self.chunk_id_to_faiss_id = {}
        self._next_id = 0
        logger.info(f"Initialized new FAISS index (dim={self.dimension})")

    def add_chunks(self, chunks: List[DocumentChunk],
                   embeddings: Optional[np.ndarray] = None) -> List[int]:
        """
        Add document chunks to the index with atomic rollback and thread safety.

        Args:
            chunks: List of DocumentChunk objects (must have .embedding or provide embeddings)
            embeddings: Optional pre-computed embeddings (overrides chunk.embedding)

        Returns:
            List of FAISS IDs assigned to the chunks

        Raises:
            ValueError: If chunks have no embeddings and embeddings not provided
        """
        if not chunks:
            return []

        with self._lock:
            # Snapshot state for atomic rollback on failure
            prev_ntotal = self.index.ntotal if self.index else 0
            prev_next_id = self._next_id
            prev_metadata = dict(self.metadata)
            prev_mapping = dict(self.chunk_id_to_faiss_id)
            prev_total_vectors = self.total_vectors

            try:
                # Collect embeddings
                if embeddings is not None:
                    chunk_embeddings = embeddings
                else:
                    # Extract embeddings from chunks
                    chunk_embeddings = []
                    missing_embeddings = []

                    for i, chunk in enumerate(chunks):
                        if chunk.embedding is None:
                            missing_embeddings.append(i)
                        else:
                            chunk_embeddings.append(chunk.embedding)

                    if missing_embeddings:
                        raise ValueError(f"Chunks missing embeddings at indices: {missing_embeddings}")

                    chunk_embeddings = np.array(chunk_embeddings, dtype=np.float32)

                # Ensure 2D array
                if chunk_embeddings.ndim == 1:
                    chunk_embeddings = chunk_embeddings.reshape(1, -1)

                # Normalize embeddings for cosine similarity (IndexFlatIP expects normalized)
                faiss.normalize_L2(chunk_embeddings)

                # Add to FAISS index
                self.index.add(chunk_embeddings)
                added_count = chunk_embeddings.shape[0]

                # Store metadata
                faiss_ids = []
                for i, chunk in enumerate(chunks):
                    faiss_id = self._next_id + i

                    # Store chunk data (excluding embedding to save memory)
                    self.metadata[faiss_id] = {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "org_id": chunk.org_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "display_text": getattr(chunk, "text", ""),
                        "embedded_text": getattr(chunk, "embedded_text", chunk.text) or chunk.text,
                        "metadata": chunk.metadata.copy()
                    }

                    # Track mapping
                    self.chunk_id_to_faiss_id[chunk.id] = faiss_id
                    faiss_ids.append(faiss_id)

                self._next_id += added_count
                self.total_vectors = self.index.ntotal

                logger.info(f"Added {len(chunks)} chunks to vector store (total: {self.total_vectors})")
                return faiss_ids

            except Exception as e:
                logger.exception(f"Failed to add chunks to FAISS index, rolling back cleanly: {e}")
                # Rollback in-memory metadata and tracking
                self.metadata = prev_metadata
                self.chunk_id_to_faiss_id = prev_mapping
                self._next_id = prev_next_id
                self.total_vectors = prev_total_vectors
                # Reset or reload FAISS index if vectors were partially added
                if self.index and self.index.ntotal != prev_ntotal:
                    if prev_ntotal == 0:
                        self._init_index()
                    elif self.index_path and os.path.exists(f"{self.index_path}.faiss") and os.path.exists(f"{self.index_path}.meta"):
                        self.load(self.index_path)
                    else:
                        self._init_index()
                raise

    def search(self, query_embedding: np.ndarray, k: int = 5,
               filter_func: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Search for similar chunks in a thread-safe manner.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_func: Optional filter function(metadata) -> bool

        Returns:
            List of result dicts with similarity, chunk data, and metadata
        """
        with self._lock:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("Empty index, no vectors to search")
                return []

            # Ensure query is 2D and normalized
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)

            query_norm = np.linalg.norm(query_embedding)
            if query_norm > 0:
                query_embedding = query_embedding / query_norm

            # Search
            k_search = min(k * 2, self.index.ntotal)  # Fetch more in case we filter
            distances, indices = self.index.search(query_embedding.astype(np.float32), k_search)

            results = []
            for i, (distance, faiss_id) in enumerate(zip(distances[0], indices[0])):
                if faiss_id == -1:  # FAISS returns -1 for padded results
                    continue

                # Get metadata
                meta = self.metadata.get(int(faiss_id))
                if not meta:
                    logger.warning(f"Missing metadata for FAISS ID {faiss_id}")
                    continue

                # Apply filter if provided
                if filter_func and not filter_func(meta):
                    continue

                # Convert inner product to cosine similarity (already normalized)
                # Clamp to [0, 1] — float precision can push IP slightly above 1.0
                similarity = min(max(float(distance), 0.0), 1.0)

                result = {
                    "chunk_id": meta["chunk_id"],
                    "faiss_id": int(faiss_id),
                    "similarity_score": similarity,
                    "document_id": meta["document_id"],
                    "org_id": meta["org_id"],
                    "text": meta["text"],
                    "metadata": meta["metadata"],
                    "rank": len(results) + 1
                }

                results.append(result)

                # Stop if we have enough results
                if len(results) >= k:
                    break

            return results

    def delete_by_chunk_id(self, chunk_id: str) -> bool:
        """
        Remove a chunk from the index.

        Note: FAISS doesn't support direct deletion in IndexFlat.
        This creates a new index without the deleted vectors.

        Args:
            chunk_id: External chunk ID to remove

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if chunk_id not in self.chunk_id_to_faiss_id:
                return False

            faiss_id = self.chunk_id_to_faiss_id[chunk_id]
            logger.warning("Deletion requested - rebuilding index without deleted vectors")

            all_ids = list(range(self.index.ntotal))
            keep_ids = [i for i in all_ids if i != faiss_id]

            if not keep_ids:
                self._init_index()
                return True

            logger.error("Deletion not efficiently supported. Use IndexIDFactory2 or rebuild strategy.")
            raise NotImplementedError("Deletion requires IndexIDMap2 - not yet implemented")

    def save(self, path: Optional[str] = None):
        """
        Save index and metadata to disk atomically.

        Args:
            path: Index path (uses self.index_path if None)

        Saves:
            - {path}.faiss: FAISS index
            - {path}.meta: Metadata pickle file
        """
        save_path = path or self.index_path
        if not save_path:
            raise ValueError("No index path specified")

        with self._lock:
            target_dir = Path(save_path).parent
            target_dir.mkdir(parents=True, exist_ok=True)

            faiss_path = f"{save_path}.faiss"
            meta_path = f"{save_path}.meta"
            tmp_faiss = f"{save_path}.faiss.tmp_{os.getpid()}_{id(self)}"
            tmp_meta = f"{save_path}.meta.tmp_{os.getpid()}_{id(self)}"

            try:
                # Save FAISS index to temp file
                faiss.write_index(self.index, tmp_faiss)

                # Save metadata to temp file
                with open(tmp_meta, 'wb') as f:
                    pickle.dump({
                        "metadata": self.metadata,
                        "chunk_id_to_faiss_id": self.chunk_id_to_faiss_id,
                        "_next_id": self._next_id,
                        "dimension": self.dimension,
                        "total_vectors": self.total_vectors
                    }, f)

                # Atomic replace
                os.replace(tmp_faiss, faiss_path)
                os.replace(tmp_meta, meta_path)

                logger.info(f"Saved index to {save_path} ({self.total_vectors} vectors)")
            finally:
                if os.path.exists(tmp_faiss):
                    try:
                        os.remove(tmp_faiss)
                    except OSError:
                        pass
                if os.path.exists(tmp_meta):
                    try:
                        os.remove(tmp_meta)
                    except OSError:
                        pass

    def load(self, path: str):
        """
        Load index and metadata from disk in a thread-safe manner.

        Args:
            path: Index base path

        Raises:
            FileNotFoundError: If index files not found
        """
        with self._lock:
            faiss_path = f"{path}.faiss"
            meta_path = f"{path}.meta"

            if not os.path.exists(faiss_path) or not os.path.exists(meta_path):
                logger.warning(f"Index files not found at {path}, initializing new index")
                self._init_index()
                return

            # Load FAISS index
            self.index = faiss.read_index(faiss_path)

            # Load metadata
            with open(meta_path, 'rb') as f:
                data = pickle.load(f)

            self.metadata = data["metadata"]
            self.chunk_id_to_faiss_id = data["chunk_id_to_faiss_id"]
            self._next_id = data["_next_id"]
            self.dimension = data["dimension"]
            self.total_vectors = data["total_vectors"]

            logger.info(f"Loaded index from {path} ({self.total_vectors} vectors, dim={self.dimension})")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics in a thread-safe manner.

        Returns:
            Dictionary with stats
        """
        with self._lock:
            return {
                "total_vectors": self.total_vectors,
                "dimension": self.dimension,
                "unique_documents": len(set(m["document_id"] for m in self.metadata.values())),
                "unique_orgs": len(set(m["org_id"] for m in self.metadata.values())),
                "index_path": self.index_path,
                "index_type": type(self.index).__name__ if self.index else None
            }

    def clear(self):
        """Clear all data from the index in a thread-safe manner."""
        with self._lock:
            self._init_index()
            logger.info("Cleared vector store")


def create_default_vector_store(index_path: Optional[str] = None) -> FAISSVectorStore:
    """
    Create vector store with default embedding generator.

    Args:
        index_path: Optional path for index persistence

    Returns:
        Initialized FAISSVectorStore
    """
    embedding_gen = create_default_embedding_generator()
    return FAISSVectorStore(embedding_gen, index_path)
