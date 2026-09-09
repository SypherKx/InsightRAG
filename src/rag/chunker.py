"""
Text chunking module for RAG pipeline.

Splits documents into coherent chunks with overlap.
Uses token-based chunking for consistency with embedding models.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


def build_contextual_chunk(
    raw_text: str,
    title: Optional[str] = None,
    section: Optional[str] = None,
    page_number: Optional[int] = None,
) -> str:
    """
    Prepend each chunk with a lightweight, rule-based context header for vector embedding.
    
    Structure: [Document: <title> | Page: <page_number> | Section: <section>]
    
    Args:
        raw_text: Raw chunk text (used for display and citation)
        title: Document title or filename
        section: Section header or heading name (if available)
        page_number: Page number in document
        
    Returns:
        Contextualized text formatted for dense embedding
    """
    clean_text = raw_text.strip()
    if not clean_text:
        return ""

    header_parts = []
    if title and str(title).strip():
        header_parts.append(f"Document: {str(title).strip()}")
    if page_number is not None and int(page_number) > 0:
        header_parts.append(f"Page: {int(page_number)}")
    if section and str(section).strip():
        header_parts.append(f"Section: {str(section).strip()}")

    if not header_parts:
        return clean_text

    header = " | ".join(header_parts)
    return f"[{header}]\n{clean_text}"


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    chunk_size: int = 500  # Target tokens per chunk
    overlap: int = 50  # Token overlap between chunks
    min_chunk_size: int = 1  # Minimum chunk size
    max_chunk_size: int = 1000  # Maximum chunk size
    separator: str = "\n"  # Preferred separator for splitting
    keep_separator: bool = False


class TextChunker:
    """
    Splits text into overlapping chunks for embedding.

    Uses a token-aware approach (approximates tokens as words/punctuation).
    Preserves sentence boundaries when possible to maintain coherence.
    """

    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize chunker.

        Args:
            config: Chunking configuration (uses defaults if None)
        """
        self.config = config or ChunkConfig()
        self._separator_pattern = self._compile_separator_pattern()

    def _compile_separator_pattern(self) -> re.Pattern:
        """Compile regex for splitting on separators."""
        # Split on double newlines, then single newlines, then sentences
        separators = [
            r"\n\s*\n",  # Double newline
            r"\n",  # Single newline
            r"(?<=[.!?])\s+",  # Sentence boundary
            r"(?<=;)\s+",  # Semicolon boundary
            r"\s+",  # Word boundary (fallback)
        ]
        return re.compile("|".join(separators))

    def _count_tokens(self, text: str) -> int:
        """
        Approximate token count.

        Uses a simple heuristic: tokens ≈ words + punctuation.
        For more accuracy, could use tiktoken or transformers tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b|[^\w\s]', text)
        return len(tokens)

    def _split_by_separators(self, text: str) -> List[Tuple[str, str]]:
        """
        Split text into logical sections and structural segments.
        Preserves active section headers.

        Returns:
            List of (section_title, segment_text)
        """
        # Detect headers: '# Header', '## Subheader', 'Chapter X', 'Section Y'
        header_pattern = re.compile(r'^(#{1,6}\s+.*|[A-Z0-9\.\s]{3,40}:|Chapter\s+\d+.*|Section\s+\d+.*)$', re.MULTILINE | re.IGNORECASE)
        
        lines = text.split('\n')
        sections: List[Tuple[str, str]] = []
        current_section_title = ""
        current_section_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if header_pattern.match(stripped) and len(stripped) < 80:
                if current_section_lines:
                    sec_text = "\n".join(current_section_lines).strip()
                    if sec_text:
                        sections.append((current_section_title, sec_text))
                    current_section_lines = []
                current_section_title = stripped.lstrip('#').strip()
                current_section_lines.append(line)
            else:
                current_section_lines.append(line)

        if current_section_lines:
            sec_text = "\n".join(current_section_lines).strip()
            if sec_text:
                sections.append((current_section_title, sec_text))

        # If no explicit headers were detected, treat the entire document as standard paragraphs
        if not sections:
            sections = [("", text)]

        # Now subdivide each section into coherent paragraph segments
        result: List[Tuple[str, str]] = []
        for sec_title, sec_text in sections:
            paragraphs = re.split(r'\n\s*\n', sec_text)
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean:
                    continue
                token_count = self._count_tokens(p_clean)
                if token_count <= self.config.chunk_size * 1.5:
                    result.append((sec_title, p_clean))
                else:
                    # Break large paragraphs along sentence boundaries
                    sentences = re.split(r'(?<=[.!?])\s+', p_clean)
                    cur_group = []
                    cur_tokens = 0
                    for s in sentences:
                        stoks = self._count_tokens(s)
                        if cur_tokens + stoks > self.config.chunk_size and cur_group:
                            result.append((sec_title, " ".join(cur_group)))
                            cur_group = [s]
                            cur_tokens = stoks
                        else:
                            cur_group.append(s)
                            cur_tokens += stoks
                    if cur_group:
                        result.append((sec_title, " ".join(cur_group)))

        return result

    def chunk_text(self, text: str, document_id: str, chunk_prefix: str = "") -> List[dict]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            document_id: Source document ID
            chunk_prefix: Prefix to add to each chunk (e.g., document title)

        Returns:
            List of chunk dictionaries with metadata
        """
        if not text or not text.strip():
            logger.warning(f"Empty text provided for document {document_id}")
            return []

        # Clean text
        text = self._clean_text(text)

        # Split into base segments
        segments = self._split_by_separators(text)

        chunks = []
        current_chunk = []
        current_section = ""
        current_token_count = 0
        chunk_index = 0

        for sec_title, segment in segments:
            segment_tokens = self._count_tokens(segment)
            if not current_section and sec_title:
                current_section = sec_title

            # If segment itself is larger than max chunk size, force split
            if segment_tokens > self.config.max_chunk_size:
                logger.warning(f"Segment too large ({segment_tokens} tokens), force splitting")
                char_limit = self.config.chunk_size * 4
                for i in range(0, len(segment), char_limit):
                    forced_segment = segment[i:i + char_limit]
                    if forced_segment.strip():
                        segments.append((sec_title, forced_segment))
                continue

            # Would adding this segment exceed the chunk size?
            if current_token_count + segment_tokens > self.config.chunk_size and current_chunk:
                # Save current chunk (raw clean text for display/citations)
                raw_chunk_text = self.config.separator.join(current_chunk).strip()
                embedded_chunk_text = (
                    f"{chunk_prefix}\n\n{raw_chunk_text}"
                    if chunk_prefix
                    else build_contextual_chunk(raw_chunk_text, section=current_section)
                )

                chunks.append({
                    "chunk_index": chunk_index,
                    "text": raw_chunk_text,
                    "display_text": raw_chunk_text,
                    "embedded_text": embedded_chunk_text,
                    "section": current_section,
                    "token_count": current_token_count,
                    "segment_count": len(current_chunk)
                })
                chunk_index += 1

                # Start new chunk with overlap: keep some segments
                overlap_tokens = 0
                overlap_segments = []
                for seg in reversed(current_chunk):
                    seg_tokens = self._count_tokens(seg)
                    if overlap_tokens + seg_tokens <= self.config.overlap:
                        overlap_segments.insert(0, seg)
                        overlap_tokens += seg_tokens
                    else:
                        break

                current_chunk = overlap_segments
                current_token_count = overlap_tokens
                current_section = sec_title

            # Add current segment
            current_chunk.append(segment)
            current_token_count += segment_tokens
            if sec_title:
                current_section = sec_title

        # Don't forget the last chunk
        if current_chunk:
            raw_chunk_text = self.config.separator.join(current_chunk).strip()
            embedded_chunk_text = (
                f"{chunk_prefix}\n\n{raw_chunk_text}"
                if chunk_prefix
                else build_contextual_chunk(raw_chunk_text, section=current_section)
            )

            chunks.append({
                "chunk_index": chunk_index,
                "text": raw_chunk_text,
                "display_text": raw_chunk_text,
                "embedded_text": embedded_chunk_text,
                "section": current_section,
                "token_count": current_token_count,
                "segment_count": len(current_chunk)
            })

        # Filter out chunks that are too small
        chunks = [
            c for c in chunks
            if self.config.min_chunk_size <= c["token_count"] <= self.config.max_chunk_size
        ]

        # Add document_id and final IDs
        for i, chunk in enumerate(chunks):
            chunk["document_id"] = document_id
            chunk["chunk_id"] = f"{document_id}_chunk_{i}"

        logger.info(f"Chunked document {document_id}: {len(chunks)} chunks from {len(text)} chars")
        return chunks

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Normalize whitespace
        text = re.sub(r'\r\n', '\n', text)  # Windows line endings
        text = re.sub(r'\r', '\n', text)  # Old Mac line endings
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple blank lines
        text = re.sub(r' {2,}', ' ', text)  # Multiple spaces

        # Remove zero-width characters
        text = re.sub(r'\u200b|\u200c|\u200d|\ufe0f', '', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def chunk_documents(self, documents: List[dict], text_key: str = "content") -> List[dict]:
        """
        Chunk multiple documents with full page-awareness and contextual prefixing.
        Preserves exact page_number, display_text, and embedded_text in each chunk.

        Args:
            documents: List of document dicts with at least 'id' and text content
            text_key: Key containing text content in each document

        Returns:
            Flat list of all page-indexed chunks from all documents
        """
        all_chunks = []

        for doc in documents:
            doc_id = doc.get("id", "unknown")
            title = doc.get("title", "")
            source_path = doc.get("source_path", "")
            doc_meta = doc.get("metadata", {})
            file_name = doc_meta.get("file_name", title or "Document")

            # Check if structured pages_data is available (from PDF / paginated extractors)
            pages_data = doc_meta.get("pages_data", [])

            if pages_data and isinstance(pages_data, list):
                # Chunk page-by-page to guarantee zero cross-page leakage and 100% accurate page attribution
                doc_chunks = []
                for p_idx, page_info in enumerate(pages_data):
                    page_num = page_info.get("page_number", p_idx + 1)
                    page_text = page_info.get("text", "").strip()
                    if not page_text:
                        continue
                    
                    p_chunks = self.chunk_text(page_text, f"{doc_id}_p{page_num}")
                    
                    for c in p_chunks:
                        c["page_number"] = page_num
                        c["page"] = page_num
                        c["has_images"] = page_info.get("has_images", False)
                        c["has_drawings"] = page_info.get("has_drawings", False)
                        c["has_tables"] = page_info.get("has_tables", False)
                        c["tables_count"] = page_info.get("tables_count", 0)
                        c["visual_elements"] = page_info.get("visual_elements", [])
                        c["title"] = title
                        c["source_path"] = source_path
                        
                        # Build contextually prefixed embedded_text for vector embedding
                        c["display_text"] = c["text"]
                        c["embedded_text"] = build_contextual_chunk(
                            raw_text=c["text"],
                            title=file_name or title,
                            section=c.get("section", ""),
                            page_number=page_num
                        )
                        
                        chunk_meta = dict(doc_meta)
                        chunk_meta["page_number"] = page_num
                        chunk_meta["page"] = page_num
                        chunk_meta["section"] = c.get("section", "")
                        chunk_meta["has_images"] = page_info.get("has_images", False)
                        chunk_meta["has_drawings"] = page_info.get("has_drawings", False)
                        chunk_meta["has_tables"] = page_info.get("has_tables", False)
                        chunk_meta["tables_count"] = page_info.get("tables_count", 0)
                        chunk_meta["visual_elements"] = page_info.get("visual_elements", [])
                        chunk_meta["file_name"] = file_name
                        c["doc_metadata"] = chunk_meta
                        doc_chunks.append(c)
                        
                # Re-index chunks sequentially for this document
                for i, c in enumerate(doc_chunks):
                    c["chunk_index"] = i
                    c["chunk_id"] = f"{doc_id}_chunk_{i}"
                    c["document_id"] = doc_id
                all_chunks.extend(doc_chunks)
                logger.info(f"Page-aware chunking for {file_name}: {len(doc_chunks)} chunks across {len(pages_data)} pages")
                continue

            # Fallback for plain text, markdown, or documents without explicit pages_data
            text = doc.get(text_key, "")
            if not text:
                logger.warning(f"Document {doc_id} has no text content")
                continue

            # Check if text has [Page X] tags
            page_sections = re.split(r'\[Page\s+(\d+)\]\s*\n', text)
            if len(page_sections) > 1:
                # Format: [preamble, page_1_num, page_1_text, page_2_num, page_2_text, ...]
                doc_chunks = []
                idx = 1
                while idx < len(page_sections):
                    try:
                        p_num = int(page_sections[idx])
                        p_text = page_sections[idx + 1].strip()
                    except (ValueError, IndexError):
                        idx += 2
                        continue
                    
                    if p_text:
                        p_chunks = self.chunk_text(p_text, f"{doc_id}_p{p_num}")
                        for c in p_chunks:
                            c["page_number"] = p_num
                            c["page"] = p_num
                            c["title"] = title
                            c["source_path"] = source_path
                            c["display_text"] = c["text"]
                            c["embedded_text"] = build_contextual_chunk(
                                raw_text=c["text"],
                                title=file_name or title,
                                section=c.get("section", ""),
                                page_number=p_num
                            )
                            chunk_meta = dict(doc_meta)
                            chunk_meta["page_number"] = p_num
                            chunk_meta["page"] = p_num
                            chunk_meta["section"] = c.get("section", "")
                            chunk_meta["file_name"] = file_name
                            c["doc_metadata"] = chunk_meta
                            doc_chunks.append(c)
                    idx += 2

                for i, c in enumerate(doc_chunks):
                    c["chunk_index"] = i
                    c["chunk_id"] = f"{doc_id}_chunk_{i}"
                    c["document_id"] = doc_id
                all_chunks.extend(doc_chunks)
                logger.info(f"Tag-aware chunking for {file_name}: {len(doc_chunks)} chunks")
                continue

            # Default single-page document chunking
            chunks = self.chunk_text(text, doc_id)
            for c in chunks:
                c["title"] = title
                c["source_path"] = source_path
                c["page_number"] = 1
                c["page"] = 1
                c["display_text"] = c["text"]
                c["embedded_text"] = build_contextual_chunk(
                    raw_text=c["text"],
                    title=file_name or title,
                    section=c.get("section", ""),
                    page_number=1
                )
                chunk_meta = dict(doc_meta)
                chunk_meta["page_number"] = 1
                chunk_meta["page"] = 1
                chunk_meta["section"] = c.get("section", "")
                chunk_meta["file_name"] = file_name
                c["doc_metadata"] = chunk_meta
            all_chunks.extend(chunks)

        logger.info(f"Total: {len(all_chunks)} page-aware chunks from {len(documents)} documents")
        return all_chunks


def create_default_chunker() -> TextChunker:
    """Create a chunker with default configuration."""
    config = ChunkConfig(
        chunk_size=500,
        overlap=50,
        min_chunk_size=1,
        max_chunk_size=1000
    )
    return TextChunker(config)
