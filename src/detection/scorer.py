"""
Confidence Scoring and Severity Calculation

Combines multiple algorithm outputs into a unified confidence score (0-100).
Calculates severity based on anomaly magnitude and confidence.
"""

import pandas as pd
from typing import List, Dict, Optional
from .models import Anomaly, AnomalyType


def calculate_confidence(
    algorithm_votes: int,
    total_algorithms: int,
    avg_score: float,
    relative_magnitude: float,
    data_volume_factor: float = 1.0
) -> float:
    """
    Calculate overall confidence score (0-100).

    Confidence is based on:
    - Algorithm agreement (how many methods detected this anomaly)
    - Magnitude of deviation (how extreme is the anomaly)
    - Data quality/volume factor

    Args:
        algorithm_votes: Number of algorithms that flagged this point
        total_algorithms: Total number of algorithms run
        avg_score: Average normalized anomaly score from algorithms
        relative_magnitude: |value - expected| / |expected| (relative deviation)
        data_volume_factor: Factor based on data volume (more data = more confidence)

    Returns:
        Confidence score 0-100
    """
    # Ensure relative_magnitude is scalar (handle Series from edge cases)
    if hasattr(relative_magnitude, '__iter__') and not isinstance(relative_magnitude, (str, bytes)):
        relative_magnitude = float(relative_magnitude.iloc[0] if hasattr(relative_magnitude, 'iloc') else relative_magnitude[0])
    else:
        relative_magnitude = float(relative_magnitude)

    # Algorithm consensus (0-60 points)
    consensus_score = (algorithm_votes / total_algorithms) * 60

    # Magnitude factor (0-30 points)
    magnitude_score = min(avg_score / 5.0, 1.0) * 30  # Cap at 5x deviation

    # Relative deviation factor (0-10 points)
    # Higher deviation from expected range = higher confidence
    relative_score = min(relative_magnitude, 1.0) * 10

    return consensus_score + magnitude_score + relative_score


def calculate_severity(
    confidence: float,
    normalized_deviation: float,
    anomaly_type: AnomalyType,
    is_peak: bool = False
) -> float:
    """
    Calculate severity score (0-1 scale).

    Severity differs from confidence:
    - Confidence: How sure we are this IS an anomaly
    - Severity: How BAD/important this anomaly is

    Args:
        confidence: Confidence score (0-100)
        normalized_deviation: Deviation in standard deviation units
        anomaly_type: Type of anomaly
        is_peak: If True, boost severity for extreme values

    Returns:
        Severity score 0-1
    """
    # Normalize confidence to 0-1
    conf_factor = confidence / 100.0

    # Deviation factor (how far from normal)
    dev_factor = min(normalized_deviation / 6.0, 1.0)  # Cap at 6 sigma

    # Base severity - weighted more towards confidence to avoid high severity on weak signals
    severity = 0.6 * conf_factor + 0.4 * dev_factor

    # Adjust by anomaly type (spikes/drops often more severe than deviation)
    type_multipliers = {
        AnomalyType.SPIKE: 1.2,
        AnomalyType.DROP: 1.2,
        AnomalyType.DEVIATION: 1.0,
        AnomalyType.COLLECTIVE: 1.3,
        AnomalyType.CONTEXTUAL: 0.9
    }
    type_multiplier = type_multipliers.get(anomaly_type, 1.0)

    # Peak detection boost
    if is_peak:
        type_multiplier *= 1.2

    severity = min(severity * type_multiplier, 1.0)

    return severity


def get_severity_label(severity: float) -> str:
    """Convert numeric severity to human-readable label"""
    if severity < 0.2:
        return "Low"
    elif severity < 0.4:
        return "Medium"
    elif severity < 0.7:
        return "High"
    else:
        return "Critical"


