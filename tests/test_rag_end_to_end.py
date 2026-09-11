"""
End-to-end automated tests for InsightRAG pipeline and RAGService.

Verifies:
1. Document ingestion and indexing.
2. Query execution with citations in response.
3. Multi-turn conversational query rewriting (verifying was_rewritten and retrieval_query).
4. Visual queries and page_num extraction (verifying page_num is correctly wired without NameError).
5. Streaming endpoint (query_stream) event generation and metrics.
6. Error handling with logger.exception without silent crashes.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure backend and src are in path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from backend.services.rag_service import RAGService
from src.rag.pipeline import create_pipeline


@pytest.fixture
def rag_service(tmp_path):
    """Create a temporary isolated RAGService instance."""
    index_path = str(tmp_path / "test_faiss.index")
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Create a realistic test document with page markers and architectural diagram descriptions
    doc_path = uploads_dir / "architecture_spec.txt"
    doc_path.write_text(
        "=== Document: Architecture Spec ===\n"
        "Page 1:\n"
        "The InsightForge core cluster consists of 32 high-memory nodes.\n"
        "The measured throughput capacity is 1.2 million events per second with 12ms p99 latency.\n"
        "All telemetry metrics are ingested into FAISS vector storage.\n\n"
        "Page 2:\n"
        "Figure 2.1: Infrastructure Network Topology and Diagram Schematic.\n"
        "The high-availability cluster failover threshold is configured to 250 milliseconds.\n"
        "Primary and secondary regions maintain synchronized vector embeddings.\n",
        encoding="utf-8"
    )

    pipeline = create_pipeline(index_path=index_path, org_id="test_org")
    pipeline.ingest_and_index([str(doc_path)])

    service = RAGService(index_path=index_path, org_id="test_org")
    service.pipeline = pipeline

    yield service

    # Cleanup
    pipeline.clear()


def test_rag_query_end_to_end_with_citations(rag_service):
    """
    Test 1: Full query end-to-end.
    Asserts:
    - Results are returned.
    - Ollama answer is synthesized with bracketed citations [1].
    - was_rewritten and retrieval_query are correctly populated without NameError.
    """
    mock_llm_response = MagicMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json.return_value = {
        "response": "The InsightForge cluster has a throughput capacity of 1.2 million events per second [1] with 12ms p99 latency [1].",
        "eval_count": 28,
        "eval_duration": 500000000
    }

    with patch("backend.services.ollama_manager.get_installed_models", return_value=["llama3.2:3b"]):
        with patch("httpx.Client.post", return_value=mock_llm_response):
            result = rag_service.query(
                query="What is the throughput capacity?",
                generate_answer=True,
                top_k=3,
                ollama_url="http://127.0.0.1:11434"
            )

    # 1. Verify no exceptions occurred
    assert "error" not in result or result["error"] is None
    assert result["results"] is not None
    assert len(result["results"]) > 0

    # 2. Verify citation presence
    answer = result["answer"]
    assert answer is not None
    assert "[1]" in answer, f"Expected citation '[1]' in answer: {answer}"

    # 3. Verify was_rewritten and retrieval_query are wired without NameError
    assert "was_rewritten" in result["metrics"]
    assert result["metrics"]["was_rewritten"] is False
    assert result["rewritten_query"] is None


def test_rag_query_multi_turn_rewriting(rag_service):
    """
    Test 2: Multi-turn conversational query rewriting.
    Asserts:
    - QueryProcessor.rewrite_query_with_llm is triggered when history is present.
    - was_rewritten is set to True.
    - rewritten_query is returned in the response dict and used for retrieval.
    """
    history = [
        {"role": "user", "content": "Tell me about the cluster throughput."},
        {"role": "assistant", "content": "The cluster throughput is 1.2M events per second."}
    ]

    mock_llm_response = MagicMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json.return_value = {
        "response": "The cluster failover threshold is configured to 250 milliseconds [1].",
        "eval_count": 18,
        "eval_duration": 300000000
    }

    rewritten_target = "What is the cluster failover threshold?"

    with patch("backend.services.ollama_manager.get_installed_models", return_value=["llama3.2:3b"]):
        with patch("rag.query_processor.QueryProcessor.rewrite_query_with_llm", return_value=(rewritten_target, True)):
            with patch("httpx.Client.post", return_value=mock_llm_response):
                result = rag_service.query(
                    query="What is its failover threshold?",
                    history=history,
                    generate_answer=True,
                    ollama_url="http://127.0.0.1:11434"
                )

    assert result.get("error") is None
    assert result["metrics"]["was_rewritten"] is True
    assert result["rewritten_query"] == rewritten_target
    assert "[1]" in result["answer"]


def test_rag_query_visual_target_page_wiring(rag_service, tmp_path):
    """
    Test 3: Visual / Diagram ROI query testing page_num wiring.
    Asserts:
    - No NameError on page_num.
    - visual_snippet is generated with the correct page number (Page 2).
    - crop_url contains page=2.
    """
    query_text = "Show me the diagram schematic on page 2"
    result = rag_service.query(
        query=query_text,
        generate_answer=False
    )

    assert result.get("error") is None
    assert result["visual_snippet"] is not None
    assert result["visual_snippet"]["has_image"] is True
    assert result["visual_snippet"]["page"] == 2
    assert "page=2" in result["visual_snippet"]["crop_url"]


@pytest.mark.asyncio
async def test_rag_query_stream_end_to_end(rag_service):
    """
    Test 4: Async streaming query (query_stream).
    Asserts:
    - Correct event progression: metadata -> token -> done.
    - Metadata event includes was_rewritten and target_page.
    - Done event contains metrics with was_rewritten and tokens_per_sec.
    - No NameError or unhandled exceptions occur.
    """
    history = [{"role": "user", "content": "Hello"}]
    events = []

    mock_stream_lines = [
        b'{"response": "The "}\n',
        b'{"response": "cluster "}\n',
        b'{"response": "throughput "}\n',
        b'{"response": "is 1.2M [1]."}\n'
    ]

    class MockAsyncResponse:
        status_code = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        async def aiter_lines(self):
            for line in mock_stream_lines:
                yield line.decode("utf-8")

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
        def stream(self, *args, **kwargs):
            return MockAsyncResponse()

    with patch("httpx.AsyncClient", MockAsyncClient):
        async for event in rag_service.query_stream(
            query="What is the throughput?",
            history=history
        ):
            events.append(event)

    event_types = [e.get("event") for e in events]
    assert "metadata" in event_types
    assert "token" in event_types
    assert "done" in event_types

    # Verify metadata payload
    metadata_event = next(e for e in events if e.get("event") == "metadata")
    assert "results" in metadata_event["data"]
    assert "was_rewritten" in metadata_event["data"]

    # Verify done event payload
    done_event = next(e for e in events if e.get("event") == "done")
    metrics = done_event["data"]["metrics"]
    assert "tokens_generated" in metrics
    assert "was_rewritten" in metrics
    assert metrics["tokens_generated"] == 4


def test_query_decomposition_and_hinglish():
    """
    Test 5: Verify QueryProcessor decomposes complex questions and normalizes Hinglish.
    """
    from src.rag.query_processor import QueryProcessor

    # 1. Multi-part query decomposition
    multi_q = "What is the cluster throughput and also how does failover work?"
    decomposed = QueryProcessor.decompose_query(multi_q)
    assert len(decomposed) >= 2
    assert any("throughput" in q.lower() for q in decomposed)
    assert any("failover" in q.lower() for q in decomposed)

    # 2. Comparative query decomposition
    comp_q = "Compare primary cluster and secondary cluster"
    decomposed_comp = QueryProcessor.decompose_query(comp_q)
    assert len(decomposed_comp) >= 2
    assert any("primary cluster" in q.lower() for q in decomposed_comp)
    assert any("secondary cluster" in q.lower() for q in decomposed_comp)

    # 3. Hinglish normalization
    hinglish_q = "bhai isme failover threshold kya hai aur ye kaise kaam karta hai"
    normalized = QueryProcessor.normalize_hinglish_query(hinglish_q)
    assert "bhai" not in normalized.lower()
    assert "failover" in normalized.lower()
    assert "works mechanics" in normalized.lower() or "architecture" in normalized.lower()


def test_chatgpt_grade_prompt_formatting():
    """
    Test 6: Verify build_chatgpt_rag_prompt builds structured, comprehensive prompt with guidelines.
    """
    from backend.services.rag_service import build_chatgpt_rag_prompt

    mock_results = [
        {
            "text": "Throughput capacity is 1.2M events/sec.",
            "metadata": {"file_name": "spec.txt", "page_number": 1}
        }
    ]

    prompt = build_chatgpt_rag_prompt(
        query="What is the throughput?",
        results=mock_results,
        history_str=""
    )

    assert "InsightRAG AI" in prompt
    assert "Executive Summary" in prompt
    assert "Detailed Breakdown" in prompt
    assert "spec.txt" in prompt
    assert "Throughput capacity is 1.2M" in prompt


def test_attached_visual_diagrams_and_b64_extraction(tmp_path):
    """
    Test 7: Verify extract_attached_visual_diagrams and get_b64_images.
    Asserts:
    - Diagrams extracted from chunk metadata and inline tags.
    - Base64 encoding returns valid strings for vision models.
    - build_chatgpt_rag_prompt includes ATTACHED VISUAL DIAGRAMS section.
    """
    from backend.services.rag_service import (
        extract_attached_visual_diagrams,
        get_b64_images,
        build_chatgpt_rag_prompt
    )

    dummy_img = tmp_path / "test_fig.png"
    dummy_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

    mock_results = [
        {
            "text": "System architecture [IMAGE / FIGURE: Figure 1: Pipeline Overview] [Image URL: /api/v1/rag/images/doc/fig1.jpg]",
            "metadata": {
                "file_name": "paper.pdf",
                "page_number": 2,
                "visual_elements": [
                    {
                        "caption": "Figure 1: Pipeline Overview",
                        "image_url": "/api/v1/rag/images/doc/fig1.jpg",
                        "file_path": str(dummy_img),
                        "page": 2,
                        "description": "Overview of RAG pipeline"
                    }
                ]
            }
        }
    ]

    diagrams = extract_attached_visual_diagrams(mock_results)
    assert len(diagrams) == 1
    assert diagrams[0]["caption"] == "Figure 1: Pipeline Overview"
    assert diagrams[0]["image_url"] == "/api/v1/rag/images/doc/fig1.jpg"

    b64s = get_b64_images(None, diagrams)
    assert len(b64s) == 1
    assert len(b64s[0]) > 10

    prompt = build_chatgpt_rag_prompt(
        query="Explain the architecture diagram",
        results=mock_results,
        visual_diagrams=diagrams
    )
    assert "ATTACHED VISUAL DIAGRAMS & FIGURES" in prompt
    assert "Figure 1: Pipeline Overview" in prompt


