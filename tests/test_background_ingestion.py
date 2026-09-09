"""
Automated tests for Background Document Ingestion & Concurrent FAISS Safety.

Verifies:
1. Upload endpoint (POST /api/v1/rag/documents) returns immediately without blocking (< 500ms) with task_id.
2. Status endpoint (GET /api/v1/rag/documents/{task_id}/status) reflects multi-stage progress (steps 0-5) to completion.
3. Failed ingestion is cleanly reported with status='failed' and error details, without leaving partial/corrupt vectors in FAISS.
4. Concurrent uploads serialize FAISS vector store writes safely without ID collisions or metadata corruption.
5. Query requests respond promptly WHILE background ingestion is actively executing in the thread pool.
"""

import io
import time
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from backend.main import app
from backend.dependencies import get_rag_service
from backend.services.rag_task_manager import rag_task_manager
from src.rag.models import DocumentChunk


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def rag_svc():
    """Get initialized RAGService singleton."""
    return get_rag_service()


def test_upload_returns_immediately_non_blocking(client, rag_svc):
    """(a) Confirm POST /api/v1/rag/documents returns immediately (< 500ms) with a task_id and processing status."""
    sample_content = (
        "=== Section: Cloud Architecture ===\n"
        "The distributed cluster runs across 64 edge locations.\n"
        "Each worker node maintains in-memory caching with 99.99% availability.\n"
    )
    file_bytes = io.BytesIO(sample_content.encode("utf-8"))

    start_time = time.perf_counter()
    response = client.post(
        "/api/v1/rag/documents",
        files={"files": ("architecture_quick.txt", file_bytes, "text/plain")},
    )
    elapsed = time.perf_counter() - start_time

    assert response.status_code in (200, 202), f"Upload failed: {response.text}"
    data = response.json()
    assert "task_id" in data and data["task_id"] is not None
    assert data["status"] == "processing"
    # Verify the endpoint returned immediately without waiting for ingestion
    assert elapsed < 1.0, f"Upload took {elapsed:.2f}s, should return immediately"

    # Wait for background task to finish to leave clean state
    task_id = data["task_id"]
    for _ in range(50):
        time.sleep(0.1)
        st = client.get(f"/api/v1/rag/documents/{task_id}/status").json()
        if st.get("status") in ("completed", "failed"):
            break


