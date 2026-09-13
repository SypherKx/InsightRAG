"""
Active User Feedback & RLHF Weighting Store for InsightRAG.

Features:
1. Persistent JSON store for thumbs up / thumbs down user feedback.
2. Citation Weighting: +0.12 score boost for thumbs up, -0.15 penalty for thumbs down.
3. Negative Constraints Extraction: Extracts directives from negative feedback to inject into prompt assembly.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

FEEDBACK_FILE = Path("./data/rag_feedback.json")


class FeedbackStore:
    """Manages persistent feedback and citation score boosts/penalties."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FeedbackStore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, storage_path: Optional[Path] = None):
        if self._initialized:
            return
        self.storage_path = storage_path or FEEDBACK_FILE
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
        self._initialized = True

    def _load(self) -> Dict[str, Any]:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load feedback store: {e}")
        return {
            "ratings": [],
            "source_weights": {},  # key: source or chunk_id -> float net weight
            "negative_constraints": []
        }

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist feedback store: {e}")

    def record_feedback(
        self,
        query: str,
        rating: str,  # 'up' or 'down'
        doc_name: Optional[str] = None,
        chunk_id: Optional[str] = None,
        citations: Optional[List[str]] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record feedback and adjust source citations weighting:
        - Thumbs Up: +0.12 permanent boost
        - Thumbs Down: -0.15 penalty
        """
        is_up = rating.lower() in ("up", "thumbs_up", "+1", "positive")
        delta = 0.12 if is_up else -0.15

        entry = {
            "timestamp": time.time(),
            "query": query,
            "rating": "thumbs_up" if is_up else "thumbs_down",
            "doc_name": doc_name,
            "chunk_id": chunk_id,
            "citations": citations or [],
            "comment": comment or ""
        }
        self._data["ratings"].append(entry)

        # Update source / chunk weights
        keys_to_update = []
        if chunk_id:
            keys_to_update.append(str(chunk_id))
        if doc_name:
            keys_to_update.append(str(doc_name))
        if citations:
            for c in citations:
                keys_to_update.append(str(c))

        for k in keys_to_update:
            curr = self._data["source_weights"].get(k, 0.0)
            self._data["source_weights"][k] = round(curr + delta, 3)

        # If negative feedback with comment or query, add to negative constraints
        if not is_up and (comment or query):
            directive = f"Avoid past issue for '{query}': {comment or 'Incorrect or ungrounded details.'}"
            if directive not in self._data["negative_constraints"]:
                self._data["negative_constraints"].append(directive)
                # Keep last 10 negative constraints
                self._data["negative_constraints"] = self._data["negative_constraints"][-10:]

        self._save()
        logger.info(f"Recorded feedback: {rating} for {keys_to_update} (delta: {delta})")
        return {"status": "success", "recorded_delta": delta, "total_ratings": len(self._data["ratings"])}

    def get_citation_boost(self, chunk_or_doc_key: str) -> float:
        """Get net score adjustment for a chunk or document key."""
        if not chunk_or_doc_key:
            return 0.0
        return self._data["source_weights"].get(str(chunk_or_doc_key), 0.0)

    def get_negative_constraints(self, max_constraints: int = 3) -> List[str]:
        """Get recent negative feedback constraints to steer LLM away from past errors."""
        return self._data["negative_constraints"][-max_constraints:]
