"""
API Response models.

Pydantic models for all API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


# ─── Dataset Responses ───

class ColumnSchemaResponse(BaseModel):
    name: str
    type: str
    inferred: bool = True


class DatasetResponse(BaseModel):
    id: str
    name: str
    status: str
    row_count: int
    column_count: int
    columns: List[ColumnSchemaResponse] = []
    time_column: Optional[str] = None
    dimensions: List[str] = []
    quality_score: Optional[float] = None
    anomaly_count: int = 0
    uploaded_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]
    total: int
    page: int = 1
    per_page: int = 20


class UploadResponse(BaseModel):
    dataset_id: str
    name: str
    status: str
    row_count: int
    column_count: int
    anomalies_detected: int = 0
    message: str = ""


# ─── Anomaly Responses ───

class AnomalyResponse(BaseModel):
    id: str
    dataset_id: str
    timestamp: Optional[str] = None
    metric: str
    value: float
    expected_min: Optional[float] = None
    expected_max: Optional[float] = None
    anomaly_type: str
    severity: float
    confidence: float
    dimensions: Dict[str, str] = {}


class AnomalySummary(BaseModel):
    total_anomalies: int = 0
    avg_severity: float = 0.0
    by_type: Dict[str, int] = {}
    by_severity_level: Dict[str, int] = {}


class AnomalyListResponse(BaseModel):
    anomalies: List[AnomalyResponse]
    summary: AnomalySummary
    total: int
    page: int = 1
    per_page: int = 50


# ─── Root Cause Responses ───

class DriverResponse(BaseModel):
    segment: str
    contribution: float
    baseline_ratio: float = 1.0
    evidence: str = ""


class CorrelationResponse(BaseModel):
    metric: str
    coefficient: float
    p_value: Optional[float] = None
    lag_hours: Optional[float] = None


class ChangePointResponse(BaseModel):
    detected_at: Optional[str] = None
    confidence: float = 0.0
    before_mean: float = 0.0
    after_mean: float = 0.0
    change_magnitude: float = 0.0


class RootCauseResponse(BaseModel):
    primary_drivers: List[DriverResponse] = []
    correlations: List[CorrelationResponse] = []
    change_point: Optional[ChangePointResponse] = None
    hypothesis: str = ""
    confidence: float = 0.0
    methods_used: List[str] = []


# ─── Explanation Responses ───

class ExplanationResponse(BaseModel):
    text: str
    summary: str = ""
    recommendations: List[str] = []
    confidence: float = 0.0
    evidence_citations: List[str] = []
    llm_model: Optional[str] = None
    used_fallback: bool = False
    generated_at: Optional[datetime] = None


# ─── Full Anomaly Detail ───

class AnomalyDetailResponse(BaseModel):
    anomaly: AnomalyResponse
    root_cause: Optional[RootCauseResponse] = None
    explanation: Optional[ExplanationResponse] = None


# ─── Health ───

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = ""
    services: Dict[str, str] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    rag_enabled: bool = False


# ─── RAG ───

class RAGQueryResponse(BaseModel):
    results: List[Dict[str, Any]] = []
    query: str = ""
    total_results: int = 0
    query_time_ms: float = 0.0
    answer: Optional[str] = None
    llm_model: Optional[str] = None
    used_llm: bool = False
    visual_snippet: Optional[Dict[str, Any]] = None


class RAGUploadResponse(BaseModel):
    documents_ingested: int = 0
    chunks_created: int = 0
    errors: int = 0