def score_anomalies(
    ensemble_results: List[Dict],
    series: pd.Series,
    expected_value: float,
    expected_range: tuple
) -> List[Anomaly]:
    """
    Convert ensemble detection results into Anomaly objects with scoring.

    Args:
        ensemble_results: List from ensemble_detection()
        series: Original time series data
        expected_value: Expected baseline value (e.g., rolling mean)
        expected_range: Tuple of (min, max) expected values

    Returns:
        List of Anomaly objects with complete scoring
    """
    anomalies = []

    for result in ensemble_results:
        timestamp = result['timestamp']
        value = result['value']

        # Ensure value is scalar (convert from possible Series/numpy type)
        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
            value = float(value.iloc[0] if hasattr(value, 'iloc') else value[0])
        else:
            value = float(value)

        # Calculate relative deviation
        if expected_value != 0:
            relative_deviation = abs(value - expected_value) / abs(expected_value)
        else:
            relative_deviation = abs(value / 1e-10)  # Avoid division by zero

        # Ensure scalar (convert from possible Series/numpy type)
        if hasattr(relative_deviation, '__iter__') and not isinstance(relative_deviation, (str, bytes)):
            relative_deviation = float(relative_deviation.iloc[0] if hasattr(relative_deviation, 'iloc') else relative_deviation[0])
        else:
            relative_deviation = float(relative_deviation)

        # Calculate confidence
        confidence = calculate_confidence(
            algorithm_votes=result['algorithm_count'],
            total_algorithms=4,  # We have 4 main algorithms
            avg_score=result['avg_score'],
            relative_magnitude=relative_deviation
        )

        # Detect if this is a peak (highest/lowest in recent window)
        is_peak = False
        recent_values = series.loc[:timestamp].tail(30)
        if len(recent_values) > 0:
            if value >= recent_values.quantile(0.99) or value <= recent_values.quantile(0.01):
                is_peak = True

        # Use the anomaly type from ensemble result
        # This preserves spike/drop/collective/contextual classifications
        try:
            anomaly_type = AnomalyType(result['anomaly_type'])
        except ValueError:
            # Fallback if unknown type string
            anomaly_type = AnomalyType.DEVIATION

        # Calculate severity
        severity = calculate_severity(
            confidence=confidence,
            normalized_deviation=result['max_score'],
            anomaly_type=anomaly_type,
            is_peak=is_peak
        )

        # Create anomaly object
        anomaly = Anomaly(
            timestamp=timestamp,
            metric=series.name if series.name else "metric",
            value=value,
            expected_range=expected_range,
            anomaly_type=anomaly_type,
            severity=severity,
            confidence=confidence,
            algorithm_scores={
                'zscore': result.get('zscore_score'),
                'iqr': result.get('iqr_score'),
                'moving_avg': result.get('ma_score'),
                'stl': result.get('stl_score')
            }
        )

        anomalies.append(anomaly)

    # Sort by severity descending
    anomalies.sort(key=lambda x: x.severity, reverse=True)

    return anomalies


def filter_by_severity(
    anomalies: List[Anomaly],
    min_severity: float = 0.0,
    max_anomalies: Optional[int] = None
) -> List[Anomaly]:
    """
    Filter anomalies by severity and limit count if needed.

    Args:
        anomalies: List of Anomaly objects
        min_severity: Minimum severity threshold (0-1)
        max_anomalies: Maximum number to return (most severe first)

    Returns:
        Filtered list of anomalies
    """
    # Filter by severity
    filtered = [a for a in anomalies if a.severity >= min_severity]

    # Limit count if requested
    if max_anomalies:
        filtered = filtered[:max_anomalies]

    return filtered


def calculate_expected_range(
    series: pd.Series,
    method: str = "iqr",
    rolling_window: Optional[int] = None
) -> tuple:
    """
    Calculate expected range for a time series.

    Args:
        series: Time series data
        method: 'iqr', 'std', or 'percentile'
        rolling_window: If set, use rolling calculation

    Returns:
        Tuple of (expected_min, expected_max)
    """
    if rolling_window:
        if len(series) < rolling_window:
            return (series.mean(), series.mean())

        # Use recent window
        recent = series.iloc[-rolling_window:]
        mean = recent.mean()
        if method == 'iqr':
            q1 = recent.quantile(0.25)
            q3 = recent.quantile(0.75)
            iqr = q3 - q1
            return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        elif method == 'std':
            std = recent.std()
            return (mean - 3 * std, mean + 3 * std)
        else:  # percentile
            return (recent.quantile(0.01), recent.quantile(0.99))
    else:
        # Global calculation
        mean = series.mean()
        if method == 'iqr':
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        elif method == 'std':
            std = series.std()
            return (mean - 3 * std, mean + 3 * std)
        else:  # percentile
            return (series.quantile(0.01), series.quantile(0.99))
