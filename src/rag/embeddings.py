"""
Embedding generation module for RAG pipeline.

Uses sentence-transformers to generate dense vector embeddings.
Default model: all-MiniLM-L6-v2 (384 dimensions)
"""

from typing import List, Optional, Union
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    normalize_embeddings: bool = True
    device: Optional[str] = None  # "cpu", "cuda", or None for auto-detect
    show_progress_bar: bool = False


class EmbeddingGenerator:
    """
    Generates embeddings using sentence-transformers.

    Wraps the sentence-transformers library for consistent interface.
    Handles batching, normalization, and device management.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize embedding generator.

        Args:
            config: Embedding configuration

        Raises:
            ImportError: If sentence-transformers not installed
        """
        self.config = config or EmbeddingConfig()
        self._model = None
        self._dimension = 384  # Default for all-MiniLM-L6-v2
        self._initialized = False

    def _lazy_init(self):
        """Lazy load model on first use to reduce startup time."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.config.model_name}")
            self._model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device
            )
            test_emb = self._model.encode(["test"], convert_to_numpy=True)
            self._dimension = test_emb.shape[1]
            self._initialized = True
            logger.info(f"SentenceTransformer loaded (dimension: {self._dimension})")
        except Exception as e:
            logger.warning(f"SentenceTransformer not ready ({e}). Using sklearn vectorizer fallback.")
            from sklearn.feature_extraction.text import HashingVectorizer
            self._vectorizer = HashingVectorizer(n_features=self._dimension, norm="l2", alternate_sign=False)
            self._model = None
            self._initialized = True

    def set_device(self, device: str) -> str:
        """
        Dynamically switch embedding generator execution device between 'cuda' (GPU) and 'cpu'.
        """
        self.config.device = device
        if self._model is not None:
            try:
                import torch
                if device == "cuda" and not torch.cuda.is_available():
                    logger.warning("CUDA not available in PyTorch. Retaining CPU device.")
                    self.config.device = "cpu"
                    return "cpu"
                self._model = self._model.to(device)
                logger.info(f"SentenceTransformer moved to {device.upper()}")
                return device
            except Exception as e:
                logger.warning(f"Could not move model to {device}: {e}")
                return "cpu"
        return device

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    def generate(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            batch_size: Override batch size for this call

        Returns:
            numpy array of shape (len(texts), dimension)

        Raises:
            ValueError: If texts list is empty or contains invalid texts
        """
        if not texts:
            raise ValueError("No texts provided for embedding")

        # Filter out empty/invalid texts
        valid_texts = [t for t in texts if t and t.strip()]
        if len(valid_texts) != len(texts):
            logger.warning(f"Filtered {len(texts) - len(valid_texts)} empty texts")

        if not valid_texts:
            raise ValueError("No valid texts provided for embedding")

        self._lazy_init()

        batch_size = batch_size or self.config.batch_size

        try:
            if self._model is not None:
                embeddings = self._model.encode(
                    valid_texts,
                    batch_size=batch_size,
                    show_progress_bar=self.config.show_progress_bar,
                    convert_to_numpy=True,
                    normalize_embeddings=self.config.normalize_embeddings
                )
            else:
                sparse_mat = self._vectorizer.transform(valid_texts)
                embeddings = sparse_mat.toarray()

            # Ensure 2D array
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)

            logger.debug(f"Generated {len(embeddings)} embeddings (batch_size={batch_size})")
            return embeddings.astype(np.float32)

        except Exception as e:
            logger.exception(f"Failed to generate embeddings: {e}")
            raise

    def generate_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (with LRU query cache).

        Args:
            text: Text to embed

        Returns:
            numpy array of shape (dimension,)
        """
        if not text or not text.strip():
            raise ValueError("Empty text provided for embedding")

        try:
            from .cache import query_cache
            cached = query_cache.get(text)
            if cached is not None:
                return cached
        except Exception:
            cached = None

        emb = self.generate([text])[0]
        try:
            from .cache import query_cache
            query_cache.set(text, emb)
        except Exception:
            pass
        return emb

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score (0-1)
        """
        # Normalize if needed
        if embedding1.ndim == 1:
            embedding1 = embedding1.reshape(1, -1)
        if embedding2.ndim == 1:
            embedding2 = embedding2.reshape(1, -1)

        # Cosine similarity
        norm1 = np.linalg.norm(embedding1, axis=1, keepdims=True)
        norm2 = np.linalg.norm(embedding2, axis=1, keepdims=True)

        normalized1 = embedding1 / (norm1 + 1e-8)
        normalized2 = embedding2 / (norm2 + 1e-8)

        similarity = np.dot(normalized1, normalized2.T)
        return float(similarity[0, 0])

    def compute_similarities(self, query_embedding: np.ndarray,
                            candidate_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute similarities between query and multiple candidates.

        Optimized batch computation.

        Args:
            query_embedding: Query embedding (1D or 2D)
            candidate_embeddings: Candidate embeddings (2D)

        Returns:
            Array of similarity scores
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Normalize
        query_norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
        query_normalized = query_embedding / (query_norm + 1e-8)

        candidate_norm = np.linalg.norm(candidate_embeddings, axis=1, keepdims=True)
        candidate_normalized = candidate_embeddings / (candidate_norm + 1e-8)

        # Compute similarities
        similarities = np.dot(candidate_normalized, query_normalized.T).flatten()
        return similarities


def create_default_embedding_generator() -> EmbeddingGenerator:
    """Create embedding generator with default configuration."""
    config = EmbeddingConfig(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=32,
        normalize_embeddings=True
    )
    return EmbeddingGenerator(config)
