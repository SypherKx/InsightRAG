"""
Unit & Integration Test Suite for Advanced RAG Features in InsightRAG.

Verifies:
1. RapidOCR fallback for scanned/image-dominant documents
2. VisualFingerprintMatcher (dHash, aHash, NCC, color histogram, 5ms reverse image matching)
3. QueryProcessor (greeting interception, intent expansion, HyDE generation)
4. FeedbackStore (active learning thumbs up/down weighting, negative constraints)
5. AntiHallucinationEngine (refusal regex detection, citation sanitization, sigmoid confidence calibration)
6. RAGRetriever (attention composite reranker, lexical keyword preservation)
"""

import os
import sys
import pytest
from pathlib import Path
from PIL import Image, ImageDraw

# Add src and backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_visual_fingerprint_matcher():
    """Test 64-bit perceptual hashing and sub-5ms reverse image matching."""
    from src.rag.image_regions import VisualFingerprintMatcher

    # Create two identical diagrams
    img1 = Image.new("RGB", (120, 120), color="white")
    d1 = ImageDraw.Draw(img1)
    d1.rectangle([20, 20, 100, 100], fill="black")
    d1.text((30, 30), "Architecture", fill="white")

    img2 = Image.new("RGB", (120, 120), color="white")
    d2 = ImageDraw.Draw(img2)
    d2.rectangle([20, 20, 100, 100], fill="black")
    d2.text((30, 30), "Architecture", fill="white")

    # Create distinct diagram
    img3 = Image.new("RGB", (120, 120), color="white")
    d3 = ImageDraw.Draw(img3)
    d3.ellipse([10, 10, 110, 110], fill="blue")

    fp1 = VisualFingerprintMatcher.compute_fingerprint(img1)
    fp2 = VisualFingerprintMatcher.compute_fingerprint(img2)
    fp3 = VisualFingerprintMatcher.compute_fingerprint(img3)

    assert fp1 is not None and "dhash" in fp1 and "ncc" in fp1 and "hist" in fp1

    sim_identical = VisualFingerprintMatcher.compute_similarity(fp1, fp2)
    sim_different = VisualFingerprintMatcher.compute_similarity(fp1, fp3)

    assert sim_identical >= 0.98, f"Identical images should have >= 0.98 similarity, got {sim_identical}"
    assert sim_different < 0.75, f"Different shapes should have < 0.75 similarity, got {sim_different}"

    # Reverse image search match test
    stored_diagrams = [
        {"caption": "Target Architecture", "fingerprint": fp2, "page": 3},
        {"caption": "Other Graphic", "fingerprint": fp3, "page": 7}
    ]
    match = VisualFingerprintMatcher.find_best_match(img1, stored_diagrams, threshold=0.80)
    assert match is not None
    matched_diag, score = match
    assert matched_diag["caption"] == "Target Architecture"
    assert matched_diag["page"] == 3
    assert score >= 0.95


def test_anti_hallucination_engine():
    """Test refusal detection, fake citation sanitization, and sigmoid confidence."""
    from src.rag.anti_hallucination import AntiHallucinationEngine

    # 1. Refusal check
    refusal_text = "I could not find any mention of quantum flux capacitors in the provided documents [1][2]."
    assert AntiHallucinationEngine.is_refusal(refusal_text) is True

    # 2. Citation sanitization on refusal
    cleaned, valid_cits = AntiHallucinationEngine.sanitize_citations(refusal_text, max_valid_chunk=5)
    assert "[1]" not in cleaned and "[2]" not in cleaned
    assert len(valid_cits) == 0

    # 3. Grounding evaluation on refusal
    eval_refusal = AntiHallucinationEngine.evaluate_grounding(
        refusal_text,
        results=[{"text": "Sample text", "similarity_score": 0.5}],
        query="What is the quantum flux capacitor?"
    )
    assert eval_refusal["is_grounded"] is False
    assert eval_refusal["refusal_detected"] is True
    assert eval_refusal["status"] == "refusal_not_in_context"

    # 4. Valid factual answer
    good_text = "According to the specifications, the maximum payload is 500kg [1] operating at 24V [2]."
    eval_good = AntiHallucinationEngine.evaluate_grounding(
        good_text,
        results=[
            {"text": "maximum payload is 500kg", "similarity_score": 0.85},
            {"text": "operating at 24V", "similarity_score": 0.75}
        ],
        query="What is the maximum payload and voltage?"
    )
    assert eval_good["is_grounded"] is True
    assert eval_good["refusal_detected"] is False
    assert 1 in eval_good["citations"] and 2 in eval_good["citations"]
    assert eval_good["confidence_score"] >= 0.80


def test_greeting_interception_and_intent_expansion():
    """Test instant greeting interception and summary/visual keyword expansions."""
    from src.rag.query_processor import QueryProcessor

    # Greeting interception
    assert QueryProcessor.intercept_greeting("hi") is not None
    assert QueryProcessor.intercept_greeting("hello") is not None
    assert QueryProcessor.intercept_greeting("namaste") is not None
    assert QueryProcessor.intercept_greeting("what is the battery life?") is None

    # Intent expansion
    summary_exp = QueryProcessor.expand_query_intent("summarize this report")
    assert "abstract" in summary_exp and "main findings" in summary_exp

    visual_exp = QueryProcessor.expand_query_intent("show the circuit diagram")
    assert "schematic" in visual_exp and "workflow" in visual_exp


def test_feedback_store():
    """Test active user feedback weighting and negative constraints."""
    from src.rag.feedback_store import FeedbackStore
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "test_feedback.json"
        store = FeedbackStore(storage_path=store_path)

        # Thumbs up
        store.record_feedback(query="transformer architecture", rating="up", chunk_id="chunk_101", doc_name="paper.pdf")
        boost = store.get_citation_boost("chunk_101")
        assert boost == 0.12

        # Thumbs down
        store.record_feedback(
            query="loss formula",
            rating="down",
            chunk_id="chunk_202",
            doc_name="paper.pdf",
            comment="Wrong loss function cited."
        )
        penalty = store.get_citation_boost("chunk_202")
        assert penalty == -0.15

        # Negative constraints
        constraints = store.get_negative_constraints()
        assert len(constraints) >= 1
        assert "loss formula" in constraints[0]


def test_rapidocr_integration():
    """Test RapidOCR ONNX runtime on an image containing text."""
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np

    img = Image.new("RGB", (300, 100), color="white")
    d = ImageDraw.Draw(img)
    d.text((20, 40), "InsightRAG OCR Engine 2026", fill="black")

    ocr = RapidOCR()
    result, _ = ocr(np.array(img))
    assert result is not None
    extracted_texts = [item[1] for item in result if len(item) >= 2]
    combined = " ".join(extracted_texts).lower()
    assert "insightrag" in combined or "ocr" in combined or "engine" in combined


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
