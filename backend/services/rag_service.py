"""
RAG Service — Manages document ingestion and retrieval.
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

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


def extract_attached_visual_diagrams(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract attached visual diagrams and schematics from retrieved results and chunk text.
    Returns deduplicated list with captions, pages, and image URLs.
    """
    import re
    diagrams = []
    seen_urls = set()

    for r in results:
        r_meta = r.get("metadata", {})
        p_num = r_meta.get("page_number") or r_meta.get("page", 1)
        doc = r_meta.get("file_name") or r_meta.get("title") or r_meta.get("source", "")
        
        # 1. From chunk metadata visual_elements
        for vis in r_meta.get("visual_elements", []):
            url = vis.get("image_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                diagrams.append({
                    "doc_name": doc,
                    "page": vis.get("page", p_num),
                    "caption": vis.get("caption", f"Figure on Page {p_num}"),
                    "image_url": url,
                    "file_path": vis.get("file_path"),
                    "visual_type": vis.get("visual_type", "Diagram"),
                    "description": vis.get("description", ""),
                    "bbox": vis.get("bbox"),
                })

        # 2. From inline markdown tags in chunk text [IMAGE / FIGURE: ...] [Image URL: ...]
        txt = r.get("text", "")
        matches = re.findall(r'\[IMAGE / FIGURE:\s*([^\]]+)\]\s*\[Image URL:\s*([^\]]+)\]', txt)
        for cap, url in matches:
            clean_url = url.strip()
            if clean_url and clean_url not in seen_urls:
                seen_urls.add(clean_url)
                diagrams.append({
                    "doc_name": doc,
                    "page": p_num,
                    "caption": cap.strip(),
                    "image_url": clean_url,
                    "visual_type": "Figure / Architecture Diagram",
                    "description": "",
                })

    return diagrams


def get_b64_images(images: Optional[List[str]], visual_diagrams: List[Dict[str, Any]], max_images: int = 2) -> List[str]:
    """Get base64-encoded strings for multimodal vision processing."""
    import base64
    from pathlib import Path
    b64_list = []

    # 1. Directly provided images (base64 or URLs/paths)
    if images:
        for img in images[:max_images]:
            if img.startswith("data:image"):
                b64_list.append(img.split(",", 1)[-1])
            elif Path(img).exists():
                b64_list.append(base64.b64encode(Path(img).read_bytes()).decode("utf-8"))
            elif len(img) > 100 and not img.startswith("http"):
                b64_list.append(img)

    # 2. If no user images, use retrieved visual diagrams
    if not b64_list and visual_diagrams:
        for vd in visual_diagrams[:max_images]:
            fpath = vd.get("file_path")
            if fpath and Path(fpath).exists():
                b64_list.append(base64.b64encode(Path(fpath).read_bytes()).decode("utf-8"))
            elif vd.get("image_url"):
                url_parts = vd["image_url"].split("/images/", 1)
                if len(url_parts) == 2:
                    local_p = Path("./uploads/extracted_images") / url_parts[1]
                    if local_p.exists():
                        b64_list.append(base64.b64encode(local_p.read_bytes()).decode("utf-8"))

    return b64_list


