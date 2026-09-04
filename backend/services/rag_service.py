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
        generate_answer: bool = True, ollama_url: Optional[str] = None,
        processing_mode: str = "local", api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query RAG for relevant context and synthesize answer using Local Ollama or Turbo Cloud Server."""
        if not self.is_available:
            return {"results": [], "error": "RAG not available", "answer": None}

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
                        f"You are InsightRAG AI, a high-precision multimodal RAG assistant.\n"
                        f"Answer the user's question clearly and accurately using the provided document context below. Cite sources where possible.\n\n"
                        f"DOCUMENT CONTEXT:\n{context_str}\n\n"
                        f"USER QUESTION:\n{query}\n\n"
                        f"GROUNDED ANSWER:"
                    )
                else:
                    prompt = (
                        f"You are InsightRAG AI, an expert local AI assistant.\n"
                        f"Answer the user's query clearly and concisely:\n\n"
                        f"QUESTION: {query}\n\n"
                        f"ANSWER:"
                    )

                # =========================================================
                # 1. ADVANCE TURBO CLOUD / SERVER ACCELERATED MODE
                # =========================================================
                is_cloud_mode = (processing_mode in ["cloud", "turbo", "advance"]) or model.startswith(("groq", "gemini", "openai", "claude"))
                
                if is_cloud_mode:
                    try:
                        # 1A. Groq High-Speed Cloud Inference
                        if model.startswith("groq") or "groq" in processing_mode or not (model.startswith("gemini") or model.startswith("openai")):
                            g_key = api_key or os.getenv("GROQ_API_KEY")
                            g_model = model.split(":", 1)[1] if ":" in model else "llama-3.3-70b-versatile"
                            
                            if g_key:
                                with httpx.Client(timeout=60.0) as client:
                                    g_resp = client.post(
                                        "https://api.groq.com/openai/v1/chat/completions",
                                        headers={"Authorization": f"Bearer {g_key}", "Content-Type": "application/json"},
                                        json={
                                            "model": g_model,
                                            "messages": [
                                                {"role": "system", "content": "You are InsightRAG AI, a high-speed accurate RAG engine."},
                                                {"role": "user", "content": prompt}
                                            ],
                                            "temperature": 0.2,
                                        }
                                    )
                                    if g_resp.status_code == 200:
                                        data = g_resp.json()
                                        answer = data["choices"][0]["message"]["content"].strip()
                                        used_llm = True
                                        llm_model = f"⚡ Turbo Cloud ({g_model})"

                        # 1B. Google Gemini Cloud Inference
                        if not answer and (model.startswith("gemini") or "gemini" in processing_mode):
                            gem_key = api_key or os.getenv("GEMINI_API_KEY")
                            if gem_key:
                                with httpx.Client(timeout=60.0) as client:
                                    gem_resp = client.post(
                                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gem_key}",
                                        json={"contents": [{"parts": [{"text": prompt}]}]}
                                    )
                                    if gem_resp.status_code == 200:
                                        data = gem_resp.json()
                                        answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                                        used_llm = True
                                        llm_model = "⚡ Gemini 1.5 Flash (Cloud)"

                        # 1C. OpenAI GPT Cloud Inference
                        if not answer and (model.startswith("openai") or "openai" in processing_mode):
                            oai_key = api_key or os.getenv("OPENAI_API_KEY")
                            if oai_key:
                                with httpx.Client(timeout=60.0) as client:
                                    oai_resp = client.post(
                                        "https://api.openai.com/v1/chat/completions",
                                        headers={"Authorization": f"Bearer {oai_key}", "Content-Type": "application/json"},
                                        json={
                                            "model": "gpt-4o-mini",
                                            "messages": [{"role": "user", "content": prompt}],
                                            "temperature": 0.2
                                        }
                                    )
                                    if oai_resp.status_code == 200:
                                        data = oai_resp.json()
                                        answer = data["choices"][0]["message"]["content"].strip()
                                        used_llm = True
                                        llm_model = "⚡ OpenAI GPT-4o-mini (Cloud)"
                    except Exception as cloud_err:
                        logger.warning(f"Cloud turbo processing failed ({cloud_err}), falling back to local...")

                # =========================================================
                # 2. 100% LOCAL ON-DEVICE MODE (OLLAMA ENGINE)
                # =========================================================
                if not answer:
                    try:
                        from .ollama_manager import get_working_ollama_host, get_installed_models
                        import asyncio

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

                        local_model = model if not model.startswith(("groq", "gemini", "openai")) else "llama3.2:3b"
                        candidate_models = [local_model, "llama3.2:3b", "llama3.2", "qwen2.5:3b", "mistral:latest"]
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
                                llm_model = f"💻 Local Ollama ({successful_model})"
                            elif results:
                                answer = (
                                    f"💻 [Local Mode Active]\n\n"
                                    f"Here are the top retrieved passages from your indexed documents:\n\n"
                                    + "\n\n".join(
                                        f"📄 [{i+1}] {r.get('text', '')[:500]}"
                                        for i, r in enumerate(results[:3])
                                    )
                                )
                    except Exception as ollama_err:
                        logger.info(f"Local Ollama generation unavailable ({ollama_err}).")
                        if results:
                            answer = (
                                f"📄 Relevant passages from your local documents:\n\n"
                                + "\n\n".join(
                                    f"[{i+1}] {r.get('text', '')[:500]}"
                                    for i, r in enumerate(results[:3])
                                )
                            )

            # Visual Snippet Extraction for Diagram / Region of Interest Cropping
            visual_snippet = None
            if results:
                top_hit = results[0]
                meta = top_hit.get("metadata", {})
                doc_name = meta.get("file_name") or meta.get("source") or meta.get("document_name")
                
                # If not explicitly in metadata, check uploaded files in ./uploads
                if not doc_name:
                    uploads_dir = Path("./uploads")
                    if uploads_dir.exists():
                        files = [f.name for f in uploads_dir.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]]
                        if files:
                            doc_name = files[0]

                page_num = meta.get("page_number") or meta.get("page") or 1
                
                visual_triggers = ["diagram", "figure", "chart", "flowchart", "image", "photo", "structure", "circuit", "anatomy", "graph", "step", "part", "region", "section", "show", "draw"]
                is_visual_query = any(w in query.lower() for w in visual_triggers) or any(w in top_hit.get("text", "").lower() for w in ["figure", "diagram", "fig.", "chart"])
                
                if doc_name and (is_visual_query or Path(doc_name).suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]):
                    crop_url = f"/api/v1/rag/crop?doc_name={doc_name}&page={page_num}"
                    caption = f"Focused Visual Crop — Page {page_num} ({doc_name})"
                    visual_snippet = {
                        "has_image": True,
                        "crop_url": crop_url,
                        "doc_name": doc_name,
                        "page": page_num,
                        "caption": caption
                    }

            return {
                "results": results,
                "query": query,
                "total_results": len(results),
                "answer": answer,
                "used_llm": used_llm,
                "llm_model": llm_model,
                "visual_snippet": visual_snippet,
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
