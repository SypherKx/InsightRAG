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

    def ingest_documents(
        self,
        file_paths: List[str],
        start_page: Optional[int] = None,
        end_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """Ingest documents into RAG index with optional page range."""
        if not self.is_available:
            return {"error": "RAG not available", "documents_ingested": 0}

        try:
            stats = self.pipeline.ingest_and_index(
                file_paths,
                start_page=start_page,
                end_page=end_page
            )
            return stats
        except Exception as e:
            logger.error(f"RAG ingestion failed: {e}")
            return {"error": str(e), "documents_ingested": 0}

    def query(
        self, query: str, top_k: int = 4, min_score: float = 0.0,
        filters: Optional[Dict] = None, model: str = "llama3.2:3b",
        generate_answer: bool = True, ollama_url: Optional[str] = None,
        processing_mode: str = "local", api_key: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Query RAG for relevant context and synthesize answer using Local Ollama or Turbo Cloud Server with multi-turn history."""
        if not self.is_available:
            return {"results": [], "error": "RAG not available", "answer": None}

        from rag.cache import LatencyProfiler
        from rag.query_processor import QueryProcessor

        profiler = LatencyProfiler()
        profiler.start_stage("query_processing_ms")

        # 1. Query Intent Classification & Conversational Rewriting
        intent_info = QueryProcessor.classify_intent(query)
        effective_top_k = min(top_k, intent_info.get("top_k", 4))
        retrieval_query, was_rewritten = QueryProcessor.rewrite_conversational_query(query, history)
        history_str, chat_history_turns = QueryProcessor.compress_conversation_history(history, max_turns=4)
        profiler.end_stage("query_processing_ms")

        try:
            # 2. Hybrid Retrieval + Reranking
            profiler.start_stage("retrieval_ms")
            results = self.pipeline.query(
                query=retrieval_query,
                top_k=effective_top_k,
                min_score=min_score,
                filters=filters,
            )
            profiler.end_stage("retrieval_ms")

            answer = None
            used_llm = False
            llm_model = None
            ttft_ms = 0.0
            tokens_generated = 0
            tokens_per_sec = 0.0

            if generate_answer:
                profiler.start_stage("prompt_prep_ms")
                if results:
                    # Compressed delimiter format
                    context_texts = [f"[{i+1}] {r.get('text', '').strip()}" for i, r in enumerate(results[:4])]
                    context_str = "\n\n".join(context_texts)
                    prompt = (
                        f"You are InsightRAG AI, a fast, grounded multimodal assistant. Answer concisely and accurately using the context below. "
                        f"If diagrams are referenced, explain them clearly as visual previews render beneath your response.\n\n"
                        f"{history_str}"
                        f"DOCUMENT CONTEXT:\n{context_str}\n\n"
                        f"QUESTION: {query}\n"
                        f"ANSWER:"
                    )
                else:
                    prompt = (
                        f"You are InsightRAG AI. Answer concisely and helpfully:\n\n"
                        f"{history_str}"
                        f"QUESTION: {query}\n"
                        f"ANSWER:"
                    )
                profiler.end_stage("prompt_prep_ms")

                # =========================================================
                # 1. ADVANCE TURBO CLOUD / SERVER ACCELERATED MODE
                # =========================================================
                is_cloud_mode = (processing_mode in ["cloud", "turbo", "advance"]) or model.startswith(("groq", "gemini", "openai", "claude"))
                
                if is_cloud_mode:
                    profiler.start_stage("cloud_generation_ms")
                    try:
                        cloud_messages = [
                            {
                                "role": "system",
                                "content": "You are InsightRAG AI, an enterprise-grade grounded document intelligence assistant. Be concise, direct, and factual."
                            }
                        ]
                        cloud_messages.extend(chat_history_turns)
                        cloud_messages.append({"role": "user", "content": prompt})

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
                                            "messages": cloud_messages,
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
                                            "messages": cloud_messages,
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
                    finally:
                        profiler.end_stage("cloud_generation_ms")

                # =========================================================
                # 2. 100% LOCAL ON-DEVICE MODE (OLLAMA ENGINE)
                # =========================================================
                if not answer:
                    profiler.start_stage("local_ollama_ms")
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
                            successful_model = candidate_models[0]
                            for cand in candidate_models:
                                try:
                                    res = client.post(
                                        f"{working_endpoint}/api/generate",
                                        json={
                                            "model": cand,
                                            "prompt": prompt,
                                            "stream": False,
                                            "options": {"num_ctx": 2048, "temperature": 0.2}
                                        }
                                    )
                                    if res.status_code == 200:
                                        resp = res
                                        successful_model = cand
                                        break
                                except Exception:
                                    continue

                            if resp and resp.status_code == 200:
                                data = resp.json()
                                answer = data.get("response", "").strip()
                                used_llm = True
                                llm_model = f"💻 Local Ollama ({successful_model})"
                                tokens_generated = data.get("eval_count", 0)
                                eval_duration = data.get("eval_duration", 0)
                                if eval_duration > 0:
                                    tokens_per_sec = round((tokens_generated / (eval_duration / 1e9)), 1)
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
                    finally:
                        profiler.end_stage("local_ollama_ms")

            # 3. Visual Snippet Extraction for Diagram / Region of Interest Cropping
            visual_snippet = None
            if results:
                is_visual_query = intent_info.get("is_visual", False)
                chosen_hit = results[0]
                if is_visual_query:
                    for h in results:
                        txt_lower = h.get("text", "").lower()
                        if any(w in txt_lower for w in ["figure", "diagram", "fig.", "chart", "circuit", "table", "schematic"]):
                            chosen_hit = h
                            break

                meta = chosen_hit.get("metadata", {})
                doc_name = meta.get("file_name") or meta.get("source") or meta.get("document_name")
                
                if not doc_name:
                    uploads_dir = Path("./uploads")
                    if uploads_dir.exists():
                        files = [f.name for f in uploads_dir.iterdir() if f.is_file() and f.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]]
                        if files:
                            doc_name = files[0]

                page_num = meta.get("page_number") or meta.get("page") or 1
                is_visual_content = is_visual_query or any(w in chosen_hit.get("text", "").lower() for w in ["figure", "diagram", "fig.", "chart", "table"])
                
                if doc_name and (is_visual_content or Path(doc_name).suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]):
                    import urllib.parse
                    encoded_query = urllib.parse.quote(query)
                    crop_url = f"/api/v1/rag/crop?doc_name={urllib.parse.quote(doc_name)}&page={page_num}&query={encoded_query}"
                    caption = f"Targeted Diagram/Figure Part — Page {page_num} ({doc_name})"
                    visual_snippet = {
                        "has_image": True,
                        "crop_url": crop_url,
                        "doc_name": doc_name,
                        "page": page_num,
                        "caption": caption
                    }

            metrics = profiler.get_metrics()
            metrics["tokens_generated"] = tokens_generated
            metrics["tokens_per_sec"] = tokens_per_sec
            metrics["query_intent"] = intent_info.get("intent")
            metrics["was_rewritten"] = was_rewritten

            return {
                "results": results,
                "query": query,
                "rewritten_query": retrieval_query if was_rewritten else None,
                "total_results": len(results),
                "answer": answer,
                "used_llm": used_llm,
                "llm_model": llm_model,
                "visual_snippet": visual_snippet,
                "metrics": metrics
            }
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {"results": [], "error": str(e)}

    async def query_stream(
        self, query: str, top_k: int = 4, min_score: float = 0.0,
        filters: Optional[Dict] = None, model: str = "llama3.2:3b",
        ollama_url: Optional[str] = None, processing_mode: str = "local",
        api_key: Optional[str] = None, history: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Asynchronous Generator for Server-Sent Events (SSE) token streaming.
        Yields JSON event dictionaries: metadata, token, done.
        """
        if not self.is_available:
            yield {"event": "error", "data": {"error": "RAG not available"}}
            return

        import json
        import asyncio
        from rag.cache import LatencyProfiler
        from rag.query_processor import QueryProcessor

        profiler = LatencyProfiler()
        profiler.start_stage("retrieval_ms")

        intent_info = QueryProcessor.classify_intent(query)
        effective_top_k = min(top_k, intent_info.get("top_k", 4))
        retrieval_query, was_rewritten = QueryProcessor.rewrite_conversational_query(query, history)
        history_str, _ = QueryProcessor.compress_conversation_history(history, max_turns=4)

        results = self.pipeline.query(
            query=retrieval_query,
            top_k=effective_top_k,
            min_score=min_score,
            filters=filters,
        )
        profiler.end_stage("retrieval_ms")

        # Yield metadata event (sources, visual crop)
        visual_snippet = None
        if results:
            meta = results[0].get("metadata", {})
            doc_name = meta.get("file_name") or meta.get("source")
            page_num = meta.get("page_number") or meta.get("page") or 1
            if doc_name:
                import urllib.parse
                visual_snippet = {
                    "has_image": True,
                    "crop_url": f"/api/v1/rag/crop?doc_name={urllib.parse.quote(doc_name)}&page={page_num}&query={urllib.parse.quote(query)}",
                    "doc_name": doc_name,
                    "page": page_num,
                    "caption": f"Targeted Preview — Page {page_num} ({doc_name})"
                }

        yield {
            "event": "metadata",
            "data": {
                "results": results,
                "visual_snippet": visual_snippet,
                "intent": intent_info.get("intent"),
                "rewritten_query": retrieval_query if was_rewritten else None
            }
        }

        # Build prompt
        if results:
            context_texts = [f"[{i+1}] {r.get('text', '').strip()}" for i, r in enumerate(results[:4])]
            prompt = (
                f"You are InsightRAG AI, a fast, grounded multimodal assistant. Answer concisely and accurately using the context below:\n\n"
                f"{history_str}"
                f"DOCUMENT CONTEXT:\n{chr(10).join(context_texts)}\n\n"
                f"QUESTION: {query}\n"
                f"ANSWER:"
            )
        else:
            prompt = f"You are InsightRAG AI. Answer concisely:\n\n{history_str}QUESTION: {query}\nANSWER:"

        # Local Ollama Streaming
        from .ollama_manager import get_working_ollama_host
        working_endpoint = ollama_url or await get_working_ollama_host(auto_start=True) or "http://127.0.0.1:11434"
        local_model = model if not model.startswith(("groq", "gemini", "openai")) else "llama3.2:3b"

        first_token = True
        ttft_ms = 0.0
        token_count = 0
        gen_start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=120.0) as aclient:
                async with aclient.stream(
                    "POST",
                    f"{working_endpoint}/api/generate",
                    json={"model": local_model, "prompt": prompt, "stream": True, "options": {"num_ctx": 2048, "temperature": 0.2}}
                ) as resp:
                    if resp.status_code == 200:
                        async for line in resp.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                chunk_json = json.loads(line)
                                token = chunk_json.get("response", "")
                                if token:
                                    if first_token:
                                        ttft_ms = round((time.perf_counter() - gen_start) * 1000.0, 2)
                                        first_token = False
                                    token_count += 1
                                    yield {"event": "token", "data": {"token": token}}
                            except Exception:
                                pass
        except Exception as err:
            logger.warning(f"Streaming error: {err}")
            yield {"event": "token", "data": {"token": f"\n[Streaming error: {err}]"}}

        total_gen_time = max(time.perf_counter() - gen_start, 0.001)
        tokens_per_sec = round(token_count / total_gen_time, 1)

        metrics = profiler.get_metrics()
        metrics["ttft_ms"] = ttft_ms
        metrics["tokens_generated"] = token_count
        metrics["tokens_per_sec"] = tokens_per_sec

        yield {
            "event": "done",
            "data": {
                "metrics": metrics,
                "llm_model": f"💻 Local Ollama ({local_model})"
            }
        }

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

    def delete_single_document(self, doc_name: str) -> Dict[str, Any]:
        """Delete a single document from uploads and rebuild the FAISS vector index."""
        if not self.is_available:
            return {"status": "unavailable", "error": "RAG service unavailable"}
        try:
            from ..utils.security import sanitize_filename, validate_safe_path
            safe_name = sanitize_filename(doc_name)
            uploads_dir = Path("./uploads")
            target_path = validate_safe_path(uploads_dir, uploads_dir / safe_name)
            
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
                logger.info(f"Deleted document '{safe_name}' from uploads.")

            # Re-index remaining files into FAISS
            remaining_files = [str(f) for f in uploads_dir.iterdir() if f.is_file()]
            self.pipeline.clear()
            if remaining_files:
                self.pipeline.ingest_and_index(remaining_files)

            return {"status": "deleted", "deleted_file": safe_name, **self.get_stats()}
        except Exception as e:
            logger.error(f"Failed to delete document {doc_name}: {e}")
            return {"status": "error", "error": str(e)}

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
