"""
Local file storage for uploaded CSV files.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileStore:
    """Manages uploaded file storage on local filesystem."""

    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = Path(upload_dir)
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create upload directory {self.upload_dir}: {e}")

    def save_upload(self, file_content: bytes, dataset_id: str, filename: str) -> str:
        """
        Save uploaded file to storage with path traversal protection.

        Args:
            file_content: Raw file bytes
            dataset_id: Dataset ID for directory organization
            filename: Original filename

        Returns:
            Storage path
        """
        from ..utils.security import sanitize_filename, validate_safe_path

        safe_id = sanitize_filename(dataset_id)
        safe_name = sanitize_filename(filename)

        dataset_dir = self.upload_dir / safe_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        file_path = validate_safe_path(self.upload_dir, dataset_dir / safe_name)
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"Saved upload: {file_path} ({len(file_content)} bytes)")
        return str(file_path)

    def get_file_path(self, dataset_id: str, filename: str) -> Optional[Path]:
        """Get path to stored file with path traversal validation."""
        from ..utils.security import sanitize_filename, validate_safe_path
        try:
            safe_id = sanitize_filename(dataset_id)
            safe_name = sanitize_filename(filename)
            file_path = validate_safe_path(self.upload_dir, self.upload_dir / safe_id / safe_name)
            if file_path.exists():
                return file_path
        except Exception:
            return None
        return None

    def delete_dataset_files(self, dataset_id: str):
        """Delete all files for a dataset safely."""
        from ..utils.security import sanitize_filename, validate_safe_path
        try:
            safe_id = sanitize_filename(dataset_id)
            dataset_dir = validate_safe_path(self.upload_dir, self.upload_dir / safe_id)
            if dataset_dir.exists():
                shutil.rmtree(dataset_dir)
                logger.info(f"Deleted files for dataset {dataset_id}")
        except Exception as e:
            logger.warning(f"Could not safely delete files for dataset {dataset_id}: {e}")