def build_chatgpt_rag_prompt(
    query: str,
    results: List[Dict[str, Any]],
    history_str: str = "",
    target_page: Optional[int] = None,
    is_visual_query: bool = False,
    visual_diagrams: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Constructs an articulate, structured, ChatGPT-grade prompt.
    Ensures:
    1. Deep question comprehension and multi-part decomposition.
    2. Grounded facts with bracketed citations [1], [2].
    3. Clear structured markdown output (Executive Summary, ### Sections, Bullet points, Tables).
    4. Seamless understanding of natural language, English, and Hinglish queries.
    5. Graceful explanation of available information without rigid refusals.
    """
    if results:
        context_blocks = []
        for i, r in enumerate(results[:8]):
            r_meta = r.get("metadata", {})
            p_num = r_meta.get("page_number") or r_meta.get("page")
            p_str = f"Page {p_num}" if p_num else "Excerpt"
            f_name = r_meta.get("file_name") or r_meta.get("title") or "Doc"
            chunk_text = r.get('text', '').strip()[:2500]
            context_blocks.append(f"[{i+1}] ({f_name} | {p_str}):\n{chunk_text}")
        context_str = "\n\n".join(context_blocks)

        page_instruction = (
            f"CRITICAL PAGE FOCUS: The user specifically asked about Page {target_page}. You MUST detail the content on Page {target_page} using the context provided below.\n"
            if target_page else ""
        )
        
        visual_diagram_lines = []
        if visual_diagrams:
            for vd in visual_diagrams[:5]:
                desc = f": {vd['description']}" if vd.get('description') else ""
                visual_diagram_lines.append(
                    f"- {vd.get('caption', 'Diagram')} [Page {vd.get('page', 1)}]{desc} (URL: {vd.get('image_url', '')})"
                )

        visual_instruction = (
            "ATTACHED VISUAL DIAGRAMS & FIGURES:\n"
            "The following diagrams/figures from the document are attached to this answer:\n"
            + "\n".join(visual_diagram_lines) + "\n"
            "Explain the visual structure, flow, and components referenced in these diagrams, and mention that the user can inspect the high-resolution attached diagrams in the viewer cards below.\n"
            if visual_diagram_lines else (
                "VISUAL DIAGRAMS/SNAPSHOTS: When the user asks for an image, diagram, architecture schematic, or snapshot (e.g. 'photo of the project part'), explain the visual structure and components from the context and note that the focused visual crop snapshot is rendered in the viewer.\n"
                if is_visual_query else ""
            )
        )

        return (
            "You are InsightRAG AI, an elite, articulate, and comprehensive AI document intelligence consultant inspired by the depth, clarity, and helpfulness of ChatGPT.\n"
            "Your objective is to thoroughly answer the user's question, address every facet or sub-part asked, and provide a rich, well-structured response grounded in the provided document context.\n\n"
            "CORE OPERATING PRINCIPLES:\n"
            "1. QUESTION COMPREHENSION & BREAKDOWN:\n"
            "   - Break down the user's question into its core components and systematically answer each part.\n"
            "   - If the user asks in Hindi, Hinglish, or English, understand their intent deeply and respond in an articulate, clear, and natural tone (using clear English or natural bilingual explanation as best fits the query).\n\n"
            "2. FACTUAL GROUNDING & PRECISE CITATIONS:\n"
            "   - Base all statements, metrics, specifications, and dates on the provided context chunks.\n"
            "   - You MUST cite every claim using bracketed markers like [1], [2], or [1][3] immediately after the relevant statement.\n"
            "   - If certain specific details requested are not mentioned in the context, state clearly what the document DOES specify, and politely clarify what details are not present, rather than shutting down or refusing.\n\n"
            "3. STRUCTURED CHATGPT-GRADE PRESENTATION:\n"
            "   - **Executive Summary / Direct Answer**: Start with a crisp 1-2 sentence direct overview answering the core question upfront.\n"
            "   - **Detailed Breakdown**: Structure multi-part or complex answers using clear markdown headings (###), logical sub-sections, bullet points, and **bold** key terms.\n"
            "   - **Data & Comparisons**: Use markdown tables or bulleted specs when presenting comparative numbers, metrics, or architecture components.\n"
            "   - **Synthesis & Explanation**: Don't just list raw chunks. Explain *how* and *why* things work, synthesizing details across multiple chunks into a cohesive narrative.\n"
            "   - **Key Takeaways / Practical Summary**: Conclude with a helpful summary or key takeaway when relevant.\n\n"
            f"{visual_instruction}"
            f"{page_instruction}"
            f"{history_str}"
            f"DOCUMENT CONTEXT:\n{context_str}\n\n"
            f"QUESTION: {query}\n"
            f"ANSWER:"
        )
    else:
        return (
            "You are InsightRAG AI, a brilliant, articulate, and helpful document intelligence assistant inspired by ChatGPT.\n"
            "Provide a comprehensive, well-structured, and helpful answer to the user's question using clear markdown formatting.\n"
            "If the question specifically refers to proprietary document data that has not yet been indexed, provide a helpful conceptual answer and politely remind the user to upload their documents (.pdf, .txt, .md, .docx, .csv) for document-grounded answers.\n\n"
            f"{history_str}"
            f"QUESTION: {query}\n"
            f"ANSWER:"
        )


class RAGService:
    """Manages RAG document ingestion and retrieval."""

    def __init__(self, index_path: str = "./rag_index", org_id: str = "default"):
        self.index_path = index_path
        self.org_id = org_id
        self.hardware_mode: str = "gpu"
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

    def set_hardware_mode(self, mode: str) -> Dict[str, Any]:
        """
        Dynamically switch processing hardware mode between 'gpu' and 'cpu'.
        Logs a prominent banner in the terminal, moves embedding models, and adjusts Ollama GPU offload.
        """
        mode = mode.lower().strip()
        if mode not in ["gpu", "cpu"]:
            mode = "gpu"

        from .ollama_manager import get_system_hardware_specs
        specs = get_system_hardware_specs()
        has_gpu = specs.get("has_gpu", False)
        gpu_name = specs.get("gpu_name", "GPU")
        vram_gb = specs.get("vram_gb", 0.0)

        effective_device = "cpu"
        if mode == "gpu":
            try:
                import torch
                if torch.cuda.is_available():
                    effective_device = "cuda"
            except Exception:
                pass

        self.hardware_mode = mode

        # Configure pipeline embedding generator
        if self.is_available and hasattr(self.pipeline, "embedding_gen"):
            try:
                self.pipeline.embedding_gen.set_device(effective_device)
            except Exception as e:
                logger.warning(f"Failed to set embedding device to {effective_device}: {e}")

        def _safe_terminal_print(text: str):
            try:
                print(text, flush=True)
            except Exception:
                try:
                    import sys
                    sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
                    sys.stdout.buffer.flush()
                except Exception:
                    pass

        # Prominent Terminal Output
        if mode == "gpu":
            _safe_terminal_print("\n" + "=" * 72)
            _safe_terminal_print("[HARDWARE ACCELERATION ENGINE] SWITCHED TO GPU ACCELERATION MODE")
            _safe_terminal_print(f"   Target Device:        GPU (High-Speed Local Hardware Acceleration)")
            _safe_terminal_print(f"   Detected GPU:         {gpu_name} (VRAM: {vram_gb} GB)")
            _safe_terminal_print(f"   Embedding Model:      RUNNING ON {effective_device.upper()}")
            _safe_terminal_print(f"   Ollama GPU Offload:   ENABLED (num_gpu: 99 Layers Offloaded)")
            _safe_terminal_print("   Processing Status:    ACTIVE -- INFERENCE & RETRIEVAL BOOSTED ON GPU")
            _safe_terminal_print("=" * 72 + "\n")
            msg = f"GPU Acceleration Active ({gpu_name} - num_gpu: 99)"
        else:
            _safe_terminal_print("\n" + "=" * 72)
            _safe_terminal_print("[HARDWARE ACCELERATION ENGINE] SWITCHED TO CPU STANDARD MODE")
            _safe_terminal_print(f"   Target Device:        CPU (Multi-Threaded Parallel Execution)")
            _safe_terminal_print(f"   CPU Threads:          {specs.get('cpu_threads', 8)} Threads")
            _safe_terminal_print(f"   Embedding Model:      RUNNING ON CPU")
            _safe_terminal_print(f"   Ollama GPU Offload:   DISABLED (num_gpu: 0 - 100% CPU)")
            _safe_terminal_print("   Processing Status:    ACTIVE -- CPU STANDARD MODE")
            _safe_terminal_print("=" * 72 + "\n")
            msg = f"CPU Standard Mode Active ({specs.get('cpu_threads', 8)} Threads)"

        return {
            "mode": mode,
            "effective_device": effective_device,
            "has_gpu": has_gpu,
            "gpu_name": gpu_name,
            "vram_gb": vram_gb,
            "message": msg
        }

    def get_hardware_mode(self) -> Dict[str, Any]:
        """Get current hardware processing mode and specs."""
        from .ollama_manager import get_system_hardware_specs
        specs = get_system_hardware_specs()
        mode = getattr(self, "hardware_mode", "gpu")
        return {
            "mode": mode,
            "has_gpu": specs.get("has_gpu", False),
            "gpu_name": specs.get("gpu_name", "Integrated / CPU"),
            "vram_gb": specs.get("vram_gb", 0.0),
            "cpu_threads": specs.get("cpu_threads", 8),
            "acceleration_mode": "GPU AUTO-ACCELERATED" if mode == "gpu" else "CPU PARALLEL ENGINE",
        }

    @property
    def is_available(self) -> bool:
        return self.pipeline is not None

    def ingest_documents(
        self,
        file_paths: List[str],
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Ingest documents synchronously into RAG index with optional page range."""
        if not self.is_available:
            return {"error": "RAG not available", "documents_ingested": 0}

        try:
            stats = self.pipeline.ingest_and_index(
                file_paths,
                start_page=start_page,
                end_page=end_page,
                progress_callback=progress_callback,
            )
            return stats
        except Exception as e:
            logger.error(f"RAG ingestion failed: {e}")
            return {"error": str(e), "documents_ingested": 0}

    def start_background_ingestion(
        self,
        task_id: str,
        file_paths: List[str],
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches heavy ingestion to INGESTION_EXECUTOR thread pool.
        Returns immediately with initial task metadata.
        """
        from .rag_task_manager import rag_task_manager, INGESTION_EXECUTOR

        task = rag_task_manager.create_task(task_id, file_paths)

        # Offload CPU work (PyMuPDF, OpenCV, Embeddings) to dedicated thread pool
        # so FastAPI request threads and the event loop stay completely responsive
        INGESTION_EXECUTOR.submit(
            self._run_ingestion_worker,
            task_id,
            file_paths,
            start_page,
            end_page,
        )
        return task

    def _run_ingestion_worker(
        self,
        task_id: str,
        file_paths: List[str],
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
    ):
        """Worker function executed inside INGESTION_EXECUTOR thread pool."""
        from .rag_task_manager import rag_task_manager

        def progress_hook(step: int, stage_name: str, progress_pct: int, message: str):
            rag_task_manager.update_progress(task_id, step, stage_name, progress_pct, message)

        try:
            if not self.is_available:
                rag_task_manager.mark_failed(task_id, "RAG pipeline unavailable on backend.")
                return

            rag_task_manager.update_progress(
                task_id, 0, "Document Buffer & Format Validation", 5, "Starting background document ingestion..."
            )

            stats = self.pipeline.ingest_and_index(
                file_paths,
                start_page=start_page,
                end_page=end_page,
                progress_callback=progress_hook,
            )

            if stats.get("errors", 0) > 0 and stats.get("documents_ingested", 0) == 0:
                rag_task_manager.mark_failed(
                    task_id,
                    f"Extraction failed for all {len(file_paths)} document(s).",
                    stage="Document Buffer & Format Validation",
                )
            else:
                rag_task_manager.mark_completed(task_id, stats)

        except Exception as e:
            logger.exception(f"Background ingestion worker exception for task {task_id}: {e}")
            rag_task_manager.mark_failed(task_id, str(e))

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve current status of an ingestion task."""
        from .rag_task_manager import rag_task_manager
        return rag_task_manager.get_task(task_id)

    def query(
        self, query: str, top_k: int = 4, min_score: float = 0.0,
        filters: Optional[Dict] = None, model: str = "llama3.2:3b",
        generate_answer: bool = True, ollama_url: Optional[str] = None,
        processing_mode: str = "local", api_key: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None
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
        effective_top_k = max(top_k, intent_info.get("top_k", 5))
        history_str, chat_history_turns = QueryProcessor.compress_conversation_history(history, max_turns=4)

        # 1b. Service-level query rewriting & Hinglish normalization
        was_rewritten = False
        retrieval_query = QueryProcessor.normalize_hinglish_query(query)
        if history:
            try:
                retrieval_query, was_rewritten = QueryProcessor.rewrite_query_with_llm(
                    current_query=query,
                    history=history,
                    ollama_url=ollama_url or "http://127.0.0.1:11434",
                    model=model if not model.startswith(("groq", "gemini", "openai")) else "llama3.2:3b",
                )
            except Exception as rewrite_err:
                logger.warning(f"Query rewrite failed, using normalized query: {rewrite_err}")
                retrieval_query = QueryProcessor.normalize_hinglish_query(query)
                was_rewritten = False
        profiler.end_stage("query_processing_ms")

        try:
            # 2. Hybrid Retrieval + Reranking (using decomposed/rewritten standalone queries)
            profiler.start_stage("retrieval_ms")
            results = self.pipeline.query(
                query=retrieval_query,
                top_k=effective_top_k,
                min_score=min_score,
                filters=filters,
                history=None,  # rewriting already done at service level
            )
            profiler.end_stage("retrieval_ms")

            # Extract attached visual diagrams and schematics from retrieved results
            visual_diagrams = extract_attached_visual_diagrams(results)
            if visual_diagrams:
                try:
                    print(f"\nATTACHED VISUAL DIAGRAMS ({len(visual_diagrams)})", flush=True)
                    for vd in visual_diagrams:
                        print(f"  - {vd.get('caption', 'Figure')} [Page {vd.get('page', 1)}] ({vd.get('image_url', '')})", flush=True)
                except Exception:
                    pass

            b64_images = get_b64_images(images, visual_diagrams)

            answer = None
            used_llm = False
            llm_model = None
            ttft_ms = 0.0
            tokens_generated = 0
            tokens_per_sec = 0.0

            if generate_answer:
                profiler.start_stage("prompt_prep_ms")
                prompt = build_chatgpt_rag_prompt(
                    query=query,
                    results=results,
                    history_str=history_str,
                    target_page=intent_info.get("target_page"),
                    is_visual_query=intent_info.get("is_visual", False) or bool(b64_images),
                    visual_diagrams=visual_diagrams
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
                                "content": (
                                    "You are InsightRAG AI, an elite AI document intelligence consultant inspired by ChatGPT.\n"
                                    "1. Deeply understand and systematically answer all facets of the user's question (supporting English, Hindi, and Hinglish).\n"
                                    "2. Base factual claims strictly on provided context and cite chunks like [1][2].\n"
                                    "3. Format with an Executive Summary, clear markdown sections (###), bullet points, and bold key terms.\n"
                                    "4. Synthesize facts across chunks into coherent, articulate explanations.\n"
                                    "5. Include exact numbers, metrics, and page references whenever present."
                                )
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
                        logger.exception(f"Cloud turbo processing failed, falling back to local: {cloud_err}")
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
                        candidate_models = []
                        if b64_images:
                            candidate_models.extend(["qwen2.5vl:3b", "qwen2.5vl", "llama3.2-vision"])
                        candidate_models.extend([local_model, "llama3.2:3b", "llama3.2", "qwen2.5:3b", "mistral:latest"])
                        for inst in installed_models:
                            if inst not in candidate_models:
                                candidate_models.append(inst)

                        _cpu_threads = max(1, (os.cpu_count() or 4) - 1)
                        with httpx.Client(timeout=120.0) as client:
                            resp = None
                            successful_model = candidate_models[0]
                            for cand in candidate_models:
                                try:
                                    payload = {
                                        "model": cand,
                                        "prompt": prompt,
                                        "stream": False,
                                        "keep_alive": "30m",
                                        "options": {
                                            "num_ctx": 8192,
                                            "temperature": 0.35,
                                            "num_predict": 2048,
                                            "num_thread": _cpu_threads,
                                            "top_k": 40,
                                            "top_p": 0.9,
                                        }
                                    }
                                    if b64_images and ("vl" in cand or "vision" in cand):
                                        payload["images"] = b64_images[:2]

                                    res = client.post(
                                        f"{working_endpoint}/api/generate",
                                        json=payload
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
                                is_vision_used = "vl" in successful_model or "vision" in successful_model
                                tag = "Local Vision" if is_vision_used else "Local Ollama"
                                llm_model = f"💻 {tag} ({successful_model})"
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
                        logger.exception(f"Local Ollama generation failed: {ollama_err}")
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
                target_page = intent_info.get("target_page")
                
                # Pick the most relevant result
                chosen_hit = results[0]
                if target_page is not None:
                    for h in results:
                        h_meta = h.get("metadata", {})
                        h_page = h_meta.get("page_number") or h_meta.get("page")
                        if h_page is not None and int(h_page) == int(target_page):
                            chosen_hit = h
                            break
                elif is_visual_query:
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

                # Only attach visual snippet if user query requested visual content or target page
                requires_visual = is_visual_query or (target_page is not None)

                # Compute page_num from target_page or best-hit metadata
                page_num = target_page
                if page_num is None:
                    meta_page = meta.get("page_number") or meta.get("page")
                    page_num = int(meta_page) if meta_page is not None else 1
                
                if doc_name and requires_visual:
                    import urllib.parse
                    encoded_query = urllib.parse.quote(query)
                    coords_param = ""
                    for v in meta.get("visual_elements", []):
                        for sub in v.get("sub_regions", []):
                            lbl = sub.get("label", "").lower()
                            if lbl and any(kw in lbl for kw in query.lower().split() if len(kw) > 2):
                                sb = sub.get("bbox")
                                if sb and len(sb) == 4:
                                    coords_param = f"&x0={sb[0]}&y0={sb[1]}&x1={sb[2]}&y1={sb[3]}"
                                    break
                        if coords_param:
                            break

                    crop_url = f"/api/v1/rag/crop?doc_name={urllib.parse.quote(doc_name)}&page={page_num}{coords_param}&query={encoded_query}"
                    caption = f"Targeted Page {page_num} Preview ({doc_name})" if target_page else f"Focused Section / Diagram ROI — Page {page_num} ({doc_name})"
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
                "visual_diagrams": visual_diagrams,
                "metrics": metrics
            }
        except Exception as e:
            logger.exception(f"RAG query failed with full traceback: {e}")
            return {"results": [], "error": str(e), "answer": None}

    async def query_stream(
        self, query: str, top_k: int = 4, min_score: float = 0.0,
        filters: Optional[Dict] = None, model: str = "llama3.2:3b",
        ollama_url: Optional[str] = None, processing_mode: str = "local",
        api_key: Optional[str] = None, history: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None
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
        effective_top_k = max(top_k, intent_info.get("top_k", 5))
        history_str, _ = QueryProcessor.compress_conversation_history(history, max_turns=4)

        # 1b. Service-level query rewriting & Hinglish normalization
        was_rewritten = False
        retrieval_query = QueryProcessor.normalize_hinglish_query(query)
        if history:
            try:
                retrieval_query, was_rewritten = QueryProcessor.rewrite_query_with_llm(
                    current_query=query,
                    history=history,
                    ollama_url=ollama_url or "http://127.0.0.1:11434",
                    model=model if not model.startswith(("groq", "gemini", "openai")) else "llama3.2:3b",
                )
            except Exception as rewrite_err:
                logger.warning(f"Query rewrite failed, using normalized query: {rewrite_err}")
                retrieval_query = QueryProcessor.normalize_hinglish_query(query)
                was_rewritten = False

        results = self.pipeline.query(
            query=retrieval_query,
            top_k=effective_top_k,
            min_score=min_score,
            filters=filters,
            history=None,  # rewriting already done at service level
        )
        profiler.end_stage("retrieval_ms")

        # Extract attached visual diagrams and schematics from retrieved results
        visual_diagrams = extract_attached_visual_diagrams(results)
        if visual_diagrams:
            try:
                print(f"\nATTACHED VISUAL DIAGRAMS ({len(visual_diagrams)})", flush=True)
                for vd in visual_diagrams:
                    print(f"  - {vd.get('caption', 'Figure')} [Page {vd.get('page', 1)}] ({vd.get('image_url', '')})", flush=True)
            except Exception:
                pass

        b64_images = get_b64_images(images, visual_diagrams)

        # Yield metadata event (sources, visual crop, attached visual diagrams)
        visual_snippet = None
        target_page = intent_info.get("target_page")
        is_visual_query = intent_info.get("is_visual", False)
        requires_visual = is_visual_query or (target_page is not None)

        if results and requires_visual:
            chosen_hit = results[0]
            if target_page is not None:
                for h in results:
                    h_meta = h.get("metadata", {})
                    h_page = h_meta.get("page_number") or h_meta.get("page")
                    if h_page is not None and int(h_page) == int(target_page):
                        chosen_hit = h
                        break

            meta = chosen_hit.get("metadata", {})
            doc_name = meta.get("file_name") or meta.get("source")
            page_num = target_page or meta.get("page_number") or meta.get("page") or 1
            if doc_name:
                import urllib.parse
                coords_param = ""
                for v in meta.get("visual_elements", []):
                    for sub in v.get("sub_regions", []):
                        lbl = sub.get("label", "").lower()
                        if lbl and any(kw in lbl for kw in query.lower().split() if len(kw) > 2):
                            sb = sub.get("bbox")
                            if sb and len(sb) == 4:
                                coords_param = f"&x0={sb[0]}&y0={sb[1]}&x1={sb[2]}&y1={sb[3]}"
                                break
                    if coords_param:
                        break

                visual_snippet = {
                    "has_image": True,
                    "crop_url": f"/api/v1/rag/crop?doc_name={urllib.parse.quote(doc_name)}&page={page_num}{coords_param}&query={urllib.parse.quote(query)}",
                    "doc_name": doc_name,
                    "page": page_num,
                    "caption": f"Targeted Page {page_num} Preview ({doc_name})" if target_page else f"Focused Section / Diagram ROI — Page {page_num} ({doc_name})"
                }

        yield {
            "event": "metadata",
            "data": {
                "results": results,
                "visual_snippet": visual_snippet,
                "visual_diagrams": visual_diagrams,
                "intent": intent_info.get("intent"),
                "target_page": target_page,
                "was_rewritten": was_rewritten,
                "rewritten_query": retrieval_query if was_rewritten else None,
            }
        }

        # Build ChatGPT-grade prompt
        prompt = build_chatgpt_rag_prompt(
            query=query,
            results=results,
            history_str=history_str,
            target_page=target_page,
            is_visual_query=is_visual_query or bool(b64_images),
            visual_diagrams=visual_diagrams
        )

        # Local Ollama Streaming
        from .ollama_manager import get_working_ollama_host, get_installed_models
        working_endpoint = ollama_url or await get_working_ollama_host(auto_start=True) or "http://127.0.0.1:11434"
        local_model = model if not model.startswith(("groq", "gemini", "openai")) else "llama3.2:3b"

        stream_model = local_model
        if b64_images:
            try:
                installed = await get_installed_models()
                for v_cand in ["qwen2.5vl:3b", "qwen2.5vl", "llama3.2-vision"]:
                    if v_cand in installed:
                        stream_model = v_cand
                        break
            except Exception:
                pass

        first_token = True
        ttft_ms = 0.0
        token_count = 0
        gen_start = time.perf_counter()

        try:
            stream_payload = {
                "model": stream_model,
                "prompt": prompt,
                "stream": True,
                "keep_alive": "30m",
                "options": {
                    "num_ctx": 8192,
                    "temperature": 0.35,
                    "num_predict": 2048,
                    "num_thread": max(1, (__import__('os').cpu_count() or 4) - 1),
                    "top_k": 40,
                    "top_p": 0.9,
                }
            }
            if b64_images and ("vl" in stream_model or "vision" in stream_model):
                stream_payload["images"] = b64_images[:2]

            async with httpx.AsyncClient(timeout=120.0) as aclient:
                async with aclient.stream(
                    "POST",
                    f"{working_endpoint}/api/generate",
                    json=stream_payload
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
            logger.exception(f"Streaming error with full traceback: {err}")
            yield {"event": "token", "data": {"token": f"\n[Streaming error: {err}]"}}

        total_gen_time = max(time.perf_counter() - gen_start, 0.001)
        tokens_per_sec = round(token_count / total_gen_time, 1)

        metrics = profiler.get_metrics()
        metrics["ttft_ms"] = ttft_ms
        metrics["tokens_generated"] = token_count
        metrics["tokens_per_sec"] = tokens_per_sec
        metrics["query_intent"] = intent_info.get("intent")
        metrics["was_rewritten"] = was_rewritten

        is_vision = "vl" in stream_model or "vision" in stream_model
        tag = "Local Vision" if is_vision else "Local Ollama"

        yield {
            "event": "done",
            "data": {
                "metrics": metrics,
                "llm_model": f"💻 {tag} ({stream_model})"
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
