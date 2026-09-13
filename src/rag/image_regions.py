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


class VisualFingerprintMatcher:
    """
    Perceptual Visual Fingerprinting for sub-5ms CPU reverse image and diagram matching.
    
    Combines:
    1. 64-bit dHash (Difference Gradient Hash - 9x8 grayscale)
    2. 64-bit aHash (Average Luminance Mean Hash - 8x8 grayscale)
    3. 32x32 NCC (Normalized Cross Correlation spatial vector)
    4. 16-bin Color Histogram (RGB color distribution)
    
    Composite Formula:
    Score = (0.40 * sim_d) + (0.25 * sim_a) + (0.20 * sim_ncc) + (0.15 * sim_col)
    """

    @staticmethod
    def _to_pil_image(image_input) -> Optional[Any]:
        """Convert bytes, base64 string, or filepath to PIL Image in RGB mode."""
        from PIL import Image
        import io
        import base64
        from pathlib import Path

        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")
        if isinstance(image_input, bytes):
            return Image.open(io.BytesIO(image_input)).convert("RGB")
        if isinstance(image_input, str):
            if image_input.startswith("data:image"):
                image_input = image_input.split(",", 1)[-1]
            if len(image_input) > 200 and not image_input.startswith("http"):
                try:
                    raw = base64.b64decode(image_input)
                    return Image.open(io.BytesIO(raw)).convert("RGB")
                except Exception:
                    pass
            p = Path(image_input)
            if p.exists() and p.is_file():
                return Image.open(p).convert("RGB")
        return None

    @classmethod
    def compute_dhash(cls, img) -> int:
        """Compute 64-bit difference hash (9x8 grayscale gradient)."""
        gray = img.convert("L").resize((9, 8), cls._resample_filter())
        pixels = list(gray.getdata())
        diff = []
        for row in range(8):
            for col in range(8):
                idx = row * 9 + col
                diff.append(1 if pixels[idx] > pixels[idx + 1] else 0)
        
        val = 0
        for bit in diff:
            val = (val << 1) | bit
        return val

    @classmethod
    def compute_ahash(cls, img) -> int:
        """Compute 64-bit average hash (8x8 grayscale mean threshold)."""
        gray = img.convert("L").resize((8, 8), cls._resample_filter())
        pixels = list(gray.getdata())
        avg = sum(pixels) / 64.0
        val = 0
        for p in pixels:
            val = (val << 1) | (1 if p > avg else 0)
        return val

    @classmethod
    def compute_ncc_vector(cls, img) -> List[float]:
        """Compute 32x32 RGB normalized thumbnail vector."""
        thumb = img.resize((32, 32), cls._resample_filter())
        pixels = list(thumb.getdata())
        flat = [c for px in pixels for c in px[:3]]
        mean_val = sum(flat) / len(flat)
        centered = [x - mean_val for x in flat]
        norm = (sum(x * x for x in centered) ** 0.5) or 1.0
        return [round(x / norm, 5) for x in centered]

    @classmethod
    def compute_color_histogram(cls, img) -> List[float]:
        """Compute 16-bin per RGB channel normalized histogram (48 bins total)."""
        thumb = img.resize((64, 64), cls._resample_filter())
        pixels = list(thumb.getdata())
        r_hist = [0] * 16
        g_hist = [0] * 16
        b_hist = [0] * 16
        total = max(1, len(pixels))

        for r, g, b in (p[:3] for p in pixels):
            r_hist[min(15, r // 16)] += 1
            g_hist[min(15, g // 16)] += 1
            b_hist[min(15, b // 16)] += 1

        full = [round(c / total, 5) for c in (r_hist + g_hist + b_hist)]
        return full

    @classmethod
    def _resample_filter(cls):
        from PIL import Image
        return getattr(Image, "Resampling", Image).LANCZOS

    @classmethod
    def compute_fingerprint(cls, image_input) -> Optional[Dict[str, Any]]:
        """Compute all 4 perceptual fingerprint features for an image."""
        try:
            img = cls._to_pil_image(image_input)
            if img is None:
                return None
            return {
                "dhash": hex(cls.compute_dhash(img)),
                "ahash": hex(cls.compute_ahash(img)),
                "ncc": cls.compute_ncc_vector(img),
                "hist": cls.compute_color_histogram(img),
                "width": img.width,
                "height": img.height
            }
        except Exception as e:
            logger.debug(f"Fingerprint computation error: {e}")
            return None

    @classmethod
    def hamming_similarity(cls, hex1: str, hex2: str, bits: int = 64) -> float:
        """Compute normalized similarity from hamming distance between two hex integers."""
        try:
            v1 = int(hex1, 16)
            v2 = int(hex2, 16)
            xor_val = v1 ^ v2
            dist = bin(xor_val).count('1')
            return max(0.0, 1.0 - (dist / float(bits)))
        except Exception:
            return 0.0

    @classmethod
    def vector_cosine_similarity(cls, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        return min(max(dot, 0.0), 1.0)

    @classmethod
    def histogram_intersection(cls, h1: List[float], h2: List[float]) -> float:
        """Compute histogram intersection similarity normalized to [0.0, 1.0]."""
        if not h1 or not h2 or len(h1) != len(h2):
            return 0.0
        # Sum of intersection across 3 channels (each channel sums to 1.0, so total max is 3.0)
        total_inter = sum(min(a, b) for a, b in zip(h1, h2))
        return min(max(total_inter / 3.0, 0.0), 1.0)

    @classmethod
    def compute_similarity(cls, fp1: Dict[str, Any], fp2: Dict[str, Any]) -> float:
        """
        Compute composite visual similarity score:
        Score = (0.40 * sim_d) + (0.25 * sim_a) + (0.20 * sim_ncc) + (0.15 * sim_col)
        """
        if not fp1 or not fp2:
            return 0.0

        sim_d = cls.hamming_similarity(fp1.get("dhash", "0x0"), fp2.get("dhash", "0x0"), 64)
        sim_a = cls.hamming_similarity(fp1.get("ahash", "0x0"), fp2.get("ahash", "0x0"), 64)
        sim_ncc = cls.vector_cosine_similarity(fp1.get("ncc", []), fp2.get("ncc", []))
        sim_col = cls.histogram_intersection(fp1.get("hist", []), fp2.get("hist", []))

        composite = (0.40 * sim_d) + (0.25 * sim_a) + (0.20 * sim_ncc) + (0.15 * sim_col)
        return round(composite, 4)

    @classmethod
    def find_best_match(
        cls,
        query_image,
        stored_diagrams: List[Dict[str, Any]],
        threshold: float = 0.78
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Sub-5ms CPU reverse visual search across stored diagram fingerprints.
        Returns: (matching_diagram_dict, similarity_score) or None if no match meets threshold.
        """
        q_fp = cls.compute_fingerprint(query_image)
        if not q_fp or not stored_diagrams:
            return None

        best_diag = None
        best_score = 0.0

        for diag in stored_diagrams:
            target_fp = diag.get("fingerprint")
            if not target_fp and diag.get("file_path"):
                target_fp = cls.compute_fingerprint(diag["file_path"])
                diag["fingerprint"] = target_fp

            if target_fp:
                score = cls.compute_similarity(q_fp, target_fp)
                if score > best_score:
                    best_score = score
                    best_diag = diag

        if best_diag and best_score >= threshold:
            return best_diag, best_score
        return None
