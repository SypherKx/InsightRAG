"""
Anomaly Detection Module - Pure Statistical Methods

This module implements statistical anomaly detection algorithms WITHOUT LLM.
Designed for time series business data (revenue, sales, metrics).

Algorithms:
- Z-Score: Standard deviation-based detection for normal distributions
- IQR: Interquartile range for robust outlier detection
- Moving Average Deviation: Seasonality-aware detection
- Change Point Detection: Sudden shifts in distribution

Detection Types:
- Point anomalies: Single data point outliers
- Collective anomalies: Sequences of unusual values
- Contextual anomalies: Deviations from expected pattern
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class AnomalyType(Enum):
    """Types of anomalies detected"""
    SPIKE = "spike"
    DROP = "drop"
    DEVIATION = "deviation"
    COLLECTIVE = "collective"
    CONTEXTUAL = "contextual"


class Severity(Enum):
    """Severity levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    timestamp: Any
    metric: str
    value: float
    expected_range: tuple
    anomaly_type: AnomalyType
    severity: float  # 0-1 scale
    confidence: float  # 0-100 scale
    dimensions: Optional[Dict[str, str]] = None
    algorithm_scores: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp,
            "metric": self.metric,
            "value": self.value,
            "expected_min": self.expected_range[0],
            "expected_max": self.expected_range[1],
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity,
            "confidence": self.confidence,
            "dimensions": self.dimensions or {},
            "algorithm_scores": self.algorithm_scores or {},
            "metadata": self.metadata or {}
        }


@dataclass
class DetectionConfig:
    """Configuration for anomaly detection"""
    # Z-Score parameters
    z_threshold: float = 3.5  # Standard deviations from mean (more conservative)
    z_rolling_window: Optional[int] = None  # If set, use rolling z-score

    # IQR parameters
    iqr_multiplier: float = 3.0  # Multiplier for IQR (extreme outliers only)

    # Moving Average parameters
    ma_window: int = 7  # Window size for moving average
    ma_deviation_threshold: float = 3.0  # Std deviations from MA

    # Seasonal decomposition
    seasonal_period: int = 7  # Seasonality period (e.g., 7 for weekly)
    seasonal_deviation_threshold: float = 3.5

    # Change Point Detection
    cp_method: str = "pettitt"  # 'pettitt', 'cusum', 'bayesian'
    cp_significance: float = 0.05  # p-value threshold

    # General
    min_periods: int = 10  # Minimum data points required
    outlier_fraction: float = 0.1  # Max fraction of points that can be outliers

    # Collective anomaly detection
    collective_window: int = 3  # Consecutive points to flag as collective
    collective_threshold: float = 2.5  # Z-score threshold for collective

    # Contextual anomaly (requires grouping)
    contextual_groupby: Optional[str] = None

    def __post_init__(self):
        """Validate configuration"""
        if self.z_threshold <= 0:
            raise ValueError("z_threshold must be positive")
        if self.iqr_multiplier <= 0:
            raise ValueError("iqr_multiplier must be positive")
        if self.ma_window < 2:
            raise ValueError("ma_window must be at least 2")
