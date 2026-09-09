"""
Dataset Service — CRUD operations and file management.
"""

import logging
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

import pandas as pd

from ..storage.database import (
    DatasetRecord, AnomalyRecord, RootCauseRecord, ExplanationRecord,
    get_session
)
from ..storage.file_store import FileStore

logger = logging.getLogger(__name__)


class DatasetService:
    """Manages dataset lifecycle: upload, storage, metadata, deletion."""

    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    def create_dataset(
        self,
        file_content: bytes,
        filename: str,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new dataset from uploaded file.

        Returns:
            Dataset metadata dict
        """
        dataset_id = str(uuid.uuid4())
        dataset_name = name or filename

        # Save file
        file_path = self.file_store.save_upload(file_content, dataset_id, filename)

        # Compute hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Quick parse to get row/column counts
        try:
            df = pd.read_csv(file_path)
            row_count = len(df)
            column_count = len(df.columns)
            columns = []
            for col in df.columns:
                col_type = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else \
                           "datetime" if pd.api.types.is_datetime64_any_dtype(df[col]) else \
                           "categorical"
                # Try parsing as datetime
                if col_type == "categorical":
                    try:
                        sample = df[col].dropna().head(20)
                        parsed = pd.to_datetime(sample, errors="coerce")
                        if parsed.notna().mean() > 0.8:
                            col_type = "datetime"
                    except Exception:
                        pass
                columns.append({"name": col, "type": col_type, "inferred": True})
        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
            row_count = 0
            column_count = 0
            columns = []

        # Save to database
        session = get_session()
        try:
            record = DatasetRecord(
                id=dataset_id,
                name=dataset_name,
                file_path=file_path,
                file_hash=file_hash,
                row_count=row_count,
                column_count=column_count,
                column_schema=columns,
                status="uploaded",
                uploaded_at=datetime.utcnow(),
            )
            session.add(record)
            session.commit()

            logger.info(f"Created dataset {dataset_id}: {dataset_name} ({row_count} rows)")

            return {
                "id": dataset_id,
                "name": dataset_name,
                "status": "uploaded",
                "row_count": row_count,
                "column_count": column_count,
                "columns": columns,
                "file_path": file_path,
            }
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset by ID."""
        session = get_session()
        try:
            record = session.query(DatasetRecord).filter_by(id=dataset_id).first()
            if not record:
                return None

            anomaly_count = session.query(AnomalyRecord).filter_by(dataset_id=dataset_id).count()

            return {
                "id": record.id,
                "name": record.name,
                "status": record.status,
                "row_count": record.row_count,
                "column_count": record.column_count,
                "columns": record.column_schema or [],
                "time_column": record.time_column,
                "dimensions": record.dimensions or [],
                "quality_score": record.quality_score,
                "anomaly_count": anomaly_count,
                "uploaded_at": record.uploaded_at,
                "processing_completed_at": record.processing_completed_at,
                "error_message": record.error_message,
                "file_path": record.file_path,
            }
        finally:
            session.close()

    def list_datasets(
        self, page: int = 1, per_page: int = 20, status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List datasets with pagination."""
        session = get_session()
        try:
            query = session.query(DatasetRecord)
            if status:
                query = query.filter_by(status=status)

            total = query.count()
            records = (
                query.order_by(DatasetRecord.uploaded_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            datasets = []
            for r in records:
                anomaly_count = session.query(AnomalyRecord).filter_by(dataset_id=r.id).count()
                datasets.append({
                    "id": r.id,
                    "name": r.name,
                    "status": r.status,
                    "row_count": r.row_count,
                    "column_count": r.column_count,
                    "columns": r.column_schema or [],
                    "time_column": r.time_column,
                    "dimensions": r.dimensions or [],
                    "quality_score": r.quality_score,
                    "anomaly_count": anomaly_count,
                    "uploaded_at": r.uploaded_at,
                    "processing_completed_at": r.processing_completed_at,
                    "error_message": r.error_message,
                })

            return {"datasets": datasets, "total": total, "page": page, "per_page": per_page}
        finally:
            session.close()

    def update_dataset_status(
        self, dataset_id: str, status: str, **kwargs
    ):
        """Update dataset status and metadata."""
        session = get_session()
        try:
            record = session.query(DatasetRecord).filter_by(id=dataset_id).first()
            if record:
                record.status = status
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def save_analysis_results(
        self, dataset_id: str, results: Dict[str, Any]
    ):
        """Save analysis results (anomalies, root causes, explanations) to database."""
        session = get_session()
        try:
            # Save anomalies
            for anomaly_data in results.get("anomalies", []):
                anomaly_record = AnomalyRecord(
                    id=anomaly_data["id"],
                    dataset_id=dataset_id,
                    timestamp=pd.to_datetime(anomaly_data["timestamp"]) if anomaly_data.get("timestamp") else None,
                    metric=anomaly_data["metric"],
                    value=anomaly_data["value"],
                    expected_min=anomaly_data.get("expected_min"),
                    expected_max=anomaly_data.get("expected_max"),
                    anomaly_type=anomaly_data["anomaly_type"],
                    severity=anomaly_data["severity"],
                    confidence=anomaly_data["confidence"],
                    dimensions=anomaly_data.get("dimensions", {}),
                    algorithm_scores=anomaly_data.get("algorithm_scores", {}),
                )
                session.add(anomaly_record)

            # Save root causes
            for rc_data in results.get("root_causes", []):
                if rc_data:
                    rc_record = RootCauseRecord(
                        anomaly_id=rc_data["anomaly_id"],
                        hypothesis=rc_data.get("hypothesis", ""),
                        primary_drivers=rc_data.get("primary_drivers", []),
                        correlations=rc_data.get("correlations", []),
                        change_point=rc_data.get("change_point"),
                        confidence=rc_data.get("confidence", 0),
                        methods_used=rc_data.get("methods_used", []),
                        supporting_evidence=rc_data.get("supporting_evidence", {}),
                        processing_time_sec=rc_data.get("processing_time_sec", 0),
                    )
                    session.add(rc_record)

            # Save explanations
            for exp_data in results.get("explanations", []):
                if exp_data:
                    exp_record = ExplanationRecord(
                        anomaly_id=exp_data["anomaly_id"],
                        text=exp_data.get("text", ""),
                        summary=exp_data.get("summary", ""),
                        recommendations=exp_data.get("recommendations", []),
                        confidence=exp_data.get("confidence", 0),
                        evidence_citations=exp_data.get("evidence_citations", []),
                        llm_model=exp_data.get("llm_model"),
                        tokens_input=exp_data.get("tokens_input", 0),
                        tokens_output=exp_data.get("tokens_output", 0),
                        latency_ms=exp_data.get("latency_ms", 0),
                        used_fallback=exp_data.get("used_fallback", False),
                    )
                    session.add(exp_record)

            session.commit()
            logger.info(f"Saved analysis results for dataset {dataset_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save analysis results: {e}")
            raise
        finally:
            session.close()

    def get_anomalies(
        self,
        dataset_id: str,
        severity_min: float = 0.0,
        anomaly_type: Optional[str] = None,
        metric: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        """Get anomalies for a dataset with filters."""
        session = get_session()
        try:
            query = session.query(AnomalyRecord).filter_by(dataset_id=dataset_id)

            if severity_min > 0:
                query = query.filter(AnomalyRecord.severity >= severity_min)
            if anomaly_type:
                query = query.filter_by(anomaly_type=anomaly_type)
            if metric:
                query = query.filter_by(metric=metric)

            total = query.count()

            records = (
                query.order_by(AnomalyRecord.severity.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            anomalies = []
            for r in records:
                anomalies.append({
                    "id": r.id,
                    "dataset_id": r.dataset_id,
                    "timestamp": str(r.timestamp) if r.timestamp else None,
                    "metric": r.metric,
                    "value": r.value,
                    "expected_min": r.expected_min,
                    "expected_max": r.expected_max,
                    "anomaly_type": r.anomaly_type,
                    "severity": r.severity,
                    "confidence": r.confidence,
                    "dimensions": r.dimensions or {},
                })

            # Summary
            all_records = session.query(AnomalyRecord).filter_by(dataset_id=dataset_id).all()
            summary = self._build_anomaly_summary(all_records)

            return {
                "anomalies": anomalies,
                "summary": summary,
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        finally:
            session.close()

    def get_anomaly_detail(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        """Get full anomaly detail with root cause and explanation."""
        session = get_session()
        try:
            anomaly = session.query(AnomalyRecord).filter_by(id=anomaly_id).first()
            if not anomaly:
                return None

            result = {
                "anomaly": {
                    "id": anomaly.id,
                    "dataset_id": anomaly.dataset_id,
                    "timestamp": str(anomaly.timestamp) if anomaly.timestamp else None,
                    "metric": anomaly.metric,
                    "value": anomaly.value,
                    "expected_min": anomaly.expected_min,
                    "expected_max": anomaly.expected_max,
                    "anomaly_type": anomaly.anomaly_type,
                    "severity": anomaly.severity,
                    "confidence": anomaly.confidence,
                    "dimensions": anomaly.dimensions or {},
                },
            }

            # Root cause
            rc = session.query(RootCauseRecord).filter_by(anomaly_id=anomaly_id).first()
            if rc:
                result["root_cause"] = {
                    "primary_drivers": rc.primary_drivers or [],
                    "correlations": rc.correlations or [],
                    "change_point": rc.change_point,
                    "hypothesis": rc.hypothesis,
                    "confidence": rc.confidence,
                    "methods_used": rc.methods_used or [],
                }

            # Explanation
            exp = session.query(ExplanationRecord).filter_by(anomaly_id=anomaly_id).first()
            if exp:
                result["explanation"] = {
                    "text": exp.text,
                    "summary": exp.summary,
                    "recommendations": exp.recommendations or [],
                    "confidence": exp.confidence,
                    "evidence_citations": exp.evidence_citations or [],
                    "llm_model": exp.llm_model,
                    "used_fallback": exp.used_fallback,
                    "generated_at": exp.generated_at,
                }

            return result
        finally:
            session.close()

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete dataset and all associated data."""
        session = get_session()
        try:
            record = session.query(DatasetRecord).filter_by(id=dataset_id).first()
            if not record:
                return False

            session.delete(record)
            session.commit()

            # Delete files
            self.file_store.delete_dataset_files(dataset_id)
            logger.info(f"Deleted dataset {dataset_id}")
            return True
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def load_dataframe(self, dataset_id: str) -> Optional[pd.DataFrame]:
        """Load CSV file as DataFrame for a dataset."""
        dataset = self.get_dataset(dataset_id)
        if not dataset or not dataset.get("file_path"):
            return None

        file_path = Path(dataset["file_path"])
        if not file_path.exists():
            return None

        return pd.read_csv(file_path)

    def _build_anomaly_summary(self, records) -> Dict[str, Any]:
        if not records:
            return {
                "total_anomalies": 0,
                "avg_severity": 0,
                "by_type": {},
                "by_severity_level": {},
            }

        severities = [r.severity for r in records]
        types = [r.anomaly_type for r in records]

        severity_levels = {}
        for s in severities:
            if s >= 0.7:
                level = "critical"
            elif s >= 0.4:
                level = "high"
            elif s >= 0.2:
                level = "medium"
            else:
                level = "low"
            severity_levels[level] = severity_levels.get(level, 0) + 1

        return {
            "total_anomalies": len(records),
            "avg_severity": float(sum(severities) / len(severities)),
            "by_type": {t: types.count(t) for t in set(types)},
            "by_severity_level": severity_levels,
        }
