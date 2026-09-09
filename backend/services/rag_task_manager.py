"""
RAG Ingestion Task Manager and Thread Pool Executor.

Manages background document ingestion tasks, multi-stage progress tracking,
and offloads CPU-bound extraction/embedding work to a dedicated thread pool
so concurrent API queries are never blocked.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Dedicated bounded thread pool for CPU-heavy ingestion work (PyMuPDF, OpenCV, Embeddings)
# Keeps work off the FastAPI event loop and allows concurrent HTTP queries to respond promptly.
INGESTION_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="rag-ingest-worker"
)


class RAGTaskManager:
    """
    Thread-safe in-memory registry for document ingestion background tasks.
    Tracks status, multi-stage progress (0-5), and error state.
    """

    def __init__(self, max_history: int = 100):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._max_history = max_history

    def create_task(self, task_id: str, files: List[str]) -> Dict[str, Any]:
        """Register a new ingestion task."""
        with self._lock:
            # Prune old tasks if exceeding max_history
            if len(self._tasks) >= self._max_history:
                # Remove oldest tasks
                sorted_tasks = sorted(self._tasks.items(), key=lambda x: x[1].get("created_at", ""))
                for old_id, _ in sorted_tasks[:20]:
                    del self._tasks[old_id]

            now = datetime.now(timezone.utc).isoformat()
            task = {
                "task_id": task_id,
                "status": "queued",
                "step": 0,
                "stage": "Document Buffer & Format Validation",
                "progress": 0,
                "message": f"Queued {len(files)} document(s) for background processing.",
                "files": files,
                "documents_ingested": 0,
                "chunks_created": 0,
                "errors": 0,
                "error_message": None,
                "created_at": now,
                "updated_at": now,
            }
            self._tasks[task_id] = task
            logger.info(f"Created ingestion task {task_id} for {len(files)} files")
            return dict(task)

    def update_progress(self, task_id: str, step: int, stage: str, progress: int, message: str):
        """Update progress metrics for an ongoing task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            # Do not overwrite terminal statuses
            if task["status"] in ("completed", "failed"):
                return

            task["status"] = "processing"
            task["step"] = step
            task["stage"] = stage
            task["progress"] = max(task["progress"], min(progress, 99))
            task["message"] = message
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

    def mark_completed(self, task_id: str, stats: Dict[str, Any], message: Optional[str] = None):
        """Mark a task as successfully completed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            now = datetime.now(timezone.utc).isoformat()
            task["status"] = "completed"
            task["step"] = 5
            task["stage"] = "Complete"
            task["progress"] = 100
            task["documents_ingested"] = stats.get("documents_ingested", len(task["files"]))
            task["chunks_created"] = stats.get("chunks_created", 0)
            task["errors"] = stats.get("errors", 0)
            task["error_message"] = None
            task["message"] = message or (
                f"Successfully indexed {task['documents_ingested']} document(s) "
                f"({task['chunks_created']} chunks)!"
            )
            task["updated_at"] = now
            logger.info(f"Task {task_id} completed: {task['chunks_created']} chunks created")

    def mark_failed(self, task_id: str, error_message: str, stage: Optional[str] = None):
        """Mark a task as failed with an error description."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            now = datetime.now(timezone.utc).isoformat()
            task["status"] = "failed"
            if stage:
                task["stage"] = stage
            task["error_message"] = error_message
            task["message"] = f"Ingestion failed: {error_message}"
            task["updated_at"] = now
            logger.error(f"Task {task_id} failed: {error_message}")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get copy of a task by ID."""
        with self._lock:
            task = self._tasks.get(task_id)
            return dict(task) if task else None

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tracked tasks."""
        with self._lock:
            return [dict(t) for t in self._tasks.values()]

    def clear(self):
        """Clear all tasks (used in tests or server reset)."""
        with self._lock:
            self._tasks.clear()


# Global singleton instance
rag_task_manager = RAGTaskManager()
