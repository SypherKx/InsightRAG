"""
RAG Service — Manages document ingestion and retrieval.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

SRC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

logger = logging.getLogger(__name__)

# RAG is optional — gracefully degrade if dependencies missing
_RAG_AVAILABLE = False
_rag_pipeline = None

try:
    from rag.pipeline import RAGPipeline, create_pipeline
    _RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG module not available: {e}. RAG features disabled.")


import os
import httpx

class RAGService:
    """Manages RAG document ingestion and retrieval."""

    def __init__(self, index_path: str = "./rag_index", org_id: str = "default"):
        self.index_path = index_path
        self.org_id = org_id
        self.pipeline = None

        if _RAG_AVAILABLE:
            try:
                self.pipeline = create_pipeline(
                    index_path=index_path,
                    org_id=org_id,
                )
                logger.info("RAG pipeline initialized")
            except Exception as e:
                logger.warning(f"RAG pipeline init failed: {e}")

    @property
    def is_available(self) -> bool:
        return self.pipeline is not None

    def ingest_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Ingest documents into RAG index."""
        if not self.is_available:
            return {"error": "RAG not available", "documents_ingested": 0}

        try:
            stats = self.pipeline.ingest_and_index(file_paths)
            return stats
        except Exception as e:
            logger.error(f"RAG ingestion failed: {e}")
            return {"error": str(e), "documents_ingested": 0}

    def query(
        self, query: str, top_k: int = 5, min_score: float = 0.0,
        filters: Optional[Dict] = None, model: str = "llama3.2:3b",
        generate_answer: bool = True, ollama_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query RAG for relevant context and synthesize answer using local Ollama model."""
        if not self.is_available:
            return {"results": [], "error": "RAG not available", "answer": None}

        # Lock model to llama3.2:3b regardless of what frontend sends
        model = "llama3.2:3b"

        try:
            results = self.pipeline.query(
                query=query,
                top_k=top_k,
                min_score=min_score,
                filters=filters,
            )

            answer = None
            used_llm = False
            llm_model = None

            if generate_answer:
                if results:
                    # Build context from retrieved FAISS passages
                    context_texts = [f"[{i+1}] {r.get('text', '')}" for i, r in enumerate(results)]
                    context_str = "\n\n".join(context_texts)
                    prompt = (
                        f"You are a helpful AI assistant. Answer the user's question using the provided document context below.\n\n"
                        f"CONTEXT:\n{context_str}\n\n"
                        f"QUESTION:\n{query}\n\n"
                        f"ANSWER:"
                    )
                else:
                    # General prompt fallback when no document chunks match
                    prompt = (
                        f"You are InsightRAG AI, an expert local AI assistant for Healthcare & Education.\n"
                        f"Answer the user's query clearly and concisely:\n\n"
                        f"QUESTION: {query}\n\n"
                        f"ANSWER:"
                    )

                try:
                    from .ollama_manager import get_working_ollama_host, get_installed_models
                    import asyncio

                    # Get working host and installed models using modular helper
                    working_endpoint = ollama_url
                    if not working_endpoint:
                        try:
                            working_endpoint = asyncio.run(get_working_ollama_host(auto_start=True))
                        except Exception:
                            working_endpoint = "http://127.0.0.1:11434"

                    if not working_endpoint:
                        working_endpoint = "http://127.0.0.1:11434"

                    try:
                        installed_models = asyncio.run(get_installed_models())
                    except Exception:
                        installed_models = []

                    # Build list of candidate models to try
                    candidate_models = [model]
                    base = model.split(":")[0] if ":" in model else model
                    if base not in candidate_models:
                        candidate_models.append(base)
                    
                    for inst in installed_models:
                        if inst not in candidate_models:
                            candidate_models.append(inst)

                    with httpx.Client(timeout=120.0) as client:
                        resp = None
                        for cand in candidate_models:
                            try:
                                res = client.post(
                                    f"{working_endpoint}/api/generate",
                                    json={"model": cand, "prompt": prompt, "stream": False}
                                )
                                if res.status_code == 200:
                                    resp = res
                                    successful_model = cand
                                    break
                                elif res.status_code == 404:
                                    logger.warning(f"Ollama model '{cand}' not found on endpoint {working_endpoint}")
                            except httpx.ConnectError:
                                logger.warning(f"Cannot connect to Ollama at {working_endpoint}")
                                break
                            except Exception as req_err:
                                logger.warning(f"Ollama request failed for model '{cand}': {req_err}")

                        if resp and resp.status_code == 200:
                            data = resp.json()
                            answer = data.get("response", "").strip()
                            used_llm = True
                            llm_model = successful_model
                        elif results:
                            # Fallback: synthesize a readable answer from FAISS passages
                            answer = (
                                f"⚠ Ollama ({model}) is not available. Make sure Ollama is running "
                                f"(ollama serve) and the model is pulled (ollama pull {model}).\n\n"
                                f"Here are the most relevant passages from your documents:\n\n"
                                + "\n\n".join(
                                    f"📄 [{i+1}] {r.get('text', '')[:500]}"
                                    for i, r in enumerate(results[:3])
                                )
                            )
                except Exception as ollama_err:
                    logger.info(f"Ollama generation unavailable ({ollama_err}).")
                    if results:
                        answer = (
                            f"⚠ Could not reach Ollama for LLM synthesis.\n\n"
                            f"Here are the most relevant passages from your documents:\n\n"
                            + "\n\n".join(
                                f"📄 [{i+1}] {r.get('text', '')[:500]}"
                                for i, r in enumerate(results[:3])
                            )
                        )

            return {
                "results": results,
                "query": query,
                "total_results": len(results),
                "answer": answer,
                "used_llm": used_llm,
                "llm_model": llm_model,
            }
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {"results": [], "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG index statistics and list of uploaded files."""
        if not self.is_available:
            return {"status": "unavailable", "total_vectors": 0, "files": []}
        try:
            stats = self.pipeline.get_stats()
            uploads_dir = Path("./uploads")
            files_info = []
            if uploads_dir.exists():
                for f in uploads_dir.iterdir():
                    if f.is_file():
                        files_info.append({
                            "name": f.name,
                            "size_bytes": f.stat().st_size,
                            "extension": f.suffix.lower()
                        })
            stats["files"] = files_info
            return stats
        except Exception as e:
            return {"status": "error", "error": str(e), "total_vectors": 0, "files": []}

    def clear(self) -> Dict[str, Any]:
        """Clear all documents and vectors from the RAG index."""
        if not self.is_available:
            return {"status": "unavailable"}
        try:
            self.pipeline.clear()
            uploads_dir = Path("./uploads")
            if uploads_dir.exists():
                for f in uploads_dir.iterdir():
                    if f.is_file():
                        try:
                            f.unlink(missing_ok=True)
                        except Exception:
                            pass
            return {"status": "cleared", "total_vectors": 0, "files": []}
        except Exception as e:
            logger.error(f"RAG clear failed: {e}")
            return {"status": "error", "error": str(e)}
