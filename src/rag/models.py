"""
Data models for RAG module.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class Document(BaseModel):
    """Represents a raw business context document."""
    model_config = ConfigDict(extra='allow')

    id: str = Field(..., description="Unique document identifier")
    org_id: str = Field(..., description="Organization ID")
    title: Optional[str] = Field(None, description="Document title")
    source_path: str = Field(..., description="Original file path or source")
    document_type: str = Field(..., description="Type: metric_def|process|incident|other")
    content: str = Field(..., description="Full text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class DocumentChunk(BaseModel):
    """Represents a chunk of a document with embedding."""
    model_config = ConfigDict(extra='allow')

    id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Source document ID")
    org_id: str = Field(..., description="Organization ID")
    chunk_index: int = Field(..., description="Position in document (0-indexed)")
    text: str = Field(..., description="Raw chunk text content (display_text)")
    embedded_text: Optional[str] = Field(None, description="Contextualized chunk text for vector embedding")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding (384-dim)")


class RetrievalResult(BaseModel):
    """Result from a similarity search."""
    model_config = ConfigDict(extra='allow')

    chunk: DocumentChunk
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity (0-1)")
    rank: int = Field(..., description="Rank in results (1 = highest)")
    document: Optional[Document] = Field(None, description="Full document if loaded")


class RAGQuery(BaseModel):
    """Query parameters for RAG retrieval."""
    model_config = ConfigDict(extra='allow')

    query: str = Field(..., description="Search query text (raw query)")
    org_id: str = Field(..., description="Organization ID")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Metadata filters")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity threshold")
    history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Multi-turn conversation history")
    rewritten_query: Optional[str] = Field(default=None, description="Standalone rewritten query for retrieval")


class RAGResponse(BaseModel):
    """Response from RAG query."""
    model_config = ConfigDict(extra='allow')

    query: str = Field(..., description="Original query")
    results: List[RetrievalResult] = Field(default_factory=list)
    total_results: int = Field(..., description="Total matches found")
    query_time_ms: float = Field(..., description="Query execution time (ms)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
