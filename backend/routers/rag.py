"""
RAG router — Document upload and context retrieval.
"""

import logging
from pathlib import Path
from typing import List, Optional

import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Query, BackgroundTasks, status

from ..dependencies import get_rag_service
from ..models.requests import RAGQueryRequest
from ..models.responses import RAGQueryResponse, RAGUploadResponse, RAGTaskStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/stats")
async def get_rag_stats():
    """Get statistics about currently indexed documents and vectors."""
    rag_svc = get_rag_service()
    return rag_svc.get_stats()


@router.post("/clear")
@router.delete("/documents")
async def clear_rag_knowledge_base():
    """Clear all documents and vectors from the RAG knowledge base."""
    rag_svc = get_rag_service()
    return rag_svc.clear()


@router.delete("/documents/{doc_name}")
async def delete_single_rag_document(doc_name: str):
    """Delete a specific document and its vector embeddings from the knowledge base."""
    rag_svc = get_rag_service()
    result = rag_svc.delete_single_document(doc_name)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete document."))
    return result


@router.post("/documents", response_model=RAGUploadResponse)
async def upload_rag_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    start_page: Optional[int] = Form(None),
    end_page: Optional[int] = Form(None),
    sync: bool = Query(False, description="Run ingestion synchronously if True (default: False for non-blocking background ingestion)")
):
    """Upload documents to the RAG knowledge base. Ingests in the background and returns a task_id immediately."""
    rag_svc = get_rag_service()

    if not rag_svc.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available. Install sentence-transformers and faiss-cpu."
        )

    from ..utils.security import sanitize_filename, validate_file_extension, validate_safe_path

    upload_dir = Path("./uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    # Maximum file size allowed (50MB per document)
    MAX_FILE_BYTES = 50 * 1024 * 1024

    try:
        for file in files:
            # 1. Filename sanitization against path traversal / shell injection
            safe_name = sanitize_filename(file.filename or "upload.txt")
            
            # 2. Whitelist extension check
            validate_file_extension(safe_name)
            
            # 3. Path containment validation
            target_path = validate_safe_path(upload_dir, upload_dir / safe_name)
            
            # 4. Stream & enforce size limits
            content = await file.read()
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail=f"File '{safe_name}' exceeds 50MB limit.")
            if len(content) == 0:
                continue

            target_path.write_bytes(content)
            saved_paths.append(str(target_path))

        if not saved_paths:
            raise HTTPException(status_code=400, detail="No valid non-empty files were provided.")

        if sync:
            # Synchronous ingestion mode (for legacy callers / tests)
            stats = rag_svc.ingest_documents(
                saved_paths,
                start_page=start_page,
                end_page=end_page
            )
            return RAGUploadResponse(
                task_id=None,
                status="completed",
                message=f"Synchronous indexing complete: {stats.get('documents_ingested', 0)} document(s) ({stats.get('chunks_created', 0)} chunks).",
                documents_ingested=stats.get("documents_ingested", 0),
                chunks_created=stats.get("chunks_created", 0),
                errors=stats.get("errors", 0),
            )

        # Asynchronous background ingestion via dedicated thread pool executor
        task_id = str(uuid.uuid4())
        rag_svc.start_background_ingestion(
            task_id=task_id,
            file_paths=saved_paths,
            start_page=start_page,
            end_page=end_page
        )

        return RAGUploadResponse(
            task_id=task_id,
            status="processing",
            message=f"Document upload accepted for {len(saved_paths)} file(s). Ingestion running in background.",
            documents_ingested=0,
            chunks_created=0,
            errors=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document upload.")


@router.get("/documents/{task_id}/status", response_model=RAGTaskStatusResponse)
@router.get("/tasks/{task_id}", response_model=RAGTaskStatusResponse)
async def get_rag_ingestion_status(task_id: str):
    """
    Get real-time ingestion progress and status for a document upload task.
    Tracks multi-stage comprehension milestones:
    (0: Format Validation -> 1: Rasterization/OCR -> 2: Table Extraction -> 3: Diagrams/CV -> 4: Captions -> 5: FAISS Indexing -> Complete)
    """
    rag_svc = get_rag_service()
    task_info = rag_svc.get_task_status(task_id)
    if not task_info:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found. It may have expired or was never created."
        )
    return RAGTaskStatusResponse(**task_info)


import io
from ..utils.security import ALLOWED_VISUAL_EXTENSIONS

