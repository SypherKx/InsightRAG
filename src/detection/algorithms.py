"""
Statistical Anomaly Detection Algorithms

Pure mathematical/statistical methods for detecting anomalies in time series data.
No LLM involvement - deterministic, fast, and interpretable.
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Dict
from scipy import stats
from statsmodels.tsa.seasonal import STL
import warnings
warnings.filterwarnings('ignore')


def detect_zscore(
    series: pd.Series,
    threshold: float = 3.0,
    rolling_window: Optional[int] = None,
    min_periods: int = 10
) -> Tuple[List[int], List[float], List[str]]:
    """
    Z-score based anomaly detection.

    Flags points where |z-score| > threshold.
    Z-score = (value - mean) / std_dev

    For time series, can use rolling window for adaptive baseline.

    Args:
        series: Time series data (pandas Series with datetime index or numeric index)
        threshold: Z-score threshold (default 3.0 means 99.7% of normal data)
        rolling_window: If set, use rolling mean/std over this window
        min_periods: Minimum points required for calculation

    Returns:
        Tuple of (anomaly_indices, z_scores, anomaly_types)
    """
    if len(series) < min_periods:
        return [], [], []

    clean_series = series.dropna()
    if len(clean_series) < min_periods:
        return [], [], []

    if rolling_window and rolling_window > 1:
        effective_min_periods = min(min_periods, rolling_window)
        # Shift window by 1 so current point is evaluated against past history only
        rolling_mean = clean_series.shift(1).rolling(window=rolling_window, min_periods=effective_min_periods).mean()
        rolling_std = clean_series.shift(1).rolling(window=rolling_window, min_periods=effective_min_periods).std()

        epsilon = 1e-9
        safe_std = rolling_std.copy()
        safe_std[safe_std < epsilon] = epsilon

        z_scores = (clean_series - rolling_mean) / safe_std
    else:
        mean = clean_series.mean()
        std = clean_series.std()
        if std == 0:
            return [], [], []
        z_scores = (clean_series - mean) / std

    anomaly_mask = np.abs(z_scores.values) > threshold
    anomaly_indices = clean_series.index[anomaly_mask].tolist()
    anomaly_scores = z_scores.loc[anomaly_mask].tolist()

    anomaly_types = ["spike" if score > 0 else "drop" for score in anomaly_scores]
    return anomaly_indices, anomaly_scores, anomaly_types


def detect_iqr(
    series: pd.Series,
    multiplier: float = 1.5,
    min_periods: int = 10
) -> Tuple[List[int], List[float], List[str]]:
    """
    Interquartile Range (IQR) anomaly detection.

    Robust to non-normal distributions and outliers in the baseline.
    Flags points outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR].

    Args:
        series: Time series data
        multiplier: IQR multiplier (1.5 = Tukey's fences, 3.0 = extreme outliers)
        min_periods: Minimum points required

    Returns:
        Tuple of (anomaly_indices, iqr_scores, anomaly_types)
    """
    if len(series) < min_periods:
        return [], [], []

    clean_series = series.dropna()
    if len(clean_series) < min_periods:
        return [], [], []

    q1 = clean_series.quantile(0.25)
    q3 = clean_series.quantile(0.75)
    iqr = q3 - q1

    if iqr == 0:
        return [], [], []

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    anomaly_mask = (clean_series < lower_bound) | (clean_series > upper_bound)
    anomaly_indices = clean_series.index[anomaly_mask].tolist()

    anomaly_scores = []
    anomaly_types = []
    for idx, value in clean_series.loc[anomaly_mask].items():
        if value > upper_bound:
            anomaly_scores.append((value - upper_bound) / iqr)
            anomaly_types.append("spike")
        else:
            anomaly_scores.append((lower_bound - value) / iqr)
            anomaly_types.append("drop")

    return anomaly_indices, anomaly_scores, anomaly_types


def detect_moving_average(
    series: pd.Series,
    window: int = 7,
    deviation_threshold: float = 2.0,
    min_periods: int = 10,
    seasonal_adjustment: bool = True
) -> Tuple[List[int], List[float], List[str]]:
    """
    Moving average deviation detection.

    Detects points deviating from recent trend, accounting for seasonality.

    Args:
        series: Time series data
        window: Rolling window for moving average
        deviation_threshold: Std deviations from MA to flag anomaly
        min_periods: Minimum points required
        seasonal_adjustment: If True, remove seasonality before MA

    Returns:
        Tuple of (anomaly_indices, deviation_scores, anomaly_types)
    """
    if len(series) < min_periods:
        return [], [], []

    clean_idx = series.dropna().index
    if len(clean_idx) < min_periods:
        return [], [], []

    clean_series = series.loc[clean_idx]
    effective_min_periods = min(min_periods, window)
    # Shift window by 1 so current point is evaluated against past history only
    rolling_mean = clean_series.shift(1).rolling(window=window, min_periods=effective_min_periods).mean()
    rolling_std = clean_series.shift(1).rolling(window=window, min_periods=effective_min_periods).std()

    valid_mask = ~(rolling_mean.isna() | rolling_std.isna())
    valid_series = clean_series[valid_mask]
    valid_mean = rolling_mean[valid_mask]
    valid_std = rolling_std[valid_mask]

    if valid_series.empty:
        return [], [], []

    epsilon = 1e-9
    safe_std = valid_std.copy()
    safe_std[safe_std < epsilon] = epsilon

    deviation = (valid_series - valid_mean) / safe_std
    anomaly_mask = np.abs(deviation.values) > deviation_threshold
    anomaly_indices = valid_series.index[anomaly_mask].tolist()
    anomaly_scores = deviation.loc[anomaly_mask].tolist()
    anomaly_types = ["spike" if score > 0 else "drop" for score in anomaly_scores]

    return anomaly_indices, anomaly_scores, anomaly_types


def detect_seasonal_decomposition(
    series: pd.Series,
    period: int = 7,
    deviation_threshold: float = 3.0,
    robust: bool = True
) -> Tuple[List[int], List[float], List[str]]:
    """
    STL (Seasonal-Trend decomposition using LOESS) anomaly detection.

    Separates time series into trend, seasonal, and residual components.
    Flags anomalies in the residual component.

    Args:
        series: Time series data with regular frequency
        period: Seasonal period (7 for weekly, 12 for monthly, 24 for hourly)
        deviation_threshold: Std deviations of residual to flag
        robust: Use robust LOESS to downweight outliers

    Returns:
        Tuple of (anomaly_indices, residual_scores, anomaly_types)
    """
    # Need enough data for decomposition
    min_required = period * 2 + 1
    if len(series) < min_required:
        return [], [], []

    # Interpolate missing values
    clean_series = series.interpolate(method='linear')
    if clean_series.isna().any():
        clean_series = clean_series.bfill().ffill()

    try:
        # STL decomposition
        stl = STL(clean_series, period=period, robust=robust, seasonal=min(period, 13))
        result = stl.fit()

        # Anomalies in residual
        residual = result.resid
        resid_mean = residual.mean()
        resid_std = residual.std()

        if resid_std == 0:
            return [], [], []

        z_scores = (residual - resid_mean) / resid_std
        anomaly_mask = np.abs(z_scores.values) > deviation_threshold

        anomaly_indices = residual.index[anomaly_mask].tolist()
        anomaly_scores = z_scores.loc[anomaly_indices].tolist()

        # Classify
        anomaly_types = []
        for score in anomaly_scores:
            if score > 0:
                anomaly_types.append("spike")
            else:
                anomaly_types.append("drop")

        return anomaly_indices, anomaly_scores, anomaly_types

    except Exception as e:
        # STL can fail with insufficient data or edge cases
        return [], [], []


def detect_change_point(
    series: pd.Series,
    method: str = "pettitt",
    significance: float = 0.05,
    min_segment_length: int = 10
) -> Tuple[List[int], List[float], List[str]]:
    """
    Change point detection for sudden shifts in data distribution.

    Identifies points where the statistical properties (mean, variance) change.

    Args:
        series: Time series data
        method: 'pettitt' (non-parametric), 'cusum' (cumulative sum), or 'bayesian'
        significance: p-value threshold for detecting change
        min_segment_length: Minimum data points before/after change point

    Returns:
        Tuple of (change_point_indices, p_values/strengths, change_types)
    """
    if len(series) < 2 * min_segment_length:
        return [], [], []

    clean_series = series.dropna().values
    n = len(clean_series)

    if n < 2 * min_segment_length:
        return [], [], []

    change_points = []
    change_scores = []
    change_types = []

    if method == "pettitt":
        # Pettitt test for single change point
        # Non-parametric, based on rank sums
        R = stats.rankdata(clean_series)
        K = []

        for t in range(min_segment_length, n - min_segment_length):
            R1 = np.sum(R[:t])
            R2 = np.sum(R[t:])
            K_stat = np.abs(R1 - t * (n + 1) / 2 - (n - t) * (n + 1) / 2)
            K.append((t, K_stat))

        if K:
            # Find maximum K statistic
            best_t, best_K = max(K, key=lambda x: x[1])

            # Calculate p-value
            p_value = 2 * np.exp(-6 * best_K**2 / (n**3 + n**2))

            if p_value < significance:
                change_points.append(clean_series.index[best_t] if hasattr(clean_series, 'index') else best_t)
                change_scores.append(1 - p_value)  # Convert to confidence-like score
                change_types.append("distribution_shift")

                # Mark points around change point as affected
                for i in range(max(0, best_t-2), min(n, best_t+3)):
                    if i != best_t and i not in change_points:
                        change_points.append(i)
                        change_scores.append(0.5)
                        change_types.append("collective")

    elif method == "cusum":
        # Cumulative Sum control chart
        mean = np.mean(clean_series[:min_segment_length])
        std = np.std(clean_series[:min_segment_length])

        if std == 0:
            return [], [], []

        S_plus = np.zeros(n)
        S_minus = np.zeros(n)

        for i in range(1, n):
            deviation = (clean_series[i] - mean) / std
            S_plus[i] = max(0, S_plus[i-1] + deviation - 0.5)
            S_minus[i] = max(0, S_minus[i-1] - deviation - 0.5)

        # Detect when CUSUM exceeds threshold (usually 5 * sigma)
        threshold = 5 * std
        for i in range(min_segment_length, n):
            if S_plus[i] > threshold or S_minus[i] > threshold:
                if i not in change_points:
                    change_points.append(i)
                    change_scores.append(min(S_plus[i], S_minus[i]) / threshold)
                    if S_plus[i] > S_minus[i]:
                        change_types.append("spike_shift")
                    else:
                        change_types.append("drop_shift")

    return change_points, change_scores, change_types


def detect_collective_anomaly(
    series: pd.Series,
    window: int = 5,
    deviation_threshold: float = 2.5,
    min_consecutive: int = 2
) -> Tuple[List[int], List[float], List[str]]:
    """
    Detect collective anomalies - sequences of unusual values.

    Uses moving average deviation to find anomalous points, then groups
    consecutive ones into collective anomalies.

    Args:
        series: Time series data
        window: Lookback window for moving average deviation
        deviation_threshold: Threshold on deviation (in local std units)
        min_consecutive: Minimum consecutive points to flag as collective

    Returns:
        Tuple of (anomaly_indices, scores, anomaly_types)
    """
    # Use moving average detection as base
    candidate_indices, candidate_scores, candidate_types = detect_moving_average(
        series,
        window=window,
        deviation_threshold=deviation_threshold,
        min_periods=max(3, min(5, window))  # at least 3 points
    )

    if not candidate_indices:
        return [], [], []

    # Group consecutive indices
    sorted_indices = sorted(candidate_indices)
    collective_indices = []
    collective_scores = []
    collective_types = []

    current_run = []
    for idx in sorted_indices:
        if not current_run:
            current_run.append(idx)
        else:
            # Check if consecutive (numeric index)
            if hasattr(idx, '__sub__'):
                # For numeric indices, check if sequential
                consecutive = (idx - current_run[-1]) == 1
            else:
                # For datetime, treat as consecutive if within a day (simplified)
                try:
                    consecutive = (idx - current_run[-1]).total_seconds() <= 86400
                except:
                    consecutive = False

            if consecutive:
                current_run.append(idx)
            else:
                if len(current_run) >= min_consecutive:
                    collective_indices.extend(current_run)
                    # Use max score in the run as collective score
                    run_scores = [candidate_scores[candidate_indices.index(i)] for i in current_run]
                    collective_scores.extend([max(run_scores)] * len(current_run))
                    collective_types.extend(["collective"] * len(current_run))
                current_run = [idx]

    # Handle last run
    if len(current_run) >= min_consecutive:
        collective_indices.extend(current_run)
        run_scores = [candidate_scores[candidate_indices.index(i)] for i in current_run]
        collective_scores.extend([max(run_scores)] * len(current_run))
        collective_types.extend(["collective"] * len(current_run))

    return collective_indices, collective_scores, collective_types


def detect_contextual_anomaly(
    series: pd.Series,
    groups: pd.Series,
    threshold: float = 2.0
) -> Tuple[List[int], List[float], List[str]]:
    """
    Detect contextual anomalies - normal in isolation but abnormal for context.

    Example: A revenue spike in December might be normal due to holidays,
    but the same spike in February would be anomalous.

    Args:
        series: Time series data
        groups: Categorical series defining context groups (e.g., day_of_week, region)
        threshold: Z-score threshold within group

    Returns:
        Tuple of (anomaly_indices, contextual_scores, anomaly_types)
    """
    anomaly_indices = []
    anomaly_scores = []
    anomaly_types = []

    # Align series and groups
    aligned = pd.concat([series, groups], axis=1).dropna()
    if aligned.empty:
        return [], [], []

    aligned.columns = ['value', 'group']

    # Check each group separately
    for group_val, group_data in aligned.groupby('group'):
        group_series = group_data['value']

        if len(group_series) < 10:  # Need enough data per group
            continue

        # Apply z-score within group
        indices, scores, types = detect_zscore(group_series, threshold=threshold)
        anomaly_indices.extend(indices)
        anomaly_scores.extend(scores)
        anomaly_types.extend([f"contextual_{t}" for t in types])

    return anomaly_indices, anomaly_scores, anomaly_types


def ensemble_detection(
    series: pd.Series,
    config: 'DetectionConfig'
) -> List[Dict]:
    """
    Run multiple detection algorithms and combine results.

    Args:
        series: Time series data
        config: Detection configuration

    Returns:
        List of anomaly dictionaries with combined scores
    """
    all_anomalies = {}

    # Algorithm 1: Z-Score
    z_indices, z_scores, z_types = detect_zscore(
        series,
        threshold=config.z_threshold,
        rolling_window=config.z_rolling_window,
        min_periods=config.min_periods
    )
    for idx, score, atype in zip(z_indices, z_scores, z_types):
        if idx not in all_anomalies:
            all_anomalies[idx] = {
                'value': series.loc[idx],
                'type_votes': [],
                'scores': []
            }
        all_anomalies[idx]['type_votes'].append(atype)
        all_anomalies[idx]['scores'].append(abs(score))

    # Algorithm 2: IQR
    iqr_indices, iqr_scores, iqr_types = detect_iqr(
        series,
        multiplier=config.iqr_multiplier,
        min_periods=config.min_periods
    )
    for idx, score, atype in zip(iqr_indices, iqr_scores, iqr_types):
        if idx not in all_anomalies:
            all_anomalies[idx] = {
                'value': series.loc[idx],
                'type_votes': [],
                'scores': []
            }
        all_anomalies[idx]['type_votes'].append(atype)
        all_anomalies[idx]['scores'].append(score)

    # Algorithm 3: Moving Average
    ma_indices, ma_scores, ma_types = detect_moving_average(
        series,
        window=config.ma_window,
        deviation_threshold=config.ma_deviation_threshold,
        min_periods=config.min_periods
    )
    for idx, score, atype in zip(ma_indices, ma_scores, ma_types):
        if idx not in all_anomalies:
            all_anomalies[idx] = {
                'value': series.loc[idx],
                'type_votes': [],
                'scores': []
            }
        all_anomalies[idx]['type_votes'].append(atype)
        all_anomalies[idx]['scores'].append(abs(score))

    # Algorithm 4: Seasonal Decomposition (if enough data)
    if len(series) >= config.seasonal_period * 2 + 1:
        stl_indices, stl_scores, stl_types = detect_seasonal_decomposition(
            series,
            period=config.seasonal_period,
            deviation_threshold=config.seasonal_deviation_threshold
        )
        for idx, score, atype in zip(stl_indices, stl_scores, stl_types):
            if idx not in all_anomalies:
                all_anomalies[idx] = {
                    'value': series.loc[idx],
                    'type_votes': [],
                    'scores': []
                }
            all_anomalies[idx]['type_votes'].append(atype)
            all_anomalies[idx]['scores'].append(abs(score))

    # Convert to list with combined information
    results = []
    for idx, data in all_anomalies.items():
        num_algorithms = len(data['scores'])

        # Vote for anomaly type (most common)
        from collections import Counter
        type_counter = Counter(data['type_votes'])
        primary_type = type_counter.most_common(1)[0][0]

        # Simplify type (strip contextual_ prefix if present)
        if primary_type.startswith('contextual_'):
            primary_type = primary_type.replace('contextual_', '')

        results.append({
            'timestamp': idx,
            'value': data['value'],
            'anomaly_type': primary_type,
            'algorithm_count': num_algorithms,
            'avg_score': np.mean(data['scores']),
            'max_score': max(data['scores'])
        })

    return results
