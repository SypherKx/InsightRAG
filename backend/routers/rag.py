"""
RAG router — Document upload and context retrieval.
"""

import logging
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException

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
async def upload_rag_documents(files: List[UploadFile] = File(...)):
    """Upload documents to the RAG knowledge base."""
    rag_svc = get_rag_service()

    if not rag_svc.is_available:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available. Install sentence-transformers and faiss-cpu."
        )

    upload_dir = Path("./uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    try:
        for file in files:
            safe_name = Path(file.filename).name
            target_path = upload_dir / safe_name
            content = await file.read()
            target_path.write_bytes(content)
            saved_paths.append(str(target_path))

        # Ingest documents into FAISS vector database
        stats = rag_svc.ingest_documents(saved_paths)

        return RAGUploadResponse(
            documents_ingested=stats.get("documents_ingested", 0),
            chunks_created=stats.get("chunks_created", 0),
            errors=stats.get("errors", 0),
        )
    except Exception as e:
        logger.exception(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Query
import io

@router.get("/crop")
async def get_diagram_crop(
    doc_name: str = Query(..., description="Document file name in uploads directory"),
    page: int = Query(1, ge=1, description="1-indexed page number"),
    x0: float = Query(0.0),
    y0: float = Query(0.0),
    x1: float = Query(0.0),
    y1: float = Query(0.0),
    padding: int = Query(40, ge=0),
    dpi: int = Query(160, ge=72, le=300)
):
    """
    Crops and renders a specific sub-region / diagram of a PDF or image document.
    Returns high-resolution PNG image bytes.
    """
    upload_dir = Path("./uploads")
    safe_doc_name = Path(doc_name).name

    if safe_doc_name != doc_name or safe_doc_name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid document path.")

    try:
        file_path = next(
            (candidate for candidate in upload_dir.iterdir() if candidate.is_file() and candidate.name == safe_doc_name),
            None,
        )
    except FileNotFoundError:
        file_path = None

    if file_path is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found.")

    ext = file_path.suffix.lower()

    # 1. PDF File Cropping
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            page_idx = min(max(0, page - 1), len(doc) - 1)
            pdf_page = doc[page_idx]

            # If specific bounding box provided
            if x1 > x0 and y1 > y0:
                rect = fitz.Rect(
                    max(0, x0 - padding),
                    max(0, y0 - padding),
                    min(pdf_page.rect.width, x1 + padding),
                    min(pdf_page.rect.height, y1 + padding)
                )
            else:
                # Auto-detect drawings/diagrams or take upper-middle visual band
                rect = pdf_page.rect

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
            raise HTTPException(status_code=500, detail=str(e))

    # 2. Image File Cropping (.png, .jpg, .jpeg)
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        try:
            from PIL import Image
            with Image.open(file_path) as img:
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
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"Visual cropping is not supported for {ext} files.")


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
