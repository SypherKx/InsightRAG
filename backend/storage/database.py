"""
Database setup and models.

SQLAlchemy ORM with SQLite for metadata storage.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Text,
    DateTime, JSON, Boolean, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


class DatasetRecord(Base):
    """Stored dataset metadata."""
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), default="")
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    column_schema = Column(JSON, default=list)
    time_column = Column(String(100), nullable=True)
    dimensions = Column(JSON, default=list)
    status = Column(String(50), default="uploading")
    error_message = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processing_completed_at = Column(DateTime, nullable=True)

    # Relationships
    anomalies = relationship("AnomalyRecord", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_datasets_status", "status"),
    )


class AnomalyRecord(Base):
    """Detected anomaly."""
    __tablename__ = "anomalies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=True)
    metric = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    expected_min = Column(Float, nullable=True)
    expected_max = Column(Float, nullable=True)
    anomaly_type = Column(String(50), nullable=False)
    severity = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    dimensions = Column(JSON, default=dict)
    algorithm_scores = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dataset = relationship("DatasetRecord", back_populates="anomalies")
    root_cause = relationship("RootCauseRecord", back_populates="anomaly", uselist=False, cascade="all, delete-orphan")
    explanation = relationship("ExplanationRecord", back_populates="anomaly", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_anomalies_dataset", "dataset_id"),
        Index("idx_anomalies_severity", "severity"),
    )


class RootCauseRecord(Base):
    """Root cause analysis result."""
    __tablename__ = "root_causes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    anomaly_id = Column(String(36), ForeignKey("anomalies.id"), nullable=False, unique=True)
    hypothesis = Column(Text, default="")
    primary_drivers = Column(JSON, default=list)
    correlations = Column(JSON, default=list)
    change_point = Column(JSON, nullable=True)
    confidence = Column(Float, default=0.0)
    methods_used = Column(JSON, default=list)
    supporting_evidence = Column(JSON, default=dict)
    processing_time_sec = Column(Float, default=0.0)
    generated_at = Column(DateTime, default=datetime.utcnow)

    anomaly = relationship("AnomalyRecord", back_populates="root_cause")


class ExplanationRecord(Base):
    """Generated explanation."""
    __tablename__ = "explanations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    anomaly_id = Column(String(36), ForeignKey("anomalies.id"), nullable=False, unique=True)
    text = Column(Text, nullable=False)
    summary = Column(Text, default="")
    recommendations = Column(JSON, default=list)
    confidence = Column(Float, default=0.0)
    evidence_citations = Column(JSON, default=list)
    llm_model = Column(String(100), nullable=True)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    used_fallback = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    anomaly = relationship("AnomalyRecord", back_populates="explanation")


# Database engine management
_engine = None
_SessionLocal = None


def init_db(database_url: str = None):
    """Initialize database and create tables."""
    global _engine, _SessionLocal

    if database_url is None:
        database_url = "sqlite:////tmp/insightforge.db" if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) else "sqlite:///./insightforge.db"

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    try:
        _engine = create_engine(
            database_url,
            connect_args=connect_args,
            echo=False,
        )
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=_engine)
    except Exception:
        # Fallback to /tmp or memory
        fallback_url = "sqlite:////tmp/insightforge.db"
        try:
            _engine = create_engine(fallback_url, connect_args=connect_args, echo=False)
            _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
            Base.metadata.create_all(bind=_engine)
        except Exception:
            _engine = create_engine("sqlite:///:memory:", connect_args=connect_args, echo=False)
            _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
            Base.metadata.create_all(bind=_engine)

    return _engine


def get_session() -> Session:
    """Get a database session."""
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
