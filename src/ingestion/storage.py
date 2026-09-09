"""
Storage interface for dataset files and metadata.

Supports both local filesystem and S3-compatible object storage.
Manages metadata persistence to PostgreSQL.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatasetRecord(Base):
    """SQLAlchemy model for datasets table."""
    __tablename__ = "datasets"

    id = Column(String, primary_key=True)
    org_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    column_schema = Column(JSON, nullable=False)
    time_column = Column(String, nullable=True)
    dimensions = Column(JSON, nullable=True, default=list)
    status = Column(String, nullable=False, default="uploading", index=True)
    error_message = Column(Text, nullable=True)
    quality_score = Column(Integer, nullable=True)  # 0-100
    uploaded_by = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processing_completed_at = Column(DateTime, nullable=True)


class StorageEngine:
    """
    Unified storage engine supporting local filesystem and S3.

    Handles file uploads, downloads, and metadata management.
    """

    def __init__(
        self,
        storage_type: str = "local",
        base_path: str = "./data",
        s3_endpoint: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_region: str = "us-east-1",
        database_url: str = "sqlite:///./data/metadata.db"
    ):
        """
        Initialize storage engine.

        Args:
            storage_type: "local" or "s3"
            base_path: Base directory for local storage
            s3_endpoint: S3 endpoint URL (for MinIO or AWS)
            s3_access_key: S3 access key
            s3_secret_key: S3 secret key
            s3_bucket: S3 bucket name
            s3_region: S3 region
            database_url: PostgreSQL/SQLite connection URL
        """
        self.storage_type = storage_type
        self.base_path = Path(base_path)
        self.database_url = database_url

        # Initialize S3 client if needed
        self.s3_client = None
        self.s3_bucket = s3_bucket
        if storage_type == "s3":
            try:
                import boto3
                from botocore.config import Config

                # Configure for MinIO compatibility if endpoint provided
                config = Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'path'}  # Path-style addressing for MinIO
                ) if s3_endpoint else None

                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=s3_endpoint,
                    aws_access_key_id=s3_access_key,
                    aws_secret_access_key=s3_secret_key,
                    region_name=s3_region,
                    config=config
                )
                logger.info(f"Initialized S3 client with endpoint: {s3_end_url}")
            except ImportError:
                logger.error("boto3 not installed. Install with: pip install boto3")
                raise
        else:
            # Create local base directory
            self.base_path.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Storage engine initialized: {storage_type}")

    def dispose(self):
        """Dispose of database engine and close all connections to release file locks."""
        if hasattr(self, 'engine'):
            self.engine.dispose()

    def __del__(self):
        """Dispose of database engine on cleanup to release file locks."""
        if hasattr(self, 'engine'):
            self.engine.dispose()

    def compute_file_hash(self, file_path: str | Path) -> str:
        """
        Compute SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA-256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def generate_dataset_path(self, org_id: str, dataset_id: str, filename: str) -> str:
        """
        Generate storage path for a dataset.

        Args:
            org_id: Organization ID
            dataset_id: Dataset UUID
            filename: Original filename

        Returns:
            Storage path (S3 key or relative local path)
        """
        import uuid
        safe_filename = Path(filename).name
        return f"{org_id}/{dataset_id}/{safe_filename}"

    def upload_file(
        self,
        source_path: str | Path,
        org_id: str,
        dataset_id: str,
        filename: str
    ) -> str:
        """
        Upload a file to storage.

        Args:
            source_path: Local source file path
            org_id: Organization ID
            dataset_id: Dataset UUID
            filename: Target filename

        Returns:
            Storage path where file was stored
        """
        storage_path = self.generate_dataset_path(org_id, dataset_id, filename)

        if self.storage_type == "s3":
            if not self.s3_client:
                raise RuntimeError("S3 client not initialized")

            self.s3_client.upload_file(
                str(source_path),
                self.s3_bucket,
                storage_path
            )
            logger.info(f"Uploaded to S3: s3://{self.s3_bucket}/{storage_path}")
        else:
            # Local filesystem
            target_path = self.base_path / storage_path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copy2(source_path, target_path)
            logger.info(f"Uploaded to local: {target_path}")

        return storage_path

    def download_file(self, storage_path: str, target_path: str | Path) -> None:
        """
        Download a file from storage.

        Args:
            storage_path: Storage path (S3 key or relative local path)
            target_path: Local destination path
        """
        if self.storage_type == "s3":
            if not self.s3_client:
                raise RuntimeError("S3 client not initialized")

            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            self.s3_client.download_file(
                self.s3_bucket,
                storage_path,
                str(target_path)
            )
        else:
            source_path = self.base_path / storage_path
            import shutil
            shutil.copy2(source_path, target_path)

        logger.info(f"Downloaded: {storage_path} -> {target_path}")

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in storage."""
        if self.storage_type == "s3":
            if not self.s3_client:
                return False

            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=storage_path)
                return True
            except Exception:
                return False
        else:
            return (self.base_path / storage_path).exists()

    def delete_file(self, storage_path: str) -> None:
        """Delete file from storage."""
        if self.storage_type == "s3":
            if not self.s3_client:
                raise RuntimeError("S3 client not initialized")

            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=storage_path)
            logger.info(f"Deleted from S3: {storage_path}")
        else:
            file_path = self.base_path / storage_path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted local: {file_path}")

    # Database operations

    def create_dataset_record(self, metadata: 'DatasetMetadata') -> None:
        """
        Create dataset metadata record in database.

        Args:
            metadata: Dataset metadata
        """
        with self.SessionLocal() as db:
            record = DatasetRecord(
                id=metadata.id,
                org_id=metadata.org_id,
                name=metadata.name,
                file_path=metadata.file_path,
                file_hash=metadata.file_hash,
                row_count=metadata.row_count,
                column_count=metadata.column_count,
                column_schema=[col.model_dump() if hasattr(col, "model_dump") else col.dict() for col in metadata.column_schema],
                time_column=metadata.time_column,
                dimensions=metadata.dimensions,
                status=metadata.status.value,
                error_message=metadata.error_message,
                quality_score=int(metadata.quality_score * 100) if metadata.quality_score else None,
                uploaded_by=metadata.uploaded_by,
                uploaded_at=metadata.uploaded_at,
                processing_completed_at=metadata.processing_completed_at
            )
            db.add(record)
            db.commit()
            logger.info(f"Created dataset record: {metadata.id}")

    def update_dataset_record(
        self,
        dataset_id: str,
        updates: dict,
        commit: bool = True
    ) -> None:
        """
        Update dataset metadata record.

        Args:
            dataset_id: Dataset ID
            updates: Dictionary of fields to update
            commit: Whether to commit transaction
        """
        with self.SessionLocal() as db:
            record = db.query(DatasetRecord).filter_by(id=dataset_id).first()
            if not record:
                raise ValueError(f"Dataset {dataset_id} not found")

            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)

            if commit:
                db.commit()
                logger.info(f"Updated dataset record: {dataset_id}")

    def get_dataset_record(self, dataset_id: str) -> Optional[DatasetRecord]:
        """
        Get dataset metadata record.

        Args:
            dataset_id: Dataset ID

        Returns:
            DatasetRecord or None if not found
        """
        with self.SessionLocal() as db:
            return db.query(DatasetRecord).filter_by(id=dataset_id).first()

    def delete_dataset_record(self, dataset_id: str) -> None:
        """Delete dataset metadata record."""
        with self.SessionLocal() as db:
            record = db.query(DatasetRecord).filter_by(id=dataset_id).first()
            if record:
                db.delete(record)
                db.commit()
                logger.info(f"Deleted dataset record: {dataset_id}")

    def list_datasets(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[DatasetRecord]:
        """
        List datasets with optional filters.

        Args:
            org_id: Filter by organization ID
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of DatasetRecord objects
        """
        with self.SessionLocal() as db:
            query = db.query(DatasetRecord)

            if org_id:
                query = query.filter_by(org_id=org_id)
            if status:
                query = query.filter_by(status=status)

            query = query.order_by(DatasetRecord.uploaded_at.desc())
            return query.offset(offset).limit(limit).all()

    def get_file_path(self, dataset_id: str) -> Optional[str]:
        """
        Get storage file path for a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Storage path or None if dataset not found
        """
        record = self.get_dataset_record(dataset_id)
        return record.file_path if record else None

    def get_local_file_path(self, dataset_id: str, download_dir: str | Path) -> Path:
        """
        Get or download file to local path.

        Args:
            dataset_id: Dataset ID
            download_dir: Directory to download to

        Returns:
            Local file path
        """
        record = self.get_dataset_record(dataset_id)
        if not record:
            raise ValueError(f"Dataset {dataset_id} not found")

        storage_path = record.file_path
        download_dir = Path(download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)

        local_path = download_dir / f"{dataset_id}_{Path(storage_path).name}"

        if not local_path.exists():
            self.download_file(storage_path, local_path)

        return local_path
