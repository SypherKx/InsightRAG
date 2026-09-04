"""
RAG router — Document upload and context retrieval.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Query

from ..dependencies import get_rag_service
from ..models.requests import RAGQueryRequest
from ..models.responses import RAGQueryResponse, RAGUploadResponse

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


@router.post("/documents", response_model=RAGUploadResponse)
async def upload_rag_documents(
    files: List[UploadFile] = File(...),
    start_page: Optional[int] = Form(None),
    end_page: Optional[int] = Form(None),
):
    """Upload documents to the RAG knowledge base with sanitized paths and strict extension checks."""
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

        # Ingest documents into FAISS vector database
        stats = rag_svc.ingest_documents(
            saved_paths,
            start_page=start_page,
            end_page=end_page
        )

        return RAGUploadResponse(
            documents_ingested=stats.get("documents_ingested", 0),
            chunks_created=stats.get("chunks_created", 0),
            errors=stats.get("errors", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document upload.")


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
    from ..utils.security import sanitize_filename, validate_safe_path

    upload_dir = Path("./uploads")
    
    # 1. Sanitize input doc_name
    safe_doc_name = sanitize_filename(doc_name)
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
            page_idx = min(max(0, page - 1), len(doc) - 1)
            pdf_page = doc[page_idx]

            # Mode A: User supplied explicit bounding box coordinates
            if x1 > x0 and y1 > y0:
                rect = fitz.Rect(
                    max(0, x0 - padding),
                    max(0, y0 - padding),
                    min(pdf_page.rect.width, x1 + padding),
                    min(pdf_page.rect.height, y1 + padding)
                )
            else:
                # Mode B: Intelligent Diagram / Figure Region Localization
                target_rect = None
                
                # 1. Collect all vector drawings on page
                drawings = pdf_page.get_drawings()
                drawing_rects = [d["rect"] for d in drawings if d.get("rect") and (d["rect"].width * d["rect"].height) > 600]

                # 2. Collect all embedded images on page
                image_infos = pdf_page.get_image_info(xrefs=True)
                image_rects = [fitz.Rect(img["bbox"]) for img in image_infos if img.get("bbox") and (fitz.Rect(img["bbox"]).width * fitz.Rect(img["bbox"]).height) > 600]

                all_visual_rects = drawing_rects + image_rects

                # 3. If query provided, search for targeted figure/diagram keyword location
                matched_hit_rects = []
                if query:
                    import re
                    # Extract meaningful search terms (remove stopwords)
                    stopwords = {"the", "a", "an", "is", "of", "and", "or", "in", "to", "for", "with", "diagram", "diagrams", "figure", "figures", "chart", "show", "give", "me", "what", "how", "part", "image", "draw", "preview"}
                    keywords = [w for w in re.findall(r'[a-zA-Z0-9]+', query.lower()) if len(w) > 2 and w not in stopwords]
                    
                    # Search for keywords and figure/diagram captions
                    for kw in keywords[:4]:
                        hits = pdf_page.search_for(kw)
                        matched_hit_rects.extend(hits)
                    
                    # Also search for explicit Figure / Diagram captions
                    for caption_term in ["figure", "fig.", "diagram", "table", "illustration", "circuit"]:
                        matched_hit_rects.extend(pdf_page.search_for(caption_term))

                # 4. If search hits found, find the closest visual element (drawing or image)
                if matched_hit_rects and all_visual_rects:
                    best_visual = None
                    min_dist = float("inf")
                    for hit in matched_hit_rects:
                        for vrect in all_visual_rects:
                            # Distance between hit center and visual rect center
                            dist = ((hit.x0 - vrect.x0)**2 + (hit.y0 - vrect.y0)**2)**0.5
                            if dist < min_dist:
                                min_dist = dist
                                best_visual = vrect
                    if best_visual and min_dist < 400:
                        # Include caption in the crop bounding box
                        target_rect = fitz.Rect(
                            min(best_visual.x0, min(h.x0 for h in matched_hit_rects if abs(h.y0 - best_visual.y0) < 300)),
                            min(best_visual.y0, min(h.y0 for h in matched_hit_rects if abs(h.y0 - best_visual.y0) < 300)),
                            max(best_visual.x1, max(h.x1 for h in matched_hit_rects if abs(h.y0 - best_visual.y0) < 300)),
                            max(best_visual.y1, max(h.y1 for h in matched_hit_rects if abs(h.y0 - best_visual.y0) < 300))
                        )
                    elif best_visual:
                        target_rect = best_visual
                elif matched_hit_rects and not all_visual_rects:
                    # Focus crop around the matched text/paragraph region
                    min_x = min(h.x0 for h in matched_hit_rects)
                    min_y = min(h.y0 for h in matched_hit_rects)
                    max_x = max(h.x1 for h in matched_hit_rects)
                    max_y = max(h.y1 for h in matched_hit_rects)
                    target_rect = fitz.Rect(
                        max(0, min_x - 30),
                        max(0, min_y - 60),
                        min(pdf_page.rect.width, max_x + 30),
                        min(pdf_page.rect.height, max_y + 180)
                    )
                elif all_visual_rects:
                    # Pick largest visual element on the page
                    target_rect = max(all_visual_rects, key=lambda r: r.width * r.height)

                # Fallback to full page if no sub-region detected
                if target_rect is None or (target_rect.width < 50 or target_rect.height < 50):
                    rect = pdf_page.rect
                else:
                    rect = fitz.Rect(
                        max(0, target_rect.x0 - padding),
                        max(0, target_rect.y0 - padding),
                        min(pdf_page.rect.width, target_rect.x1 + padding),
                        min(pdf_page.rect.height, target_rect.y1 + padding)
                    )

            pix = pdf_page.get_pixmap(clip=rect, dpi=dpi)
            img_bytes = pix.tobytes("png")
            doc.close()
            return Response(content=img_bytes, media_type="image/png")
        except ImportError:
            # Fallback placeholder if fitz is not installed
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (400, 200), color=(255, 240, 240))
            draw = ImageDraw.Draw(img)
            draw.text((20, 90), f"Diagram Preview (Page {page})", fill=(0, 0, 0))
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
                if x1 > x0 and y1 > y0:
                    w, h = img.size
                    crop_box = (
                        max(0, int(x0 - padding)),
                        max(0, int(y0 - padding)),
                        min(w, int(x1 + padding)),
                        min(h, int(y1 + padding))
                    )
                    cropped = img.crop(crop_box)
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
        total_results=result.get("total_results", len(res_list)),
        answer=answer,
        llm_model=result.get("llm_model"),
        used_llm=result.get("used_llm", False),
        visual_snippet=result.get("visual_snippet"),
    )