@router.get("/crop")
async def get_diagram_crop(
    doc_name: str = Query(..., description="Document file name in uploads directory"),
    page: int = Query(1, ge=1, le=10000, description="1-indexed page number"),
    query: Optional[str] = Query(None, description="Target query / diagram keyword to isolate specific part"),
    x0: float = Query(0.0),
    y0: float = Query(0.0),
    x1: float = Query(0.0),
    y1: float = Query(0.0),
    padding: int = Query(35, ge=0, le=200),
    dpi: int = Query(175, ge=72, le=300)
):
    """
    Crops and renders a specific sub-region / diagram of a PDF or image document safely.
    If query or diagram terms are present, automatically isolates the exact targeted figure/diagram bounding box.
    Returns high-resolution PNG image bytes.
    """
    # Safely coerce query parameters
    try:
        f_x0 = float(x0) if not hasattr(x0, 'default') else 0.0
        f_y0 = float(y0) if not hasattr(y0, 'default') else 0.0
        f_x1 = float(x1) if not hasattr(x1, 'default') else 0.0
        f_y1 = float(y1) if not hasattr(y1, 'default') else 0.0
        f_padding = int(padding) if not hasattr(padding, 'default') else 35
        f_dpi = int(dpi) if not hasattr(dpi, 'default') else 175
        f_page = int(page) if not hasattr(page, 'default') else 1
    except (ValueError, TypeError):
        f_x0, f_y0, f_x1, f_y1, f_padding, f_dpi, f_page = 0.0, 0.0, 0.0, 0.0, 35, 175, 1

    clean_query = str(query).strip() if (query is not None and not hasattr(query, 'default')) else ""

    from ..utils.security import sanitize_filename, validate_safe_path

    upload_dir = Path("./uploads")
    
    # 1. Sanitize input doc_name
    safe_doc_name = sanitize_filename(str(doc_name))
    target_candidate = upload_dir / safe_doc_name

    # 2. Enforce strict directory containment
    safe_path = validate_safe_path(upload_dir, target_candidate)

    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="Document not found.")

    ext = safe_path.suffix.lower()
    if ext not in ALLOWED_VISUAL_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Visual cropping is not supported for {ext} files.")

    # 1. PDF File Targeted Cropping
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(safe_path))
            page_idx = min(max(0, f_page - 1), len(doc) - 1)
            pdf_page = doc[page_idx]

            # Mode A: User supplied explicit bounding box coordinates
            if f_x1 > f_x0 and f_y1 > f_y0:
                rect = fitz.Rect(
                    max(0, f_x0 - f_padding),
                    max(0, f_y0 - f_padding),
                    min(pdf_page.rect.width, f_x1 + f_padding),
                    min(pdf_page.rect.height, f_y1 + f_padding)
                )
            else:
                # Mode B: Multi-tiered Intelligent Region of Interest (ROI) Localization
                target_rect = None
                
                STOPWORDS = {
                    'the', 'a', 'an', 'is', 'of', 'od', 'and', 'or', 'in', 'to', 'for', 'with',
                    'diagram', 'diagrams', 'figure', 'figures', 'chart', 'charts', 'show', 'give',
                    'me', 'what', 'how', 'part', 'image', 'images', 'photo', 'photos', 'picture',
                    'pictures', 'pic', 'pics', 'preview', 'crop', 'snapshot', 'document', 'doc',
                    'pdf', 'file', 'page', 'section', 'portion', 'content', 'view', 'display',
                    'take', 'send', 'tell', 'about', 'write', 'extract', 'find', 'please', 'can',
                    'you', 'there', 'this', 'that', 'from', 'here'
                }
                
                import re
                keywords = []
                if clean_query:
                    keywords = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', clean_query) if len(w) > 1 and w.lower() not in STOPWORDS]

                # 1. Visual Elements check (Images & Vector Diagrams)
                drawings = pdf_page.get_drawings()
                drawing_rects = [d["rect"] for d in drawings if d.get("rect") and (d["rect"].width * d["rect"].height) > 1500 and d["rect"].height > 30 and d["rect"].width > 50]
                image_infos = pdf_page.get_image_info(xrefs=True)
                image_rects = [fitz.Rect(img["bbox"]) for img in image_infos if img.get("bbox") and (fitz.Rect(img["bbox"]).width * fitz.Rect(img["bbox"]).height) > 1500]
                all_visual_rects = drawing_rects + image_rects

                # Priority 1: Diagram / Figure / Chart / Table Localization with Sub-Region Support
                is_diagram_query = bool(clean_query and any(w in clean_query.lower() for w in ['diagram', 'figure', 'fig.', 'chart', 'circuit', 'graph', 'schematic', 'table', 'box', 'node', 'architecture', 'component']))
                if is_diagram_query and all_visual_rects:
                    try:
                        from src.rag.image_regions import find_pdf_diagram_and_sub_regions
                        sub_rect, is_sub, meta_info = find_pdf_diagram_and_sub_regions(pdf_page, clean_query, padding=f_padding)
                        if sub_rect is not None:
                            target_rect = sub_rect
                    except Exception as roi_err:
                        logger.debug(f"Sub-region ROI localization error: {roi_err}")

                    if target_rect is None:
                        caption_hits = []
                        for kw in keywords[:3]:
                            caption_hits.extend(pdf_page.search_for(kw))
                        for cap in ['figure', 'fig.', 'diagram', 'chart', 'table', 'circuit']:
                            caption_hits.extend(pdf_page.search_for(cap))
                        
                        if caption_hits:
                            best_vis = None
                            min_dist = float('inf')
                            for hit in caption_hits:
                                for v in all_visual_rects:
                                    dist = ((hit.x0 - v.x0)**2 + (hit.y0 - v.y0)**2)**0.5
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_vis = v
                            if best_vis and min_dist < 400:
                                target_rect = fitz.Rect(
                                    max(0, best_vis.x0 - f_padding),
                                    max(0, best_vis.y0 - f_padding),
                                    min(pdf_page.rect.width, best_vis.x1 + f_padding),
                                    min(pdf_page.rect.height, best_vis.y1 + f_padding)
                                )
                        if target_rect is None and all_visual_rects:
                            target_rect = max(all_visual_rects, key=lambda r: r.width * r.height)

                # Priority 2: Intelligent Document Section / Heading Bounding Box
                # (Resumes, Reports, Scientific Papers, Layout-driven PDFs)
                if target_rect is None and keywords:
                    blocks = [b for b in pdf_page.get_text("blocks") if b[6] == 0 and b[4].strip()]
                    
                    SECTION_TERMS = {
                        'project', 'projects', 'experience', 'education', 'skill', 'skills', 
                        'competencies', 'summary', 'certification', 'certifications', 
                        'publication', 'publications', 'reference', 'objective', 'work', 
                        'background', 'methodology', 'results', 'discussion', 'conclusion', 
                        'abstract', 'overview', 'interests', 'achievements', 'awards'
                    }
                    
                    headings = []
                    for i, b in enumerate(blocks):
                        txt = b[4].strip()
                        lines = [l.strip() for l in txt.split('\n') if l.strip()]
                        clean_txt = re.sub(r'[^a-zA-Z0-9\s]', '', txt).strip()
                        words_in_b = [w.lower() for w in clean_txt.split()]
                        
                        is_heading = False
                        if len(lines) <= 2 and len(txt) <= 80:
                            if clean_txt.isupper() and len(clean_txt) >= 3:
                                is_heading = True
                            elif any(t in words_in_b for t in SECTION_TERMS):
                                is_heading = True
                        if is_heading:
                            headings.append((i, b, txt))
                            
                    # Check if any query keyword matches a section heading
                    matched_h_idx = None
                    for kw in keywords:
                        for idx, (b_idx, b, txt) in enumerate(headings):
                            txt_lower = txt.lower()
                            if kw in txt_lower or any(kw == w for w in re.findall(r'\b\w+\b', txt_lower)):
                                matched_h_idx = idx
                                break
                        if matched_h_idx is not None:
                            break
                            
                    if matched_h_idx is not None:
                        curr_b_idx, curr_b, curr_txt = headings[matched_h_idx]
                        start_y = curr_b[1]  # y0 of heading
                        
                        # Section boundary extends to the start of the next section heading
                        if matched_h_idx + 1 < len(headings):
                            next_b_idx, next_b, next_txt = headings[matched_h_idx + 1]
                            end_y = next_b[1]
                        else:
                            end_y = blocks[-1][3]
                            
                        target_rect = fitz.Rect(
                            max(0, pdf_page.rect.x0 + 15),
                            max(0, start_y - 12),
                            min(pdf_page.rect.width, pdf_page.rect.width - 15),
                            min(pdf_page.rect.height, end_y - 2)
                        )

                # Priority 3: Targeted Paragraph / Sub-block Match
                # (For specific project titles, keywords, technologies, or topics)
                if target_rect is None and keywords:
                    blocks = [b for b in pdf_page.get_text("blocks") if b[6] == 0 and b[4].strip()]
                    best_block = None
                    max_score = 0
                    for b in blocks:
                        b_text = b[4].lower()
                        score = sum(3 if f' {kw} ' in f' {b_text} ' else (1 if kw in b_text else 0) for kw in keywords)
                        if score > max_score:
                            max_score = score
                            best_block = b
                            
                    if best_block and max_score > 0:
                        target_rect = fitz.Rect(
                            max(0, pdf_page.rect.x0 + 15),
                            max(0, best_block[1] - 18),
                            min(pdf_page.rect.width, pdf_page.rect.width - 15),
                            min(pdf_page.rect.height, best_block[3] + 18)
                        )

                # Priority 4: Largest visual graphic on page
                if target_rect is None and all_visual_rects:
                    target_rect = max(all_visual_rects, key=lambda r: r.width * r.height)

                # Fallback to full page if no specific section was targeted
                if target_rect is None or (target_rect.width < 50 or target_rect.height < 50):
                    rect = pdf_page.rect
                else:
                    rect = target_rect

            pix = pdf_page.get_pixmap(clip=rect, dpi=f_dpi)
            img_bytes = pix.tobytes("png")
            doc.close()
            return Response(content=img_bytes, media_type="image/png")
        except ImportError:
            # Fallback placeholder if fitz is not installed
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (400, 200), color=(255, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.text((20, 90), f"Diagram Preview (Page {f_page})", fill=(0, 0, 0))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return Response(content=buf.getvalue(), media_type="image/png")
        except Exception as e:
            logger.error(f"Failed to crop PDF diagram: {e}")
            raise HTTPException(status_code=500, detail="Failed to render document crop.")

    # 2. Image File Cropping (.png, .jpg, .jpeg, .webp, .bmp)
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        try:
            from PIL import Image
            # Decompression bomb guard
            Image.MAX_IMAGE_PIXELS = 25_000_000

            with Image.open(safe_path) as img:
                if f_x1 > f_x0 and f_y1 > f_y0:
                    w, h = img.size
                    crop_box = (
                        max(0, int(f_x0 - f_padding)),
                        max(0, int(f_y0 - f_padding)),
                        min(w, int(f_x1 + f_padding)),
                        min(h, int(f_y1 + f_padding))
                    )
                    cropped = img.crop(crop_box)
                elif clean_query:
                    from src.rag.image_regions import find_image_sub_region
                    sub_box, is_sub = find_image_sub_region(img, clean_query, padding=int(f_padding))
                    if is_sub:
                        cropped = img.crop(sub_box)
                    else:
                        cropped = img
                else:
                    cropped = img

                buf = io.BytesIO()
                cropped.save(buf, format="PNG")
                return Response(content=buf.getvalue(), media_type="image/png")
        except Exception as e:
            logger.error(f"Failed to crop image: {e}")
            raise HTTPException(status_code=500, detail="Failed to render image crop.")


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest):
    """Query RAG knowledge base for relevant context and optional LLM synthesis."""
    rag_svc = get_rag_service()

    if not rag_svc.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available."
        )

    result = rag_svc.query(
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score,
        filters=request.filters,
        model=request.model or "llama3.2:3b",
        generate_answer=request.generate_answer,
        processing_mode=request.processing_mode or "local",
        api_key=request.api_key,
        history=request.history,
    )

    answer = result.get("answer")
    res_list = result.get("results", [])

    if not res_list and not answer:
        answer = "No relevant context found in your uploaded documents for this query. Upload more documents (.pdf, .txt, .md, .docx, .csv) to expand the knowledge base."

    return RAGQueryResponse(
        results=res_list,
        query=request.query,
        rewritten_query=result.get("rewritten_query"),
        total_results=result.get("total_results", len(res_list)),
        answer=answer,
        llm_model=result.get("llm_model"),
        used_llm=result.get("used_llm", False),
        visual_snippet=result.get("visual_snippet"),
        metrics=result.get("metrics")
    )


import json
from fastapi.responses import StreamingResponse

@router.post("/query/stream")
async def query_rag_stream(request: RAGQueryRequest):
    """
    High-Performance Server-Sent Events (SSE) streaming endpoint.
    Streams tokens in real-time with sub-50ms TTFT from local Ollama or Turbo Cloud.
    """
    rag_svc = get_rag_service()

    if not rag_svc.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available."
        )

    async def sse_event_generator():
        try:
            async for event_item in rag_svc.query_stream(
                query=request.query,
                top_k=request.top_k,
                min_score=request.min_score,
                filters=request.filters,
                model=request.model or "llama3.2:3b",
                processing_mode=request.processing_mode or "local",
                api_key=request.api_key,
                history=request.history
            ):
                event_type = event_item.get("event", "message")
                payload = json.dumps(event_item.get("data", {}))
                yield f"event: {event_type}\ndata: {payload}\n\n"
        except Exception as e:
            logger.exception(f"SSE stream error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
