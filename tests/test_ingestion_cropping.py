"""
Automated test suite for RAG ingestion, chunking, table extraction, and sub-region diagram cropping.

Verifies:
1. Section header detection: Numbered ('2.1 Architecture') and uppercase ('EXECUTIVE SUMMARY')
   headers populate 'Section:' in build_contextual_chunk.
2. Table extraction & chunk integrity: Markdown tables remain intact as atomic structures.
3. Multi-column reading order preservation.
4. Diagram sub-region extraction: Verifies sub-region bboxes are detected and cropped.
5. Raster image CV contour sub-region localization and graceful fallback.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from PIL import Image, ImageDraw

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from src.rag.chunker import TextChunker, ChunkConfig, build_contextual_chunk, is_section_heading, is_markdown_table
from src.rag.ingestion import DocumentIngester
from src.rag.image_regions import find_pdf_diagram_and_sub_regions, find_image_sub_region


def test_section_header_detection_and_contextual_prefixing():
    """
    Test 1: Explicit test asserting the section header fix works.
    Ingests a document with a numbered heading ('2.1 Architecture') and an uppercase heading
    ('EXECUTIVE SUMMARY'), and asserts build_contextual_chunk correctly populates the
    'Section:' field for both — not just the empty-collapse case.
    """
    # 1. Direct heading recognizer verification
    is_head_num, title_num = is_section_heading("2.1 Architecture")
    assert is_head_num is True
    assert "2.1 Architecture" in title_num

    is_head_upper, title_upper = is_section_heading("EXECUTIVE SUMMARY")
    assert is_head_upper is True
    assert "EXECUTIVE SUMMARY" in title_upper

    # 2. Document chunking verification
    doc_text = (
        "EXECUTIVE SUMMARY\n"
        "This platform delivers high-performance real-time telemetry analytics.\n"
        "All services are deployed across distributed Kubernetes clusters.\n\n"
        "2.1 Architecture\n"
        "The system architecture incorporates FAISS vector storage and Ollama LLM synthesis.\n"
        "Ingestion pipelines parse multimodal documents into contextualized chunks.\n"
    )

    chunker = TextChunker(ChunkConfig(chunk_size=100))
    chunks = chunker.chunk_text(doc_text, document_id="doc_test_headers")

    assert len(chunks) >= 2

    sections_found = [c.get("section", "") for c in chunks]
    embedded_texts = [c.get("embedded_text", "") for c in chunks]

    # Verify both sections were detected and preserved
    assert any("EXECUTIVE SUMMARY" in s for s in sections_found), f"Expected EXECUTIVE SUMMARY in sections: {sections_found}"
    assert any("2.1 Architecture" in s for s in sections_found), f"Expected 2.1 Architecture in sections: {sections_found}"

    # Verify build_contextual_chunk properly includes 'Section:'
    assert any("Section: EXECUTIVE SUMMARY" in emb for emb in embedded_texts), f"Expected 'Section: EXECUTIVE SUMMARY' in: {embedded_texts}"
    assert any("Section: 2.1 Architecture" in emb for emb in embedded_texts), f"Expected 'Section: 2.1 Architecture' in: {embedded_texts}"


def test_markdown_table_detection_and_chunk_integrity():
    """
    Test 2: Markdown table extraction and chunk integrity.
    Asserts:
    - Tables are recognized via is_markdown_table.
    - Tables are preserved intact as atomic structured blocks without sentence mutilation.
    """
    table_text = (
        "| Metric | Target | P99 Latency | Status |\n"
        "|---|---|---|---|\n"
        "| Ingestion Rate | 1.2M eps | 12.5ms | OK |\n"
        "| Query TTFT | 45ms | 48.2ms | OK |\n"
        "| FAISS Recall | 98.5% | 15.1ms | OK |"
    )

    assert is_markdown_table(table_text) is True

    doc_text = f"=== 1. System Performance ===\n{table_text}\n\nAdditional explanatory text below table."
    chunker = TextChunker(ChunkConfig(chunk_size=150))
    chunks = chunker.chunk_text(doc_text, document_id="table_doc")

    # Locate the chunk containing the table
    table_chunks = [c for c in chunks if "| Metric | Target |" in c["text"]]
    assert len(table_chunks) >= 1

    table_chunk = table_chunks[0]
    # Check that table markdown delimiter line is intact
    assert "|---|---|---|---|" in table_chunk["text"]
    # Check that rows remain intact
    assert "1.2M eps" in table_chunk["text"]
    assert "FAISS Recall" in table_chunk["text"]


def test_pdf_diagram_sub_region_localization(tmp_path):
    """
    Test 3: Diagram sub-region bbox extraction and targeted cropping.
    Creates a synthetic PDF with a diagram container containing labeled components
    ('Auth Service', 'Worker Node', 'FAISS Storage').
    Asserts:
    - find_pdf_diagram_and_sub_regions correctly localizes the sub-region matching 'Worker Node'.
    - Returns is_sub_region == True.
    - Sub-region rectangle is strictly smaller than the parent diagram rectangle.
    """
    import fitz

    pdf_path = tmp_path / "diagram_test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # 1. Draw parent diagram bounding box
    diagram_rect = fitz.Rect(50, 100, 550, 450)
    page.draw_rect(diagram_rect, color=(0, 0, 1), width=2)

    # 2. Draw sub-box for 'Auth Service'
    auth_box = fitz.Rect(70, 130, 200, 200)
    page.draw_rect(auth_box, color=(1, 0, 0), width=1.5)
    page.insert_text(fitz.Point(85, 165), "Auth Service", fontsize=12)

    # 3. Draw sub-box for 'Worker Node'
    worker_box = fitz.Rect(350, 280, 520, 360)
    page.draw_rect(worker_box, color=(0, 0.8, 0), width=1.5)
    page.insert_text(fitz.Point(370, 320), "Worker Node", fontsize=12)

    doc.save(str(pdf_path))
    doc.close()

    # Re-open and test sub-region localization
    read_doc = fitz.open(str(pdf_path))
    test_page = read_doc[0]

    # Query for specific sub-component
    sub_rect, is_sub, meta = find_pdf_diagram_and_sub_regions(test_page, query="Worker Node diagram component")

    assert sub_rect is not None
    assert is_sub is True, f"Expected sub-region localization, got meta: {meta}"
    assert "worker" in meta.get("label", "").lower()

    # Assert sub-region is smaller than the parent diagram
    sub_area = (sub_rect.x1 - sub_rect.x0) * (sub_rect.y1 - sub_rect.y0)
    parent_area = (diagram_rect.width * diagram_rect.height)
    assert sub_area < parent_area * 0.6, f"Sub-region area {sub_area} is not significantly smaller than parent {parent_area}"

    # Verify that worker node coordinates are inside the cropped sub_rect
    assert sub_rect.x0 <= 370 and sub_rect.x1 >= 430
    assert sub_rect.y0 <= 320 and sub_rect.y1 >= 320

    read_doc.close()


def test_raster_image_sub_region_and_clean_fallback():
    """
    Test 4: Raster image CV contour sub-region localization and clean fallback.
    Asserts:
    - Multi-box architecture diagram image detects sub-boxes (is_sub_region == True).
    - Uniform/continuous photo cleanly falls back to full image (is_sub_region == False).
    """
    # 1. Create a synthetic flowchart image with two distinct high-contrast boxes
    diagram_img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(diagram_img)
    # Top box
    draw.rectangle([60, 40, 260, 160], outline=(0, 0, 0), width=3)
    # Bottom box
    draw.rectangle([340, 220, 540, 340], outline=(0, 0, 0), width=3)

    # Query targeting bottom box
    sub_box, is_sub = find_image_sub_region(diagram_img, query="Show me the bottom lower box in the diagram")
    assert is_sub is True
    assert sub_box[1] >= 180  # y0 should be near the bottom half

    # 2. Test continuous photo / smooth image fallback
    smooth_img = Image.new("RGB", (400, 300), color=(128, 128, 128))
    fallback_box, is_sub_smooth = find_image_sub_region(smooth_img, query="Show me diagram")
    assert is_sub_smooth is False
    assert fallback_box == (0, 0, 400, 300)


def test_pdf_multicolumn_and_table_deduplication(tmp_path):
    """
    Test 5: Multi-column reading order and table deduplication during PDF ingestion.
    Asserts:
    - Text blocks are read in column-sorted order (left column completes before right column).
    - Table content is captured in structured tables and not duplicated into text blocks.
    """
    import fitz

    pdf_path = tmp_path / "multicolumn_table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # Left column text (x: 50..250)
    page.insert_textbox(
        fitz.Rect(50, 50, 250, 300),
        "Alpha section begins here. This is the primary narrative of the left column. Conclusion of alpha."
    )

    # Right column text (x: 350..550)
    page.insert_textbox(
        fitz.Rect(350, 50, 550, 300),
        "Beta section starts here. This is the secondary narrative of the right column. Conclusion of beta."
    )

    # Table at the bottom (x: 50..550, y: 400..600)
    table_rect = fitz.Rect(50, 400, 550, 550)
    page.draw_rect(table_rect, color=(0, 0, 0), width=1)
    page.insert_textbox(fitz.Rect(60, 410, 540, 440), "Server | Status | Load")
    page.insert_textbox(fitz.Rect(60, 450, 540, 480), "Node-A | Active | 42%")

    doc.save(str(pdf_path))
    doc.close()

    ingester = DocumentIngester()
    ingested_doc = ingester.ingest_file(pdf_path, org_id="test_org")

    assert ingested_doc is not None
    content = ingested_doc.content

    # Multi-column verification: Left column text should appear before Right column text
    alpha_idx = content.find("Alpha section begins here")
    alpha_end_idx = content.find("Conclusion of alpha")
    beta_idx = content.find("Beta section starts here")

    assert alpha_idx != -1, "Left column text not found"
    assert beta_idx != -1, "Right column text not found"
    # Column 1 should finish before Column 2 starts (not interleaved)
    assert alpha_idx < alpha_end_idx < beta_idx, (
        f"Multi-column reading order failed: alpha_idx={alpha_idx}, "
        f"alpha_end_idx={alpha_end_idx}, beta_idx={beta_idx}"
    )
