"""
Visual Region of Interest (ROI) and Sub-Region Extraction module.

Handles:
1. Detecting diagrams, flowcharts, vector schematics, and embedded figures in documents.
2. Localizing fine-grained sub-regions within multi-part diagrams based on text labels,
   component shapes, and query keywords.
3. Computer-vision contour analysis for raster diagram sub-box localization with clean
   fallback to full images for photographs and continuous plots.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

STOPWORDS = {
    'the', 'a', 'an', 'is', 'of', 'and', 'or', 'in', 'to', 'for', 'with',
    'diagram', 'diagrams', 'figure', 'figures', 'chart', 'charts', 'show', 'give',
    'me', 'what', 'how', 'part', 'image', 'images', 'photo', 'photos', 'picture',
    'pictures', 'pic', 'pics', 'preview', 'crop', 'snapshot', 'document', 'doc',
    'pdf', 'file', 'page', 'section', 'portion', 'content', 'view', 'display',
    'take', 'send', 'tell', 'about', 'write', 'extract', 'find', 'please', 'can',
    'you', 'there', 'this', 'that', 'from', 'here', 'box', 'node', 'component'
}


def extract_query_keywords(query: str) -> List[str]:
    """Extract salient, non-stopword alphanumeric keywords from a user query."""
    if not query:
        return []
    words = re.findall(r'[a-zA-Z0-9_\-\.]+', str(query).lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


def find_pdf_diagram_and_sub_regions(
    page,
    query: str = "",
    padding: float = 25.0
) -> Tuple[Optional[Any], bool, Dict[str, Any]]:
    """
    Locate diagram on a PyMuPDF page, and if the query specifies a sub-component,
    crop precisely to that sub-region rather than the entire diagram.

    Args:
        page: fitz.Page object
        query: User query string
        padding: Padding around localized bounds in points/pixels

    Returns:
        Tuple of:
        - target_rect: fitz.Rect or None
        - is_sub_region: True if cropped to a specific sub-component, False if whole diagram
        - meta: Dictionary with details (label, confidence, parent_bbox, sub_bbox)
    """
    import fitz

    keywords = extract_query_keywords(query)
    p_rect = page.rect

    # 1. Collect all visual elements (drawings and embedded images)
    drawings = page.get_drawings()
    drawing_rects = [
        d["rect"] for d in drawings
        if d.get("rect") and (d["rect"].width * d["rect"].height) > 1000
        and d["rect"].width > 30 and d["rect"].height > 20
    ]

    image_infos = page.get_image_info(xrefs=True)
    image_rects = [
        fitz.Rect(img["bbox"]) for img in image_infos
        if img.get("bbox") and (fitz.Rect(img["bbox"]).width * fitz.Rect(img["bbox"]).height) > 1200
    ]

    all_visual_rects = drawing_rects + image_rects
    if not all_visual_rects:
        return None, False, {"error": "No visual elements on page"}

    # Find the union / largest visual container bounding box
    parent_rect = fitz.Rect(
        min(r.x0 for r in all_visual_rects),
        min(r.y0 for r in all_visual_rects),
        max(r.x1 for r in all_visual_rects),
        max(r.y1 for r in all_visual_rects)
    )

    # 2. Extract words with coordinates to locate sub-region labels inside or near visuals
    words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
    
    # Check for targeted sub-component matches
    matched_word_rects = []
    matched_keywords = []

    if keywords and words:
        for w in words:
            w_text = w[4].lower().strip(".,;:()[]{}'\"")
            w_rect = fitz.Rect(w[0], w[1], w[2], w[3])
            
            # Check if this word is inside or within 30px of any visual element
            is_in_visual = any(
                (v.x0 - 20 <= w_rect.x0 and w_rect.x1 <= v.x1 + 20 and
                 v.y0 - 20 <= w_rect.y0 and w_rect.y1 <= v.y1 + 20)
                for v in all_visual_rects
            ) or (
                parent_rect.x0 - 20 <= w_rect.x0 and w_rect.x1 <= parent_rect.x1 + 20 and
                parent_rect.y0 - 20 <= w_rect.y0 and w_rect.y1 <= parent_rect.y1 + 20
            )

            if is_in_visual:
                for kw in keywords:
                    if kw in w_text or w_text in kw:
                        matched_word_rects.append(w_rect)
                        matched_keywords.append(w[4])

    # If sub-part keyword matches found inside the visual, locate the specific sub-region!
    if matched_word_rects:
        # Compute bounding rectangle of matching words
        sub_x0 = min(r.x0 for r in matched_word_rects)
        sub_y0 = min(r.y0 for r in matched_word_rects)
        sub_x1 = max(r.x1 for r in matched_word_rects)
        sub_y1 = max(r.y1 for r in matched_word_rects)

        # Check if there is a tight vector drawing enclosing this word group (e.g. a flowchart box)
        enclosing_box = None
        for d_rect in drawing_rects:
            if (d_rect.x0 <= sub_x0 + 5 and d_rect.y0 <= sub_y0 + 5 and
                d_rect.x1 >= sub_x1 - 5 and d_rect.y1 >= sub_y1 - 5):
                # Don't pick the giant parent container
                if d_rect.width < parent_rect.width * 0.85 or d_rect.height < parent_rect.height * 0.85:
                    if enclosing_box is None or (d_rect.width * d_rect.height < enclosing_box.width * enclosing_box.height):
                        enclosing_box = d_rect

        if enclosing_box is not None:
            crop_rect = fitz.Rect(
                max(0, enclosing_box.x0 - padding),
                max(0, enclosing_box.y0 - padding),
                min(p_rect.width, enclosing_box.x1 + padding),
                min(p_rect.height, enclosing_box.y1 + padding)
            )
        else:
            # Expand word bounds comfortably with padding to frame the component box
            box_pad_x = max(padding, 35.0)
            box_pad_y = max(padding, 25.0)
            crop_rect = fitz.Rect(
                max(0, sub_x0 - box_pad_x),
                max(0, sub_y0 - box_pad_y),
                min(p_rect.width, sub_x1 + box_pad_x),
                min(p_rect.height, sub_y1 + box_pad_y)
            )

        return crop_rect, True, {
            "label": " ".join(matched_keywords[:4]),
            "is_sub_region": True,
            "parent_bbox": [parent_rect.x0, parent_rect.y0, parent_rect.x1, parent_rect.y1],
            "sub_bbox": [crop_rect.x0, crop_rect.y0, crop_rect.x1, crop_rect.y1]
        }

    # 3. Whole diagram localization (fallback if no sub-part keyword matched)
    # Search for figure / diagram caption hits to identify the most relevant diagram
    caption_hits = []
    for cap in ['figure', 'fig.', 'diagram', 'chart', 'table', 'schematic']:
        caption_hits.extend(page.search_for(cap))
    for kw in keywords[:3]:
        caption_hits.extend(page.search_for(kw))

    best_vis = None
    if caption_hits:
        min_dist = float('inf')
        for hit in caption_hits:
            for v in all_visual_rects:
                dist = ((hit.x0 - v.x0)**2 + (hit.y0 - v.y0)**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    best_vis = v

    chosen = best_vis if (best_vis and min_dist < 400) else max(all_visual_rects, key=lambda r: r.width * r.height)
    crop_rect = fitz.Rect(
        max(0, chosen.x0 - padding),
        max(0, chosen.y0 - padding),
        min(p_rect.width, chosen.x1 + padding),
        min(p_rect.height, chosen.y1 + padding)
    )

    return crop_rect, False, {
        "label": "Full Diagram",
        "is_sub_region": False,
        "parent_bbox": [chosen.x0, chosen.y0, chosen.x1, chosen.y1]
    }


def find_image_sub_region(
    pil_img,
    query: str = "",
    padding: int = 20
) -> Tuple[Tuple[int, int, int, int], bool]:
    """
    Detect sub-region bounding box inside a raster image (PNG, JPG, etc.).
    Uses OpenCV contour analysis to detect distinct boxes/components in flowcharts
    and architecture diagrams. Cleanly falls back to full image for photographs,
    gradients, or continuous plots without discrete sub-structures.

    Args:
        pil_img: PIL.Image instance
        query: User query string
        padding: Padding in pixels

    Returns:
        Tuple of ((x0, y0, x1, y1), is_sub_region)
    """
    import numpy as np
    import cv2

    w, h = pil_img.size
    full_box = (0, 0, w, h)

    keywords = extract_query_keywords(query)
    # If user didn't ask for a specific sub-region or diagram part, return full image
    if not keywords:
        return full_box, False

    try:
        cv_img = np.array(pil_img.convert('RGB'))
        gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)

        # Morphological gradient / adaptive threshold to detect structural outlines
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 4
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return full_box, False

        boxes = []
        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            # Filter for meaningful sub-module boxes:
            # - Not tiny noise (> 50x35)
            # - Not the outer full image (> 90% width or height)
            if (bw >= 50 and bh >= 35 and
                bw < w * 0.88 and bh < h * 0.88 and
                (bw * bh) > 2000):
                boxes.append((x, y, x + bw, y + bh))

        if not boxes:
            return full_box, False

        # If sub-boxes detected (e.g. flowchart or multi-box architecture diagram)
        # Check query keywords: if query mentions position/number/term, select appropriate box
        q_lower = query.lower()
        chosen_box = None

        if any(w in q_lower for w in ["top", "upper", "first", "start"]):
            chosen_box = min(boxes, key=lambda b: b[1])  # Min y0 (topmost)
        elif any(w in q_lower for w in ["bottom", "lower", "last", "end"]):
            chosen_box = max(boxes, key=lambda b: b[3])  # Max y1 (bottommost)
        elif any(w in q_lower for w in ["left"]):
            chosen_box = min(boxes, key=lambda b: b[0])  # Min x0 (leftmost)
        elif any(w in q_lower for w in ["right"]):
            chosen_box = max(boxes, key=lambda b: b[2])  # Max x1 (rightmost)
        elif any(w in q_lower for w in ["middle", "center", "core"]):
            center_x, center_y = w / 2, h / 2
            chosen_box = min(boxes, key=lambda b: ((b[0]+b[2])/2 - center_x)**2 + ((b[1]+b[3])/2 - center_y)**2)
        else:
            # By default, if multiple discrete boxes exist and query targets a sub-part,
            # select the most prominent central sub-box
            if len(boxes) >= 2:
                # Rank by central proximity and reasonable size
                center_x, center_y = w / 2, h / 2
                chosen_box = min(
                    boxes,
                    key=lambda b: (((b[0]+b[2])/2 - center_x)**2 + ((b[1]+b[3])/2 - center_y)**2) / (b[2]-b[0] + 1)
                )

        if chosen_box is not None:
            bx0, by0, bx1, by1 = chosen_box
            crop_box = (
                max(0, bx0 - padding),
                max(0, by0 - padding),
                min(w, bx1 + padding),
                min(h, by1 + padding)
            )
            return crop_box, True

    except Exception as e:
        logger.debug(f"Image sub-region CV analysis error: {e}")

    return full_box, False
