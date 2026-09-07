"""
Performance Caching and Telemetry Module for InsightRAG.

Provides:
- Thread-safe LRU Query Embedding Cache
- Document Content Hash Deduplication
- Microsecond-precision Pipeline Latency Timer & Telemetry
"""

import time
import hashlib
import threading
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
import numpy as np
import logging

logger = logging.getLogger(__name__)


class QueryEmbeddingCache:
    """Thread-safe LRU cache for query text -> embedding vectors."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, query: str) -> Optional[np.ndarray]:
        key = query.strip().lower()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                return self._cache[key].copy()
            self.misses += 1
            return None

    def set(self, query: str, embedding: np.ndarray) -> None:
        key = query.strip().lower()
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                self._cache[key] = embedding.copy()

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0


class DocumentHashRegistry:
    """Tracks document SHA256 hashes to prevent redundant re-indexing."""

    def __init__(self):
        self._hashes: Dict[str, str] = {}
        self._lock = threading.Lock()

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return ""

    def is_already_indexed(self, doc_id: str, file_path: str) -> bool:
        new_hash = self.compute_file_hash(file_path)
        if not new_hash:
            return False
        with self._lock:
            return self._hashes.get(doc_id) == new_hash

    def register(self, doc_id: str, file_path: str) -> None:
        new_hash = self.compute_file_hash(file_path)
        if new_hash:
            with self._lock:
                self._hashes[doc_id] = new_hash

    def remove(self, doc_id: str) -> None:
        with self._lock:
            self._hashes.pop(doc_id, None)

    def clear(self) -> None:
        with self._lock:
            self._hashes.clear()


class LatencyProfiler:
    """High-precision execution timer for measuring end-to-end RAG stages."""

    def __init__(self):
        self._start_times: Dict[str, float] = {}
        self.durations_ms: Dict[str, float] = {}
        self._overall_start = time.perf_counter()

    def start_stage(self, name: str) -> None:
        self._start_times[name] = time.perf_counter()

    def end_stage(self, name: str) -> float:
        start = self._start_times.pop(name, None)
        if start is not None:
            duration = (time.perf_counter() - start) * 1000.0
            self.durations_ms[name] = round(duration, 2)
            return self.durations_ms[name]
        return 0.0

    def get_metrics(self) -> Dict[str, Any]:
        total = (time.perf_counter() - self._overall_start) * 1000.0
        return {
            **self.durations_ms,
            "total_e2e_ms": round(total, 2)
        }


# Global Singletons
query_cache = QueryEmbeddingCache(max_size=2000)
doc_hash_registry = DocumentHashRegistry()
