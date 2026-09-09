"""
Main CSV Ingestion Pipeline.

Orchestrates the complete data ingestion workflow:
1. File upload and validation
2. Schema inference
3. Data quality validation
4. Data cleaning and preprocessing
5. Storage to S3/local filesystem
6. Metadata persistence to PostgreSQL
7. Event publishing (for async processing)

Designed for production use with comprehensive error handling,
logging, and recovery mechanisms.
"""

import logging
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import pandas as pd

from .models import (
    DatasetMetadata,
    DatasetStatus,
    ColumnSchema,
    ColumnType,
    IngestionRequest,
    IngestionResponse,
    ValidationReport,
    PreprocessingConfig
)
from .parser import CSVParser
from .validator import DataValidator
from .storage import StorageEngine
from .cleaner import DataCleaner

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    dataset_id: str
    metadata: Optional[DatasetMetadata]
    validation_report: Optional[ValidationReport]
    cleaning_report: Optional[Dict[str, Any]]
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        """Initialize warnings list if None."""
        if self.warnings is None:
            self.warnings = []


class IngestionPipeline:
    """
    Main ingestion pipeline for CSV data.

    Coordinates parsing, validation, cleaning, and storage operations.
    Supports both synchronous and asynchronous processing modes.
    """

    def __init__(
        self,
        storage_engine: StorageEngine,
        preprocessing_config: PreprocessingConfig = None,
        max_file_size_mb: int = 500,
        enable_async: bool = False,
        event_publisher=None  # Will be implemented for async
    ):
        """
        Initialize ingestion pipeline.

        Args:
            storage_engine: Configured storage engine
            preprocessing_config: Data preprocessing configuration
            max_file_size_mb: Maximum allowed file size in MB
            enable_async: Enable async event publishing
            event_publisher: Event publisher for async notifications
        """
        self.storage = storage_engine
        self.preprocessing_config = preprocessing_config or PreprocessingConfig()
        self.max_file_size_mb = max_file_size_mb
        self.enable_async = enable_async
        self.event_publisher = event_publisher

        # Initialize parser
        self.parser = CSVParser(
            delimiter=self.preprocessing_config.delimiter,
            quotechar=self.preprocessing_config.quotechar,
            escapechar=self.preprocessing_config.escapechar,
            encoding=self.preprocessing_config.encoding
        )

        # Statistics
        self.pipeline_stats = {
            "datasets_processed": 0,
            "total_rows_ingested": 0,
            "total_errors": 0,
            "avg_processing_time_sec": 0
        }

        logger.info("Ingestion Pipeline initialized")

    def _validate_file(
        self,
        file_path: Path,
        expected_size_mb: float
    ) -> Tuple[bool, List[str]]:
        """
        Perform pre-upload file validation.

        Args:
            file_path: Path to uploaded file
            expected_size_mb: File size in MB

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check file size
        if expected_size_mb > self.max_file_size_mb:
            errors.append(
                f"File size ({expected_size_mb:.1f} MB) exceeds limit "
                f"({self.max_file_size_mb} MB)"
            )

        # Check if file exists
        if not file_path.exists():
            errors.append("File does not exist")

        # Check extension
        if file_path.suffix.lower() not in ['.csv', '.tsv']:
            errors.append(f"Unsupported file type: {file_path.suffix}")

        return len(errors) == 0, errors

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _publish_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Publish event to message queue (if async enabled).

        Args:
            event_type: Event type identifier
            payload: Event payload
        """
        if not self.enable_async or not self.event_publisher:
            return

        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0",
                "payload": payload
            }
            self.event_publisher.publish(event)
            logger.info(f"Published event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    def _infer_time_column(
        self,
        column_schemas: List[ColumnSchema],
        user_provided: Optional[str] = None
    ) -> Optional[str]:
        """
        Determine time column from schema or inference.

        Args:
            column_schemas: Column schema list
            user_provided: User-specified time column

        Returns:
            Time column name or None
        """
        if user_provided:
            # Validate user-provided column exists
            for col in column_schemas:
                if col.name == user_provided:
                    logger.info(f"Using user-provided time column: {user_provided}")
                    return user_provided
            logger.warning(f"User-provided time column '{user_provided}' not found")

        # Use auto-detected from schema inference
        for col in column_schemas:
            if col.is_time_column:
                logger.info(f"Auto-detected time column: {col.name}")
                return col.name

        # Fallback: infer from type
        for col in column_schemas:
            if col.effective_type == ColumnType.DATETIME:
                logger.info(f"Inferred time column from type: {col.name}")
                return col.name

        return None

    def _identify_dimensions(
        self,
        column_schemas: List[ColumnSchema],
        user_provided: List[str]
    ) -> List[str]:
        """
        Identify dimension (categorical) columns.

        Args:
            column_schemas: Column schema list
            user_provided: User-provided dimension columns

        Returns:
            List of dimension column names
        """
        dimensions = []

        # Add user-provided dimensions
        for col_name in user_provided:
            for col in column_schemas:
                if col.name == col_name:
                    if col.effective_type in (ColumnType.CATEGORICAL, ColumnType.TEXT):
                        dimensions.append(col_name)
                        col.is_dimension = True
                    else:
                        logger.warning(
                            f"Dimension column '{col_name}' is not categorical "
                            f"(type: {col.effective_type})"
                        )
                    break

        # Auto-detect low-cardinality columns as potential dimensions
        for col in column_schemas:
            if (col.effective_type in (ColumnType.CATEGORICAL, ColumnType.TEXT) and
                col.name not in dimensions and
                col.unique_count < 50):  # Reasonable cardinality
                dimensions.append(col.name)
                col.is_dimension = True

        logger.info(f"Identified {len(dimensions)} dimension columns: {dimensions}")
        return dimensions

    def process_upload(
        self,
        file_path: Path,
        request: IngestionRequest,
        org_id: str,
        user_id: str
    ) -> PipelineResult:
        """
        Process uploaded CSV file through complete ingestion pipeline.

        Args:
            file_path: Path to uploaded CSV file
            request: Ingestion request parameters
            org_id: Organization ID
            user_id: User ID performing upload

        Returns:
            PipelineResult with status and metadata
        """
        import time
        start_time = time.time()
        dataset_id = str(uuid.uuid4())

        logger.info(
            f"Starting ingestion for dataset {dataset_id}: {file_path.name} "
            f"(org={org_id}, user={user_id})"
        )

        # Initialize dataset metadata
        dataset_name = request.name or file_path.name
        metadata = DatasetMetadata(
            id=dataset_id,
            name=dataset_name,
            org_id=org_id,
            file_path="",  # Will be set after upload
            file_hash="",  # Will be computed
            row_count=0,
            column_count=0,
            column_schema=[],
            status=DatasetStatus.PARSING,
            error_message=None,
            quality_score=None,
            uploaded_by=user_id,
            uploaded_at=datetime.utcnow()
        )

        try:
            # ========================================
            # STEP 1: File Validation
            # ========================================
            logger.info("Step 1: Validating file")
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            is_valid, validation_errors = self._validate_file(file_path, file_size_mb)

            if not is_valid:
                error_msg = f"File validation failed: {'; '.join(validation_errors)}"
                logger.error(error_msg)
                metadata.status = DatasetStatus.FAILED
                metadata.error_message = error_msg
                self.storage.create_dataset_record(metadata)
                return PipelineResult(
                    success=False,
                    dataset_id=dataset_id,
                    metadata=metadata,
                    validation_report=None,
                    cleaning_report=None,
                    error=error_msg
                )

            # Compute file hash for deduplication
            file_hash = self._compute_file_hash(file_path)
            metadata.file_hash = file_hash

            # ========================================
            # STEP 2: Schema Inference
            # ========================================
            logger.info("Step 2: Inferring schema")
            metadata.status = DatasetStatus.PARSING

            user_types = {}
            if request.name:  # Could extend to include user type definitions
                pass

            column_schemas = self.parser.infer_schema(
                file_path,
                time_column_candidates=[request.time_column] if request.time_column else None,
                user_provided_types=user_types
            )

            metadata.column_schema = column_schemas
            metadata.column_count = len(column_schemas)

            # ========================================
            # STEP 3: Identify Time Column and Dimensions
            # ========================================
            logger.info("Step 3: Identifying time column and dimensions")
            time_column = self._infer_time_column(column_schemas, request.time_column)
            metadata.time_column = time_column

            dimensions = self._identify_dimensions(column_schemas, request.dimensions)
            metadata.dimensions = dimensions

            # ========================================
            # STEP 4: Load Full Data
            # ========================================
            logger.info("Step 4: Loading full dataset")
            metadata.status = DatasetStatus.LOADING

            df = self.parser.read_csv(
                file_path,
                column_schema=column_schemas,
                time_column=time_column,
                chunks=False
            )

            metadata.row_count = len(df)
            logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")

            # ========================================
            # STEP 5: Data Quality Validation
            # ========================================
            logger.info("Step 5: Validating data quality")
            metadata.status = DatasetStatus.VALIDATING

            validation_report = DataValidator().validate_dataset(df, column_schemas)

            # Log validation results
            logger.info(
                f"Validation: {validation_report.overall_status}, "
                f"score={validation_report.quality_metrics.total_rows} rows"
            )

            if validation_report.warnings:
                for warning in validation_report.warnings[:5]:  # Log first 5
                    logger.warning(f"Validation warning: {warning}")

            if validation_report.errors:
                for error in validation_report.errors[:5]:
                    logger.error(f"Validation error: {error}")

            # Store quality score
            metadata.quality_score = validation_report.quality_metrics.missing_values_percentage / 100.0

            # ========================================
            # STEP 6: Data Cleaning (Optional)
            # ========================================
            logger.info("Step 6: Cleaning data")
            metadata.status = DatasetStatus.CLEANING

            cleaner = DataCleaner(self.preprocessing_config)
            df_clean, cleaning_report = cleaner.clean_dataset(
                df,
                column_schemas,
                time_column=time_column,
                config=self.preprocessing_config
            )

            logger.info(f"Cleaning complete: {len(df)} -> {len(df_clean)} rows")

            # ========================================
            # STEP 7: Store to Object Storage
            # ========================================
            logger.info("Step 7: Storing to object storage")
            metadata.status = DatasetStatus.STORING

            # Upload original file first
            storage_path = self.storage.upload_file(
                file_path,
                org_id,
                dataset_id,
                file_path.name
            )
            metadata.file_path = storage_path

            # Optionally upload cleaned file
            if self.preprocessing_config and len(df_clean) > 0:
                cleaned_path = file_path.parent / f"{dataset_id}_cleaned.csv"
                df_clean.to_csv(cleaned_path, index=False)
                self.storage.upload_file(
                    cleaned_path,
                    org_id,
                    dataset_id,
                    f"cleaned_{file_path.name}"
                )
                cleaned_path.unlink(missing_ok=True)  # Clean up local temp file

            # ========================================
            # STEP 8: Save Metadata
            # ========================================
            logger.info("Step 8: Saving metadata")
            metadata.status = DatasetStatus.COMPLETED
            metadata.processing_completed_at = datetime.utcnow()

            self.storage.create_dataset_record(metadata)

            # ========================================
            # STEP 9: Publish Event (Async)
            # ========================================
            if self.enable_async:
                logger.info("Step 9: Publishing event")
                self._publish_event("dataset_uploaded", {
                    "dataset_id": dataset_id,
                    "org_id": org_id,
                    "storage_path": storage_path,
                    "schema": [col.model_dump() if hasattr(col, "model_dump") else col.dict() for col in column_schemas],
                    "time_column": time_column,
                    "dimensions": dimensions,
                    "row_count": len(df),
                    "quality_score": metadata.quality_score
                })

            # ========================================
            # COMPLETE
            # ========================================
            elapsed_time = time.time() - start_time
            self.pipeline_stats["datasets_processed"] += 1
            self.pipeline_stats["total_rows_ingested"] += len(df)
            self.pipeline_stats["avg_processing_time_sec"] = (
                (self.pipeline_stats["avg_processing_time_sec"] *
                 (self.pipeline_stats["datasets_processed"] - 1) + elapsed_time) /
                self.pipeline_stats["datasets_processed"]
            )

            logger.info(
                f"Ingestion complete for {dataset_id} in {elapsed_time:.2f}s "
                f"({len(df)} rows, {len(column_schemas)} columns)"
            )

            response = IngestionResponse(
                dataset_id=dataset_id,
                name=dataset_name,
                status="completed",
                row_count=len(df),
                column_count=len(column_schemas),
                message="Dataset ingested successfully",
                estimated_completion=None  # Could estimate based on avg time
            )

            return PipelineResult(
                success=True,
                dataset_id=dataset_id,
                metadata=metadata,
                validation_report=validation_report,
                cleaning_report=cleaning_report,
                warnings=validation_report.warnings
            )

        except pd.errors.EmptyDataError:
            error_msg = "CSV file is empty or contains no data"
            logger.error(f"Pipeline failed for {dataset_id}: {error_msg}")
            return self._handle_failure(dataset_id, metadata, error_msg)

        except pd.errors.ParserError as e:
            error_msg = f"CSV parsing error: {str(e)}"
            logger.error(f"Pipeline failed for {dataset_id}: {error_msg}", exc_info=True)
            return self._handle_failure(dataset_id, metadata, error_msg)

        except UnicodeDecodeError as e:
            error_msg = f"Encoding error: {str(e)}. Try specifying a different encoding."
            logger.error(f"Pipeline failed for {dataset_id}: {error_msg}")
            return self._handle_failure(dataset_id, metadata, error_msg)

        except MemoryError:
            error_msg = "Insufficient memory to process dataset. Try using chunking or reduce file size."
            logger.error(f"Pipeline failed for {dataset_id}: {error_msg}")
            return self._handle_failure(dataset_id, metadata, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Pipeline failed for {dataset_id}", exc_info=True)
            return self._handle_failure(dataset_id, metadata, error_msg)

    def _handle_failure(
        self,
        dataset_id: str,
        metadata: DatasetMetadata,
        error_msg: str
    ) -> PipelineResult:
        """
        Handle pipeline failure with cleanup.

        Args:
            dataset_id: Dataset ID
            metadata: Dataset metadata
            error_msg: Error message

        Returns:
            PipelineResult with failure status
        """
        metadata.status = DatasetStatus.FAILED
        metadata.error_message = error_msg

        try:
            # Try to save failed record
            self.storage.update_dataset_record(
                dataset_id,
                {
                    "status": DatasetStatus.FAILED.value,
                    "error_message": error_msg,
                    "processing_completed_at": datetime.utcnow()
                }
            )
        except Exception as e:
            logger.error(f"Failed to save failure record: {e}")

        self.pipeline_stats["total_errors"] += 1

        return PipelineResult(
            success=False,
            dataset_id=dataset_id,
            metadata=metadata,
            validation_report=None,
            cleaning_report=None,
            error=error_msg
        )

    def get_dataset_status(self, dataset_id: str) -> Optional[DatasetMetadata]:
        """
        Get current status of a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            DatasetMetadata or None if not found
        """
        return self.storage.get_dataset_record(dataset_id)

    def list_datasets(
        self,
        org_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DatasetMetadata]:
        """
        List datasets for an organization.

        Args:
            org_id: Organization ID
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of DatasetMetadata objects
        """
        records = self.storage.list_datasets(org_id, status, limit, offset)
        return [
            DatasetMetadata(
                id=r.id,
                name=r.name,
                org_id=r.org_id,
                file_path=r.file_path,
                file_hash=r.file_hash,
                row_count=r.row_count,
                column_count=r.column_count,
                column_schema=[ColumnSchema(**col) for col in r.column_schema],
                time_column=r.time_column,
                dimensions=r.dimensions or [],
                status=DatasetStatus(r.status),
                error_message=r.error_message,
                quality_score=r.quality_score / 100.0 if r.quality_score else None,
                uploaded_by=r.uploaded_by,
                uploaded_at=r.uploaded_at,
                processing_completed_at=r.processing_completed_at
            )
            for r in records
        ]

    def delete_dataset(self, dataset_id: str, org_id: str) -> bool:
        """
        Delete dataset and associated files.

        Args:
            dataset_id: Dataset ID
            org_id: Organization ID (for authorization)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        record = self.storage.get_dataset_record(dataset_id)
        if not record or record.org_id != org_id:
            return False

        # Delete storage file
        try:
            self.storage.delete_file(record.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete storage file for {dataset_id}: {e}")

        # Delete metadata record
        self.storage.delete_dataset_record(dataset_id)

        logger.info(f"Deleted dataset {dataset_id} for org {org_id}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return self.pipeline_stats.copy()

