"""
Document ingestion module for RAG pipeline.

Handles loading and extracting text from various file formats:
- PDF (.pdf)
- Plain text (.txt)
- Markdown (.md)
- Future: DOCX, HTML, etc.
"""

import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

from .models import Document

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""
    allowed_extensions: List[str] = None
    max_file_size_mb: int = 50
    recursive: bool = False  # Recursively scan directories
    encoding: str = "utf-8"

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [
                ".pdf", ".txt", ".md", ".csv", ".json", ".log",
                ".rst", ".html", ".xml", ".docx",
                ".png", ".jpg", ".jpeg", ".webp", ".bmp"
            ]


class DocumentIngester:
    """
    Handles document loading and text extraction.

    Supports multiple file formats with proper error handling.
    Extracts text content and basic metadata.
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        """
        Initialize document ingester.

        Args:
            config: Ingestion configuration
        """
        self.config = config or IngestionConfig()
        self._loaded_extractors = self._init_extractors()

    def _init_extractors(self) -> Dict[str, callable]:
        """Initialize file format extractors."""
        return {
            ".pdf": self._extract_pdf,
            ".txt": self._extract_txt,
            ".md": self._extract_markdown,
            ".csv": self._extract_csv,
            ".json": self._extract_json,
            ".log": self._extract_txt,
            ".rst": self._extract_txt,
            ".html": self._extract_txt,
            ".xml": self._extract_txt,
            ".docx": self._extract_docx,
            ".png": self._extract_image,
            ".jpg": self._extract_image,
            ".jpeg": self._extract_image,
            ".webp": self._extract_image,
            ".bmp": self._extract_image,
        }

    def ingest_file(self, file_path: Union[str, Path], org_id: str,
                    document_type: Optional[str] = None,
                    start_page: Optional[int] = None,
                    end_page: Optional[int] = None) -> Optional[Document]:
        """
        Ingest a single file with optional page range slicing.

        Args:
            file_path: Path to file
            org_id: Organization ID for multi-tenancy
            document_type: Type classification (auto-detected if None)
            start_page: Optional 1-indexed starting page
            end_page: Optional 1-indexed ending page

        Returns:
            Document object or None if failed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        # Check file extension
        ext = file_path.suffix.lower()
        if ext not in self.config.allowed_extensions:
            logger.warning(f"Unsupported file type: {ext} for {file_path}")
            return None

        # Check file size
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            logger.error(f"File too large: {size_mb:.1f}MB > {self.config.max_file_size_mb}MB")
            return None

        # Auto-detect document type from path or filename if not provided
        if document_type is None:
            document_type = self._detect_document_type(file_path)

        try:
            # Extract text based on file type
            if ext == ".pdf":
                content, metadata = self._extract_pdf(file_path, start_page=start_page, end_page=end_page)
            elif ext in self._loaded_extractors:
                content, metadata = self._loaded_extractors[ext](file_path)
            else:
                logger.error(f"No extractor for extension: {ext}")
                return None

            if not content or not content.strip():
                logger.warning(f"No content extracted from {file_path}")
                return None

            # Create Document object
            doc = Document(
                id=str(uuid.uuid4()),
                org_id=org_id,
                title=file_path.stem,
                source_path=str(file_path),
                document_type=document_type,
                content=content,
                metadata={
                    **metadata,
                    "file_size_bytes": file_path.stat().st_size,
                    "file_extension": ext,
                    "file_name": file_path.name,
                    "start_page": start_page,
                    "end_page": end_page,
                }
            )

            range_str = f" (Pages {start_page or 1}-{end_page or metadata.get('page_count', 1)})" if (start_page or end_page) else ""
            logger.info(f"Ingested {file_path}{range_str} ({len(content)} chars, {metadata.get('page_count', 0)} total pages)")
            return doc

        except Exception as e:
            logger.exception(f"Failed to ingest {file_path}: {e}")
            return None

    def ingest_directory(self, directory_path: Union[str, Path], org_id: str,
                         document_type: Optional[str] = None) -> List[Document]:
        """
        Ingest all supported files in a directory.

        Args:
            directory_path: Directory to scan
            org_id: Organization ID
            document_type: Override document type (auto-detected per file if None)

        Returns:
            List of successfully ingested documents
        """
        directory_path = Path(directory_path)

        if not directory_path.is_dir():
            logger.error(f"Not a directory: {directory_path}")
            return []

        documents = []
        pattern = "**/*" if self.config.recursive else "*"

        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext in self.config.allowed_extensions:
                    doc = self.ingest_file(file_path, org_id, document_type)
                    if doc:
                        documents.append(doc)

        logger.info(f"Ingested {len(documents)} documents from {directory_path}")
        return documents

    def _detect_document_type(self, file_path: Path) -> str:
        """
        Detect document type from filename or path.

        Args:
            file_path: File path

        Returns:
            Document type string
        """
        name = file_path.stem.lower()

        # Check for known keywords in filename
        type_mappings = {
            "metric": "metric_def",
            "definition": "metric_def",
            "glossary": "metric_def",
            "process": "process",
            "procedure": "process",
            "runbook": "process",
            "incident": "incident",
            "postmortem": "incident",
            "outage": "incident",
            "issue": "incident",
        }

        for keyword, doc_type in type_mappings.items():
            if keyword in name:
                return doc_type

        # Check directory path
        parent = file_path.parent.name.lower()
        if "process" in parent or "procedure" in parent:
            return "process"
        if "incident" in parent or "postmortem" in parent:
            return "incident"
        if "metric" in parent or "definition" in parent:
            return "metric_def"

        # Default
        return "other"

    def _extract_pdf(self, file_path: Path, start_page: Optional[int] = None, end_page: Optional[int] = None) -> tuple[str, dict]:
        """
        Extract complete, high-fidelity content from every page of a PDF file.
        Extracts:
        - Structured text in reading order
        - Formatted Markdown tables
        - Embedded images, diagrams, and vector schematics with captions and visual analysis
        - Handles scanned pages with image rendering fallback
        """
        pages = []
        pages_data = []
        metadata = {
            "page_count": 0,
            "author": None,
            "title": None,
            "creation_date": None,
            "pages_data": [],
        }

        # 1. Primary Engine: PyMuPDF (fitz) for deep multi-page multimodal extraction
        try:
            import fitz
            doc = fitz.open(str(file_path))
            total_pages = len(doc)
            metadata["page_count"] = total_pages
            if doc.metadata:
                metadata["author"] = doc.metadata.get("author")
                metadata["title"] = doc.metadata.get("title")
                metadata["creation_date"] = doc.metadata.get("creationDate")

            s_idx = max(0, (start_page - 1)) if start_page else 0
            e_idx = min(total_pages, end_page) if end_page else total_pages

            for p_num in range(s_idx, e_idx):
                page = doc[p_num]
                page_number = p_num + 1

                # 1. Text Extraction in natural reading order
                page_text = page.get_text("text") or ""
                text_clean = page_text.strip()

                # 2. Table Extraction using PyMuPDF TableFinder
                tables_md = []
                try:
                    tabs = page.find_tables()
                    if tabs and hasattr(tabs, "tables"):
                        for t_idx, tab in enumerate(tabs.tables):
                            extracted = tab.extract()
                            if extracted:
                                md = _table_to_markdown(extracted)
                                if md:
                                    tables_md.append(f"Table {t_idx + 1} (Page {page_number}):\n{md}")
                except Exception as e:
                    logger.debug(f"Table detection on page {page_number}: {e}")

                # 3. Visual Elements (Drawings, Schematics, Embedded Images)
                visual_elements = []
                has_images = False
                has_drawings = False

                # A. Vector Drawings (Flowcharts, block diagrams, circuits)
                try:
                    drawings = page.get_drawings()
                    if drawings and len(drawings) > 0:
                        has_drawings = True
                        sig_drawings = [d for d in drawings if d.get("rect") and (d["rect"].width * d["rect"].height) > 1000]
                        if sig_drawings:
                            d_caption = _find_caption_near_bbox(page, sig_drawings[0]["rect"])
                            visual_elements.append({
                                "idx": 1,
                                "visual_type": "Vector Schematic / Architecture Diagram",
                                "width": int(sig_drawings[0]["rect"].width),
                                "height": int(sig_drawings[0]["rect"].height),
                                "aspect_ratio": "Vector Layout",
                                "caption": d_caption or f"Diagram / Schematic on Page {page_number}",
                                "description": f"Vector-rendered illustration or flowchart on Page {page_number} with {len(sig_drawings)} geometric shapes and connectors.",
                            })
                except Exception:
                    pass

                # B. Embedded Raster Images (Figures, charts, photos)
                try:
                    image_infos = page.get_image_info(xrefs=True)
                    if image_infos:
                        has_images = True
                        for img_idx, img_info in enumerate(image_infos):
                            bbox = img_info.get("bbox")
                            w = img_info.get("width", 0)
                            h = img_info.get("height", 0)
                            # Skip tiny icons or decoration (< 45x45)
                            if w < 45 and h < 45:
                                continue

                            caption = _find_caption_near_bbox(page, bbox)
                            xref = img_info.get("xref")
                            img_bytes = None
                            if xref and xref > 0:
                                try:
                                    base_img = doc.extract_image(xref)
                                    if base_img:
                                        img_bytes = base_img.get("image")
                                except Exception:
                                    pass

                            vis_info = _analyze_visual(
                                img_bytes=img_bytes,
                                w=w,
                                h=h,
                                bbox=bbox,
                                caption=caption,
                                page_num=page_number,
                                idx=len(visual_elements) + 1
                            )
                            visual_elements.append(vis_info)
                except Exception:
                    pass

                # C. Fallback for scanned pages (low selectable text + visuals present)
                if len(text_clean) < 40 and (has_images or has_drawings):
                    try:
                        pix = page.get_pixmap(dpi=150)
                        vis_info = _analyze_visual(
                            img_bytes=pix.tobytes("png"),
                            w=pix.width,
                            h=pix.height,
                            caption=f"Scanned Document / Graphic Layout on Page {page_number}",
                            page_num=page_number,
                            idx=len(visual_elements) + 1
                        )
                        visual_elements.append(vis_info)
                    except Exception:
                        pass

                # Assemble page with distinct sections
                page_sections = []
                if text_clean:
                    page_sections.append(f"=== PAGE {page_number} - TEXT CONTENT ===\n{text_clean}")
                if tables_md:
                    page_sections.append(f"=== PAGE {page_number} - STRUCTURED TABLES ===\n" + "\n\n".join(tables_md))
                if visual_elements:
                    vis_lines = []
                    for v in visual_elements:
                        vis_lines.append(
                            f"Figure {v.get('idx', 1)} [{v.get('visual_type', 'Diagram')} | Resolution: {v.get('width', 0)}x{v.get('height', 0)} px]:\n"
                            f"- Caption / Context: {v.get('caption', 'Figure')}\n"
                            f"- Visual Details: {v.get('description', '')}"
                        )
                    page_sections.append(f"=== PAGE {page_number} - VISUAL DIAGRAMS & FIGURES ===\n" + "\n\n".join(vis_lines))

                combined_page_text = "\n\n".join(page_sections).strip()
                if not combined_page_text:
                    combined_page_text = f"=== PAGE {page_number} ===\n[Blank or unreadable page]"

                pages.append(f"[Page {page_number}]\n" + combined_page_text)
                pages_data.append({
                    "page_number": page_number,
                    "text": combined_page_text,
                    "has_images": has_images,
                    "has_drawings": has_drawings,
                    "has_tables": len(tables_md) > 0,
                    "tables_count": len(tables_md),
                    "visual_elements": visual_elements,
                    "char_count": len(combined_page_text),
                })

            doc.close()
            if pages:
                metadata["page_range"] = f"Pages {s_idx + 1}-{e_idx}"
                metadata["pages_data"] = pages_data
                return "\n\n".join(pages), metadata
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"fitz PDF extraction failed for {file_path}: {e}")

        # 2. PyPDF2 Fallback
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                metadata["page_count"] = total_pages
                s_idx = max(0, (start_page - 1)) if start_page else 0
                e_idx = min(total_pages, end_page) if end_page else total_pages

                for p_num in range(s_idx, e_idx):
                    text = reader.pages[p_num].extract_text() or ""
                    text_clean = text.strip()
                    if text_clean:
                        pages.append(f"[Page {p_num + 1}]\n=== PAGE {p_num + 1} - TEXT CONTENT ===\n" + text_clean)
                        pages_data.append({
                            "page_number": p_num + 1,
                            "text": f"=== PAGE {p_num + 1} - TEXT CONTENT ===\n" + text_clean,
                            "has_images": False,
                            "has_drawings": False,
                            "has_tables": False,
                            "char_count": len(text_clean),
                        })
            if pages:
                metadata["page_range"] = f"Pages {s_idx + 1}-{e_idx}"
                metadata["pages_data"] = pages_data
                return "\n\n".join(pages), metadata
        except Exception as e:
            logger.warning(f"PyPDF2 extraction fallback failed: {e}")

        # 3. pypdf Fallback
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            total_pages = len(reader.pages)
            metadata["page_count"] = total_pages
            s_idx = max(0, (start_page - 1)) if start_page else 0
            e_idx = min(total_pages, end_page) if end_page else total_pages

            for p_num in range(s_idx, e_idx):
                text = reader.pages[p_num].extract_text() or ""
                text_clean = text.strip()
                if text_clean:
                    pages.append(f"[Page {p_num + 1}]\n=== PAGE {p_num + 1} - TEXT CONTENT ===\n" + text_clean)
                    pages_data.append({
                        "page_number": p_num + 1,
                        "text": f"=== PAGE {p_num + 1} - TEXT CONTENT ===\n" + text_clean,
                        "has_images": False,
                        "has_drawings": False,
                        "has_tables": False,
                        "char_count": len(text_clean),
                    })
            if pages:
                metadata["page_range"] = f"Pages {s_idx + 1}-{e_idx}"
                metadata["pages_data"] = pages_data
                return "\n\n".join(pages), metadata
        except Exception as e:
            logger.warning(f"pypdf extraction fallback failed: {e}")

        content = "\n\n".join(pages)
        if not content:
            raise ValueError(f"Could not extract readable text from PDF: {file_path}")
        metadata["pages_data"] = pages_data
        return content, metadata

    def _extract_txt(self, file_path: Path) -> tuple[str, dict]:
        """Extract text from plain text file."""
        content = None
        used_enc = self.config.encoding
        for encoding in [self.config.encoding, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    content = f.read()
                used_enc = encoding
                break
            except Exception:
                continue

        if content is None:
            raise ValueError(f"Unable to decode text file: {file_path}")

        metadata = {
            "file_size": file_path.stat().st_size,
            "encoding": used_enc,
        }
        return content, metadata

    def _extract_markdown(self, file_path: Path) -> tuple[str, dict]:
        """Extract text from Markdown file."""
        content, metadata = self._extract_txt(file_path)
        metadata["file_type"] = "markdown"
        return content, metadata

    def _extract_csv(self, file_path: Path) -> tuple[str, dict]:
        """Extract text from CSV file with column structure."""
        try:
            import csv
            rows_summary = []
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    rows_summary.append(f"Headers: {', '.join(headers)}")
                    for idx, row in enumerate(reader):
                        if idx < 500:
                            item_strs = [f"{h}: {v}" for h, v in zip(headers, row) if v]
                            rows_summary.append(f"Row {idx+1}: {'; '.join(item_strs)}")
                        else:
                            break
            content = "\n".join(rows_summary)
            return content, {"file_type": "csv", "file_size": file_path.stat().st_size}
        except Exception:
            return self._extract_txt(file_path)

    def _extract_json(self, file_path: Path) -> tuple[str, dict]:
        """Extract text from JSON file."""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            formatted = json.dumps(data, indent=2)
            return formatted, {"file_type": "json", "file_size": file_path.stat().st_size}
        except Exception:
            return self._extract_txt(file_path)

    def _extract_docx(self, file_path: Path) -> tuple[str, dict]:
        """Extract text and structured tables from DOCX file."""
        try:
            import docx
            doc = docx.Document(str(file_path))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            
            # Extract structured tables
            tables_md = []
            for t_idx, table in enumerate(doc.tables):
                t_rows = []
                for row in table.rows:
                    t_rows.append([cell.text.strip().replace("\n", " ") for cell in row.cells])
                if t_rows:
                    md_table = _table_to_markdown(t_rows)
                    if md_table:
                        tables_md.append(f"Table {t_idx + 1}:\n{md_table}")

            sections = []
            if paras:
                sections.append("=== DOCUMENT TEXT CONTENT ===\n" + "\n\n".join(paras))
            if tables_md:
                sections.append("=== STRUCTURED TABLES ===\n" + "\n\n".join(tables_md))

            content = "\n\n".join(sections)
            return content, {
                "file_type": "docx",
                "paragraphs_count": len(paras),
                "tables_count": len(tables_md)
            }
        except Exception:
            return self._extract_txt(file_path)

    def _extract_image(self, file_path: Path) -> tuple[str, dict]:
        """Deep multimodal visual analysis and text extraction from standalone image files."""
        metadata = {
            "file_type": "image",
            "file_size": file_path.stat().st_size,
            "page_count": 1,
            "page": 1,
        }

        vis_info = _analyze_visual(file_path=file_path, page_num=1, idx=1)
        metadata.update({
            "width": vis_info.get("width"),
            "height": vis_info.get("height"),
            "visual_type": vis_info.get("visual_type"),
            "aspect_ratio": vis_info.get("aspect_ratio"),
        })

        content = (
            f"[Visual Document: {file_path.name}]\n"
            f"=== VISUAL METRICS & TYPE ===\n"
            f"Type: {vis_info.get('visual_type')}\n"
            f"Resolution: {vis_info.get('width')}x{vis_info.get('height')} px ({vis_info.get('aspect_ratio')})\n\n"
            f"=== VISUAL CONTENT ANALYSIS ===\n"
            f"{vis_info.get('description')}"
        )
        return content, metadata


# =========================================================================
# MULTIMODAL & TABLE EXTRACTION HELPERS
# =========================================================================

def _table_to_markdown(table_data: list) -> str:
    """Convert a 2D list of table cells into a clean, valid Markdown table."""
    if not table_data or len(table_data) < 1:
        return ""
    clean_rows = []
    for r in table_data:
        if not r:
            continue
        cells = [str(c or "").strip().replace("\n", " ").replace("|", "\\|") for c in r]
        if any(cells):
            clean_rows.append(cells)
    if not clean_rows:
        return ""

    headers = clean_rows[0]
    num_cols = len(headers)
    if num_cols == 0:
        return ""

    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * num_cols) + " |")
    for row in clean_rows[1:]:
        padded = list(row)
        while len(padded) < num_cols:
            padded.append("")
        lines.append("| " + " | ".join(padded[:num_cols]) + " |")
    return "\n".join(lines)


