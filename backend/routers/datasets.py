"""
Dataset management router.

Handles CSV upload, listing, and dataset details.
"""

import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from typing import Dict, Any
from datetime import datetime

from ..dependencies import get_dataset_service, get_analysis_service
from ..models.responses import (
    DatasetResponse,
    DatasetListResponse,
    UploadResponse,
    ColumnSchemaResponse,
)
from ..utils.firebase_auth import get_current_user_optional
from ..storage.database import get_session, UserAccessLogRecord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/datasets", tags=["Datasets"])

# Max upload size 500MB
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    time_column: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    """
    Upload a CSV file and run analysis.

    The analysis pipeline runs synchronously:
    1. Parse and validate CSV
    2. Detect anomalies (statistical methods)
    3. Root cause analysis
    4. Generate explanations
    """
    # Validate file type
    if not file.filename.lower().endswith((".csv", ".tsv")):
        raise HTTPException(status_code=415, detail="Only CSV/TSV files are supported")

    # Read file content
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 500MB)")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Create dataset record
    dataset_svc = get_dataset_service()
    dataset = dataset_svc.create_dataset(
        file_content=content,
        filename=file.filename,
        name=name,
    )

    dataset_id = dataset["id"]

    # Security: Audit log dataset upload
    try:
        db = get_session()
        log_entry = UserAccessLogRecord(
            user_id=current_user.get("uid") if current_user else "anonymous",
            email=current_user.get("email") if current_user else None,
            name=current_user.get("name") if current_user else None,
            action="upload_dataset",
            path=request.url.path,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")[:200],
            meta_info={"dataset_id": dataset_id, "filename": file.filename, "size_bytes": len(content)},
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Could not record dataset upload audit log: {e}")

    # Run analysis
    try:
        dataset_svc.update_dataset_status(dataset_id, "analyzing")

        analysis_svc = get_analysis_service()

        # Load the DataFrame
        import pandas as pd
        from pathlib import Path

        df = pd.read_csv(dataset["file_path"])

        # Parse dimensions
        dim_list = []
        if dimensions:
            dim_list = [d.strip() for d in dimensions.split(",") if d.strip()]

        # Run full pipeline
        results = analysis_svc.run_full_analysis(
            df=df,
            dataset_id=dataset_id,
            time_column=time_column,
            dimensions=dim_list if dim_list else None,
        )

        # Save results to database
        dataset_svc.save_analysis_results(dataset_id, results)

        # Update dataset status
        from datetime import datetime

        detected_dims = analysis_svc._detect_dimensions(df, time_column)
        dataset_svc.update_dataset_status(
            dataset_id,
            "completed",
            time_column=time_column or analysis_svc._detect_time_column(df),
            dimensions=dim_list if dim_list else detected_dims,
            processing_completed_at=datetime.utcnow(),
        )

        anomaly_count = len(results.get("anomalies", []))

        return UploadResponse(
            dataset_id=dataset_id,
            name=dataset["name"],
            status="completed",
            row_count=dataset["row_count"],
            column_count=dataset["column_count"],
            anomalies_detected=anomaly_count,
            message=f"Analysis complete. {anomaly_count} anomalies detected.",
        )

    except Exception as e:
        logger.error(f"Analysis failed for dataset {dataset_id}: {e}", exc_info=True)
        dataset_svc.update_dataset_status(
            dataset_id, "failed", error_message=str(e)
        )
        return UploadResponse(
            dataset_id=dataset_id,
            name=dataset["name"],
            status="failed",
            row_count=dataset["row_count"],
            column_count=dataset["column_count"],
            message=f"Analysis failed: {str(e)[:200]}",
        )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
):
    """List all datasets with pagination."""
    dataset_svc = get_dataset_service()
    result = dataset_svc.list_datasets(page=page, per_page=per_page, status=status)

    datasets = [
        DatasetResponse(
            id=d["id"],
            name=d["name"],
            status=d["status"],
            row_count=d["row_count"],
            column_count=d["column_count"],
            columns=[ColumnSchemaResponse(**c) for c in d.get("columns", [])],
            time_column=d.get("time_column"),
            dimensions=d.get("dimensions", []),
            quality_score=d.get("quality_score"),
            anomaly_count=d.get("anomaly_count", 0),
            uploaded_at=d.get("uploaded_at"),
            processing_completed_at=d.get("processing_completed_at"),
            error_message=d.get("error_message"),
        )
        for d in result["datasets"]
    ]

    return DatasetListResponse(
        datasets=datasets,
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str):
    """Get dataset details."""
    dataset_svc = get_dataset_service()
    dataset = dataset_svc.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return DatasetResponse(
        id=dataset["id"],
        name=dataset["name"],
        status=dataset["status"],
        row_count=dataset["row_count"],
        column_count=dataset["column_count"],
        columns=[ColumnSchemaResponse(**c) for c in dataset.get("columns", [])],
        time_column=dataset.get("time_column"),
        dimensions=dataset.get("dimensions", []),
        quality_score=dataset.get("quality_score"),
        anomaly_count=dataset.get("anomaly_count", 0),
        uploaded_at=dataset.get("uploaded_at"),
        processing_completed_at=dataset.get("processing_completed_at"),
        error_message=dataset.get("error_message"),
    )


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset and all associated data."""
    dataset_svc = get_dataset_service()
    success = dataset_svc.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted", "id": dataset_id}
