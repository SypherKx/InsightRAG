"""
Security utility functions for InsightRAG AI.

Provides defense against:
- Path Traversal / Arbitrary File Overwrite / LFI
- Malicious Filename Injection
- Unsafe extensions & MIME mismatches
"""

import re
import os
from pathlib import Path
from typing import List, Optional, Set
from fastapi import HTTPException

# Allowed extensions across the platform
ALLOWED_EXTENSIONS: Set[str] = {
    ".pdf", ".txt", ".md", ".csv", ".tsv", ".json", ".log",
    ".rst", ".html", ".xml", ".docx",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp"
}

ALLOWED_VISUAL_EXTENSIONS: Set[str] = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp"
}


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitizes a filename to protect against path traversal and special character injection.
    
    1. Extracts basename (strips any leading directory separators or ../ paths).
    2. Replaces any non-whitelisted characters with an underscore.
    3. Strips null bytes (%00 / \\x00) and control characters.
    4. Enforces max length while preserving extension.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename: filename cannot be empty.")

    # Extract base name using Path and standard basename to avoid path traversal
    clean_name = Path(filename).name.strip()
    
    # Strip null bytes and control chars
    clean_name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_name)
    
    # Remove directory traversal patterns
    clean_name = clean_name.replace("..", "").replace("/", "").replace("\\", "")

    # Retain only safe alphanumeric characters, dashes, underscores, and dots
    stem = Path(clean_name).stem
    suffix = Path(clean_name).suffix.lower()

    # Sanitize stem
    safe_stem = re.sub(r'[^a-zA-Z0-9_\- ]', '_', stem).strip()
    if not safe_stem:
        safe_stem = "document"

    # Truncate if too long (reserving space for extension)
    allowed_stem_len = max(10, max_length - len(suffix))
    safe_stem = safe_stem[:allowed_stem_len]

    sanitized = f"{safe_stem}{suffix}"
    return sanitized


def validate_safe_path(base_dir: Path, target_path: Path) -> Path:
    """
    Validates that target_path is strictly located within base_dir.
    Prevents directory traversal (e.g. symlink or ../ escape).
    
    Raises HTTPException 403/400 if unsafe.
    """
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()

    try:
        # Python 3.9+ is_relative_to
        if not resolved_target.is_relative_to(resolved_base):
            raise HTTPException(status_code=403, detail="Access denied: Path traversal detected.")
    except AttributeError:
        # Fallback for older python
        try:
            resolved_target.relative_to(resolved_base)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied: Path traversal detected.")

    return resolved_target


def validate_file_extension(filename: str, allowed_set: Optional[Set[str]] = None) -> str:
    """
    Validates that a file's extension is in the allowed whitelist.
    """
    allowed = allowed_set or ALLOWED_EXTENSIONS
    suffix = Path(filename).suffix.lower()
    
    if suffix not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed formats: {', '.join(sorted(allowed))}"
        )
    return suffix
