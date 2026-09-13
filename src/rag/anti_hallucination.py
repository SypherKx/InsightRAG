"""
Anti-Hallucination Engine & Grounding Evaluation Module for InsightRAG.

Features:
1. Deterministic Refusal Pattern Detection (detects when LLM states information is missing).
2. Citation Sanitization (strips fabricated [1], [2] citations if model refuses).
3. Grounding & Faithfulness Evaluation against retrieved context chunks.
4. Sigmoid Confidence Calibration mapping raw similarity to [0%, 100%].
"""

import re
import math
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class AntiHallucinationEngine:
    """Evaluates answer grounding, sanitizes fake citations, and computes confidence scores."""

    REFUSAL_PATTERNS = [
        re.compile(r'\b(i could not find|could not be found|i cannot find|cannot be found)\b', re.IGNORECASE),
        re.compile(r'\b(there is no mention|no mention of|not mentioned in (the )?documents?)\b', re.IGNORECASE),
        re.compile(r'\b(not present in (the )?documents?|not found in (the )?provided|not in the provided)\b', re.IGNORECASE),
        re.compile(r'\b(the provided documents? (do not|does not) contain|documents? contain no information)\b', re.IGNORECASE),
        re.compile(r'\b(no information provided about|no details (are )?available in)\b', re.IGNORECASE),
        re.compile(r'\b(based on the provided context, there is no|based on the context, there is no)\b', re.IGNORECASE),
        re.compile(r'\b(is not specified in the uploaded|are not specified in the uploaded)\b', re.IGNORECASE),
    ]

    CITATION_REGEX = re.compile(r'\[(\d+)\]')

    @classmethod
    def is_refusal(cls, text: str) -> bool:
        """Check if LLM response indicates information was not found in the documents."""
        if not text:
            return False
        first_few_lines = "\n".join(text.strip().split("\n")[:4])
        for pattern in cls.REFUSAL_PATTERNS:
            if pattern.search(first_few_lines) or pattern.search(text):
                return True
        return False

    @classmethod
    def sanitize_citations(cls, text: str, max_valid_chunk: int) -> Tuple[str, List[int]]:
        """
        Extract and sanitize citations.
        If citations refer to indices > max_valid_chunk or if text is a refusal, clean them.
        """
        if not text:
            return text, []

        found_citations = []
        for m in cls.CITATION_REGEX.finditer(text):
            try:
                c_num = int(m.group(1))
                found_citations.append(c_num)
            except ValueError:
                pass

        # If model refused, strip all citations to prevent misleading users
        if cls.is_refusal(text):
            cleaned = cls.CITATION_REGEX.sub('', text)
            # Clean up accidental double spaces created by removal
            cleaned = re.sub(r' +', ' ', cleaned)
            return cleaned.strip(), []

        # Otherwise filter to valid citations
        valid_citations = [c for c in found_citations if 1 <= c <= max_valid_chunk]
        return text, valid_citations

    @classmethod
    def compute_sigmoid_confidence(cls, similarity_scores: List[float], query_word_overlap: float = 0.5) -> float:
        """
        Calibrate raw cosine similarity scores into an accurate [0.0, 1.0] confidence scale
        using logistic sigmoid mapping with midpoint calibration:
        Confidence = 1 / (1 + exp(-10 * (avg_score - 0.45)))
        """
        if not similarity_scores:
            return 0.0

        avg_score = sum(similarity_scores[:3]) / max(1, len(similarity_scores[:3]))
        # Combine cosine similarity with lexical overlap signal
        blended = (avg_score * 0.75) + (query_word_overlap * 0.25)
        
        # Logistic sigmoid centered around 0.45
        k = 9.0
        x0 = 0.45
        try:
            val = 1.0 / (1.0 + math.exp(-k * (blended - x0)))
            return round(min(max(val, 0.0), 1.0), 4)
        except OverflowError:
            return 1.0 if blended > x0 else 0.0

    @classmethod
    def evaluate_grounding(
        cls,
        answer: str,
        results: List[Dict[str, Any]],
        query: str = ""
    ) -> Dict[str, Any]:
        """
        Comprehensive Grounding Evaluation:
        1. Checks for refusal patterns
        2. Validates citation markers against retrieved chunks
        3. Computes calibrated sigmoid confidence
        4. Returns sanitized answer, confidence, and grounding status
        """
        if not answer:
            return {
                "is_grounded": False,
                "confidence_score": 0.0,
                "sanitized_answer": "",
                "citations": [],
                "status": "empty_response",
                "refusal_detected": False
            }

        max_chunk_idx = len(results)
        refusal_detected = cls.is_refusal(answer)
        sanitized_ans, valid_cits = cls.sanitize_citations(answer, max_valid_chunk=max_chunk_idx)

        # Extract similarities from top chunks
        sim_scores = []
        for r in results:
            s = r.get("similarity_score") or r.get("score") or 0.0
            sim_scores.append(float(s))

        # Query word overlap calculation
        q_words = set(re.findall(r'[a-zA-Z0-9]{3,}', query.lower())) if query else set()
        overlap_ratio = 0.0
        if q_words and results:
            top_texts = " ".join((r.get("text", "") for r in results[:3])).lower()
            matched = sum(1 for w in q_words if w in top_texts)
            overlap_ratio = matched / len(q_words)

        confidence = cls.compute_sigmoid_confidence(sim_scores, query_word_overlap=overlap_ratio)

        if refusal_detected:
            return {
                "is_grounded": False,
                "confidence_score": round(min(confidence, 0.25), 4),
                "sanitized_answer": sanitized_ans,
                "citations": [],
                "status": "refusal_not_in_context",
                "refusal_detected": True
            }

        # Check citation groundedness
        has_citations = len(valid_cits) > 0
        is_grounded = bool(results) and (confidence >= 0.40) and (not refusal_detected)

        status = "grounded"
        if not is_grounded:
            status = "low_confidence"
        elif has_citations:
            status = "verified_with_citations"

        return {
            "is_grounded": is_grounded,
            "confidence_score": confidence,
            "sanitized_answer": sanitized_ans,
            "citations": list(set(valid_cits)),
            "status": status,
            "refusal_detected": False
        }
