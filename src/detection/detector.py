"""
Anomaly Detection Orchestrator

Main detector class that coordinates multiple algorithms and produces final anomalies.
Works on time series business data (DataFrame with datetime index or time column).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .models import (
    Anomaly,
    DetectionConfig,
)
from .algorithms import ensemble_detection
from .scorer import (
    score_anomalies,
    calculate_expected_range,
    filter_by_severity,
    get_severity_label,
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Main anomaly detector for time series business metrics.

    Usage:
        detector = AnomalyDetector(config)
        anomalies = detector.detect(df, metric_columns=['revenue', 'orders'])
    """

    def __init__(self, config: Optional[DetectionConfig] = None):
        """
        Initialize detector with configuration.

        Args:
            config: DetectionConfig object with parameters
        """
        self.config = config or DetectionConfig()
        logger.info(f"Initialized AnomalyDetector with config: {self.config}")

    def detect(
        self,
        data: pd.DataFrame,
        metric_columns: Optional[List[str]] = None,
        time_column: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
        max_anomalies_per_metric: int = 100
    ) -> List[Anomaly]:
        """
        Detect anomalies in time series data.

        Args:
            data: Input DataFrame
            metric_columns: List of numeric columns to analyze (auto-detect if None)
            time_column: Name of timestamp column (auto-detect if None)
            dimensions: Categorical columns for contextual/collective analysis
            max_anomalies_per_metric: Limit anomalies per metric for performance

        Returns:
            List of Anomaly objects sorted by severity
        """
        logger.info(f"Starting detection on {len(data)} rows")

        # Prepare data
        df = self._prepare_data(data, time_column)
        if df is None:
            return []

        # Auto-detect metric columns if not provided
        if metric_columns is None:
            metric_columns = self._auto_detect_metrics(df)
            logger.info(f"Auto-detected metrics: {metric_columns}")

        # Validate metrics exist
        for col in metric_columns:
            if col not in df.columns:
                logger.error(f"Metric column '{col}' not found")
                raise ValueError(f"Metric column '{col}' not found in DataFrame")

        all_anomalies = []

        # Detect anomalies for each metric
        for metric in metric_columns:
            logger.info(f"Analyzing metric: {metric}")

            # Skip non-numeric columns
            if not pd.api.types.is_numeric_dtype(df[metric]):
                logger.warning(f"Skipping non-numeric metric: {metric}")
                continue

            # Check for sufficient data
            clean_series = df[metric].dropna()
            if len(clean_series) < self.config.min_periods:
                logger.warning(f"Insufficient data for {metric}: {len(clean_series)} < {self.config.min_periods}")
                continue

            # Ensure index is appropriate
            if not isinstance(clean_series.index, pd.DatetimeIndex):
                # Use integer index
                clean_series.index = pd.RangeIndex(len(clean_series))

            # Calculate expected range for this metric
            expected_range = calculate_expected_range(
                clean_series,
                method="iqr",
                rolling_window=None
            )

            # Run ensemble detection
            ensemble_results = ensemble_detection(clean_series, self.config)

            if not ensemble_results:
                logger.info(f"No anomalies detected for {metric}")
                continue

            # Score anomalies
            expected_value = clean_series.median()
            anomalies = score_anomalies(
                ensemble_results,
                clean_series,
                expected_value,
                expected_range
            )

            # Set metric name
            for anomaly in anomalies:
                anomaly.metric = metric

            all_anomalies.extend(anomalies)

            logger.info(f"Detected {len(anomalies)} anomalies for {metric}")

        # Filter globally and sort - use higher threshold to reduce false positives
        final_anomalies = filter_by_severity(
            all_anomalies,
            min_severity=0.15,  # Minimum threshold (adjusted for better detection)
            max_anomalies=max_anomalies_per_metric * len(metric_columns)
        )

        # Add dimensions if provided
        if dimensions:
            final_anomalies = self._enrich_with_dimensions(final_anomalies, df, dimensions)

        # Sort by severity (highest first)
        final_anomalies.sort(key=lambda x: x.severity, reverse=True)

        logger.info(f"Total anomalies detected: {len(final_anomalies)}")
        return final_anomalies

    def detect_with_groupby(
        self,
        data: pd.DataFrame,
        metric: str,
        groupby_column: str,
        time_column: Optional[str] = None
    ) -> List[Anomaly]:
        """
        Detect anomalies within groups (contextual detection).

        Example: Detect revenue anomalies separately for each region.

        Args:
            data: Input DataFrame
            metric: Metric column to analyze
            groupby_column: Column to group by
            time_column: Timestamp column name

        Returns:
            List of anomalies with group information
        """
        df = self._prepare_data(data, time_column)
        if df is None:
            return []

        if metric not in df.columns:
            raise ValueError(f"Metric '{metric}' not found")
        if groupby_column not in df.columns:
            raise ValueError(f"Groupby column '{groupby_column}' not found")

        all_anomalies = []

        for group_name, group_data in df.groupby(groupby_column):
            series = group_data[metric].dropna()

            if len(series) < self.config.min_periods:
                continue

            # Detect within group
            expected_range = calculate_expected_range(series, method="iqr")
            ensemble_results = ensemble_detection(series, self.config)
            expected_value = series.median()

            anomalies = score_anomalies(
                ensemble_results,
                series,
                expected_value,
                expected_range
            )

            # Add group information
            for anomaly in anomalies:
                anomaly.dimensions = {groupby_column: str(group_name)}

            all_anomalies.extend(anomalies)

        # Sort by severity
        all_anomalies.sort(key=lambda x: x.severity, reverse=True)
        return all_anomalies

    def _prepare_data(
        self,
        data: pd.DataFrame,
        time_column: Optional[str]
    ) -> Optional[pd.DataFrame]:
        """
        Prepare DataFrame: set time index, sort, clean.
        """
        df = data.copy()

        # Handle time column
        if time_column:
            if time_column not in df.columns:
                logger.error(f"Time column '{time_column}' not found")
                return None

            df[time_column] = pd.to_datetime(df[time_column], errors='coerce')
            df = df.set_index(time_column)
        else:
            # Try to auto-detect datetime column
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df = df.set_index(col)
                    break

        # Sort by time
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        return df

    def _auto_detect_metrics(self, df: pd.DataFrame) -> List[str]:
        """
        Auto-detect numeric columns that look like metrics.
        """
        metrics = []
        for col in df.columns:
            # Skip time/datetime columns
            if col == df.index.name:
                continue
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
            # Include numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):
                metrics.append(col)
        return metrics

    def _enrich_with_dimensions(
        self,
        anomalies: List[Anomaly],
        df: pd.DataFrame,
        dimensions: List[str]
    ) -> List[Anomaly]:
        """
        Add dimension information to anomalies.
        """
        # Validate dimensions exist
        valid_dims = [d for d in dimensions if d in df.columns]
        if not valid_dims:
            return anomalies

        # For each anomaly, attach dimension values at that timestamp
        for anomaly in anomalies:
            # Find closest row to timestamp
            try:
                closest_idx = df.index.get_indexer([anomaly.timestamp], method='nearest')[0]
                if closest_idx >= 0:
                    dim_values = {}
                    for dim in valid_dims:
                        val = df.iloc[closest_idx][dim]
                        if pd.notna(val):
                            dim_values[dim] = str(val)
                    if dim_values:
                        anomaly.dimensions = dim_values
            except Exception as e:
                logger.debug(f"Could not enrich dimensions for anomaly at {anomaly.timestamp}: {e}")

        return anomalies

    def get_detection_summary(self, anomalies: List[Anomaly]) -> Dict[str, Any]:
        """
        Generate summary statistics for a set of anomalies.
        """
        if not anomalies:
            return {
                "total_anomalies": 0,
                "by_type": {},
                "by_severity": {},
                "avg_severity": 0,
                "avg_confidence": 0
            }

        types = [a.anomaly_type.value for a in anomalies]
        severity_levels = [get_severity_label(a.severity) for a in anomalies]

        return {
            "total_anomalies": len(anomalies),
            "by_type": {t: types.count(t) for t in set(types)},
            "by_severity": {s: severity_levels.count(s) for s in set(severity_levels)},
            "avg_severity": np.mean([a.severity for a in anomalies]),
            "avg_confidence": np.mean([a.confidence for a in anomalies]),
            "metrics_affected": list(set([a.metric for a in anomalies]))
        }


def detect_anomalies(
    data: pd.DataFrame,
    config: Optional[DetectionConfig] = None,
    **kwargs
) -> List[Anomaly]:
    """
    Convenience function for one-off anomaly detection.

    Args:
        data: DataFrame with time series data
        config: DetectionConfig (uses default if None)
        **kwargs: Additional arguments passed to AnomalyDetector.detect()

    Returns:
        List of Anomaly objects

    Example:
        anomalies = detect_anomalies(df, metric_columns=['revenue'])
    """
    detector = AnomalyDetector(config)
    return detector.detect(data, **kwargs)