def _find_caption_near_bbox(page, bbox, margin=60) -> str:
    """Find text near an image/drawing bounding box that resembles a caption or diagram label."""
    try:
        import fitz
        if not bbox:
            return ""
        p_rect = page.rect
        search_rect = fitz.Rect(
            max(0, bbox[0] - 30),
            max(0, bbox[1] - 40),
            min(p_rect.width, bbox[2] + 30),
            min(p_rect.height, bbox[3] + margin)
        )
        near_text = page.get_text("text", clip=search_rect).strip()
        if not near_text:
            return ""

        import re
        lines = [line.strip() for line in near_text.splitlines() if line.strip()]
        for line in lines:
            if re.match(r'^(?:Figure|Fig\.|Diagram|Chart|Illustration|Photo|Image|Table)\b', line, re.I):
                return line[:200]
        if lines:
            return lines[0][:150]
    except Exception:
        pass
    return ""


def _analyze_visual(img_bytes=None, w=0, h=0, bbox=None, caption="", page_num=1, idx=1, file_path=None) -> Dict[str, Any]:
    """Analyze image geometric, computer vision, and multimodal semantic properties."""
    aspect_ratio = "1:1 (Square)"
    if w > 0 and h > 0:
        ratio = w / h
        if ratio > 1.3:
            aspect_ratio = f"{ratio:.1f}:1 (Landscape)"
        elif ratio < 0.77:
            aspect_ratio = f"1:{(1/ratio):.1f} (Portrait)"
        else:
            aspect_ratio = f"{ratio:.2f}:1 (Standard)"

    visual_type = "Embedded Graphic / Diagram"
    details = []

    try:
        import io
        import numpy as np
        import cv2
        from PIL import Image

        pil_img = None
        if img_bytes:
            pil_img = Image.open(io.BytesIO(img_bytes))
        elif file_path and Path(file_path).exists():
            pil_img = Image.open(file_path)

        if pil_img:
            w, h = pil_img.size
            details.append(f"Resolution: {w}x{h} px")
            cv_img = np.array(pil_img.convert('RGB'))
            gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = float(np.sum(edges > 0) / (w * h))

            if edge_density > 0.045:
                visual_type = "Technical Schematic / Architectural Diagram / Flowchart"
            elif edge_density > 0.015:
                visual_type = "Chart / Graph / Data Plot"
            else:
                visual_type = "Photographic Image / Illustration"
            details.append(f"Structural Classification: {visual_type}")
    except Exception as e:
        logger.debug(f"CV analysis exception: {e}")

    # Optional Cloud Vision / Local Multimodal LLM analysis
    ai_description = None
    try:
        import base64
        import httpx

        b64_data = None
        if img_bytes and len(img_bytes) < 3 * 1024 * 1024:
            b64_data = base64.b64encode(img_bytes).decode("utf-8")
        elif file_path and Path(file_path).exists() and Path(file_path).stat().st_size < 3 * 1024 * 1024:
            b64_data = base64.b64encode(Path(file_path).read_bytes()).decode("utf-8")

        if b64_data:
            gem_key = os.getenv("GEMINI_API_KEY")
            if gem_key:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gem_key}",
                        json={
                            "contents": [{
                                "parts": [
                                    {"text": "Describe this document diagram/image in 2 sentences. Note components, labels, and workflow."},
                                    {"inline_data": {"mime_type": "image/png", "data": b64_data}}
                                ]
                            }]
                        }
                    )
                    if resp.status_code == 200:
                        ai_description = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        pass

    desc = ai_description or (f"{visual_type} ({aspect_ratio}). " + ", ".join(details))
    return {
        "idx": idx,
        "visual_type": visual_type,
        "width": w,
        "height": h,
        "aspect_ratio": aspect_ratio,
        "caption": caption or f"Visual Element {idx} on Page {page_num}",
        "description": desc,
    }


def create_default_ingester() -> DocumentIngester:
    """Create ingester with default configuration."""
    config = IngestionConfig(
        allowed_extensions=[
            ".pdf", ".txt", ".md", ".csv", ".json", ".log",
            ".rst", ".html", ".xml", ".docx",
            ".png", ".jpg", ".jpeg", ".webp", ".bmp"
        ],
        max_file_size_mb=50,
        recursive=False
    )
    return DocumentIngester(config)
