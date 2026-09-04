"""
API Request models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class DatasetUploadParams(BaseModel):
    """Parameters for CSV upload."""
    name: Optional[str] = None
    time_column: Optional[str] = None
    dimensions: List[str] = Field(default_factory=list)


class AnomalyFilterParams(BaseModel):
    """Filters for anomaly listing."""
    severity_min: float = 0.0
    anomaly_type: Optional[str] = None
    metric: Optional[str] = None
    page: int = 1
    per_page: int = 50


class RAGQueryRequest(BaseModel):
    """RAG query request."""
    query: str
    top_k: int = 5
    min_score: float = 0.0
    filters: Dict[str, Any] = Field(default_factory=dict)
    model: Optional[str] = "llama3.2:3b"
    generate_answer: bool = True
    processing_mode: Optional[str] = "local"
    api_key: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)