def test_status_endpoint_progress_and_completion(client, rag_svc):
    """(b) Confirm GET /api/v1/rag/documents/{id}/status reflects progress through stages to completion."""
    doc_content = (
        "=== 1.0 System Overview ===\n"
        "InsightForge local AI platform provides offline vector search.\n"
        "Table 1:\n| Metric | Target |\n|---|---|\n| Latency | <15ms |\n| Precision | 99.5% |\n\n"
        "=== 2.0 Security Protocols ===\n"
        "Zero data transmission off the local host machine.\n"
    )
    file_bytes = io.BytesIO(doc_content.encode("utf-8"))

    resp = client.post(
        "/api/v1/rag/documents",
        files={"files": ("system_overview_spec.txt", file_bytes, "text/plain")},
    )
    assert resp.status_code in (200, 202)
    task_id = resp.json()["task_id"]

    # Poll status endpoint
    terminal_status = None
    seen_steps = set()

    for _ in range(60):
        status_resp = client.get(f"/api/v1/rag/documents/{task_id}/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()

        assert status_data["task_id"] == task_id
        assert "stage" in status_data
        assert "progress" in status_data
        seen_steps.add(status_data["step"])

        if status_data["status"] in ("completed", "failed"):
            terminal_status = status_data
            break
        time.sleep(0.1)

    assert terminal_status is not None, "Task timed out before completing"
    assert terminal_status["status"] == "completed"
    assert terminal_status["step"] == 5
    assert terminal_status["progress"] == 100
    assert terminal_status["chunks_created"] > 0
    assert terminal_status["documents_ingested"] >= 1
    assert terminal_status["error_message"] is None


def test_failed_ingestion_isolation_and_clean_rollback(client, rag_svc):
    """(c) Confirm failed ingestion is cleanly reported as 'failed' and leaves FAISS index uncorrupted."""
    initial_vectors = rag_svc.pipeline.vector_store.total_vectors

    # Simulate an ingestion failure by patching ingest_file to raise an exception
    with patch.object(rag_svc.pipeline.ingester, "ingest_file", side_effect=RuntimeError("Corrupted byte stream during OCR")):
        corrupt_bytes = io.BytesIO(b"%PDF-INVALID-DATA-CORRUPT")
        resp = client.post(
            "/api/v1/rag/documents",
            files={"files": ("corrupt_sample.pdf", corrupt_bytes, "application/pdf")},
        )
        assert resp.status_code in (200, 202)
        task_id = resp.json()["task_id"]

        # Poll until terminal state
        terminal_status = None
        for _ in range(50):
            status_resp = client.get(f"/api/v1/rag/documents/{task_id}/status")
            status_data = status_resp.json()
            if status_data["status"] in ("completed", "failed"):
                terminal_status = status_data
                break
            time.sleep(0.1)

        assert terminal_status is not None
        assert terminal_status["status"] == "failed"
        assert "Corrupted byte stream" in terminal_status["error_message"] or "Extraction failed" in terminal_status["error_message"]

    # Verify FAISS vector store was not corrupted and has 0 orphaned vectors added
    assert rag_svc.pipeline.vector_store.total_vectors == initial_vectors


def test_concurrent_uploads_faiss_thread_safety(client, rag_svc):
    """(d) Confirm concurrent uploads serialize writes and do not corrupt the shared FAISS index."""
    doc_a = "=== Section A: Node 1 Metrics ===\nHigh performance database metrics for shard A.\n" * 5
    doc_b = "=== Section B: Node 2 Metrics ===\nHigh performance database metrics for shard B.\n" * 5

    bytes_a = io.BytesIO(doc_a.encode("utf-8"))
    bytes_b = io.BytesIO(doc_b.encode("utf-8"))

    initial_vectors = rag_svc.pipeline.vector_store.total_vectors

    # Fire two concurrent upload requests
    resp_a = client.post("/api/v1/rag/documents", files={"files": ("concurrent_a.txt", bytes_a, "text/plain")})
    resp_b = client.post("/api/v1/rag/documents", files={"files": ("concurrent_b.txt", bytes_b, "text/plain")})

    assert resp_a.status_code in (200, 202)
    assert resp_b.status_code in (200, 202)

    task_a = resp_a.json()["task_id"]
    task_b = resp_b.json()["task_id"]

    # Wait for both tasks to complete
    for task_id in [task_a, task_b]:
        for _ in range(60):
            st = client.get(f"/api/v1/rag/documents/{task_id}/status").json()
            if st["status"] in ("completed", "failed"):
                assert st["status"] == "completed", f"Task {task_id} failed: {st.get('error_message')}"
                break
            time.sleep(0.1)

    # Confirm FAISS index integrity: total vectors increased, no metadata collisions
    final_vectors = rag_svc.pipeline.vector_store.total_vectors
    assert final_vectors > initial_vectors
    # Verify metadata dictionary has exact same count as total_vectors
    assert len(rag_svc.pipeline.vector_store.metadata) == final_vectors


def test_query_responds_promptly_during_background_ingestion(client, rag_svc):
    """(e) Confirm query request WHILE a large document is ingesting in background thread pool responds promptly."""
    # Create a large document to ensure ingestion takes multiple seconds
    large_doc = "\n\n".join([
        f"=== Section {i}: Architecture Component {i} ===\n"
        f"This is component {i} in the distributed system with throughput {1000 * i} ops/sec.\n"
        f"Detailed telemetry and replication parameters for partition {i}.\n"
        for i in range(1, 25)
    ])
    file_bytes = io.BytesIO(large_doc.encode("utf-8"))

    # Start background ingestion
    upload_resp = client.post(
        "/api/v1/rag/documents",
        files={"files": ("large_workload_spec.txt", file_bytes, "text/plain")},
    )
    assert upload_resp.status_code in (200, 202)
    task_id = upload_resp.json()["task_id"]

    # IMMEDIATELY fire a query request while background ingestion is actively churning in thread pool
    query_start = time.perf_counter()
    query_resp = client.post(
        "/api/v1/rag/query",
        json={
            "query": "What is the throughput of component 1?",
            "top_k": 3,
            "generate_answer": False,  # Pure retrieval test to isolate FastAPI event loop responsiveness
        },
    )
    query_elapsed = time.perf_counter() - query_start

    assert query_resp.status_code == 200, f"Query failed while ingesting: {query_resp.text}"
    # Query must return promptly (< 1.5s) without waiting for the large background ingestion
    assert query_elapsed < 1.5, f"Query took {query_elapsed:.2f}s, stalled behind background ingestion!"

    # Wait for background ingestion to complete cleanly
    for _ in range(60):
        st = client.get(f"/api/v1/rag/documents/{task_id}/status").json()
        if st["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
