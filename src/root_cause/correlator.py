"""
Correlation Analysis Module

Identifies metrics that are correlated with the anomaly metric.

Methodology:
1. Extract time series for anomaly metric around anomaly window
2. Extract time series for all other numeric metrics
3. Compute Pearson and Spearman correlations
4. Test for time lags (leading/lagging indicators)
5. Calculate statistical significance

Statistical approach:
- Pearson correlation for linear relationships
- Spearman rank correlation for monotonic relationships
- Cross-correlation for lag analysis
- Multiple testing correction (Bonferroni or Benjamini-Hochberg)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats, signal
from scipy.signal import correlate
import logging

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Analyzes correlations between metrics to find related events.

    Attributes:
        correlation_window: Window size (in data points) for correlation analysis
        lag_range: Range of lags to test (in hours/steps)
        min_correlation: Minimum absolute correlation to report
        significance_threshold: P-value threshold
        correction_method: Multiple testing correction ('bonferroni' or 'bh')
    """

    def __init__(
        self,
        correlation_window: int = 168,  # 1 week of hourly data
        lag_range: int = 24,  # Test up to 24 hours lag
        min_correlation: float = 0.3,
        significance_threshold: float = 0.05,
        correction_method: str = "bh",
    ):
        """
        Initialize correlation analyzer.

        Args:
            correlation_window: Window for correlation analysis
            lag_range: Maximum lag to consider
            min_correlation: Minimum correlation coefficient to report
            significance_threshold: Alpha for significance
            correction_method: Multiple testing correction method
        """
        self.correlation_window = correlation_window
        self.lag_range = lag_range
        self.min_correlation = min_correlation
        self.significance_threshold = significance_threshold
        self.correction_method = correction_method

    def analyze(
        self,
        anomaly_timestamp: pd.Timestamp,
        primary_metric: str,
        data: pd.DataFrame,
        time_column: str = "date",
        max_metrics: int = 20,
    ) -> List[Dict]:
        """
        Perform correlation analysis.

        Args:
            anomaly_timestamp: Time of anomaly
            primary_metric: The anomalous metric
            data: Full dataset
            time_column: Time column name
            max_metrics: Maximum number of metrics to analyze

        Returns:
            List of correlation results sorted by absolute correlation
        """
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [col for col in numeric_cols if col != time_column]

        # Prioritize top metrics with highest variance if count exceeds threshold
        if len(numeric_cols) > max_metrics:
            variances = {col: data[col].var() for col in numeric_cols if col != primary_metric}
            numeric_cols = sorted(variances, key=variances.get, reverse=True)[:max_metrics]

        window_data = self._extract_window(data, anomaly_timestamp, time_column)
        if len(window_data) < 10:
            logger.warning("Insufficient data points for correlation analysis")
            return []

        primary_series = window_data[primary_metric].values
        correlations = []

        for metric in numeric_cols:
            if metric == primary_metric or metric not in window_data.columns:
                continue

            metric_series = window_data[metric].values
            if np.isnan(metric_series).sum() > len(metric_series) * 0.1:
                continue

            result = self._compute_correlation(primary_series, metric_series, metric)
            if result and abs(result["coefficient"]) >= self.min_correlation:
                correlations.append(result)

        if correlations:
            correlations = self._apply_correction(correlations)

        correlations.sort(key=lambda x: abs(x["coefficient"]), reverse=True)
        return correlations

    def _extract_window(
        self, data: pd.DataFrame, anomaly_time: pd.Timestamp, time_column: str
    ) -> pd.DataFrame:
        """
        Extract time window around anomaly.

        Args:
            data: Full dataset
            anomaly_time: Anomaly timestamp
            time_column: Time column name

        Returns:
            Dataframe with window of data
        """
        # Sort by time
        data_sorted = data.sort_values(time_column).copy()

        # Find index of anomaly time or closest previous
        anomaly_idx = data_sorted[data_sorted[time_column] <= anomaly_time].index.max()
        if pd.isna(anomaly_idx):
            anomaly_idx = data_sorted.index.min()

        # Get window around anomaly
        start_idx = max(0, data_sorted.index.get_loc(anomaly_idx) - self.correlation_window // 2)
        end_idx = min(len(data_sorted), start_idx + self.correlation_window)

        return data_sorted.iloc[start_idx:end_idx].reset_index(drop=True)

    def _compute_correlation(
        self, series1: np.ndarray, series2: np.ndarray, metric_name: str
    ) -> Optional[Dict]:
        """
        Compute correlation between two series with lag analysis.

        Args:
            series1: Primary anomaly metric series
            series2: Secondary metric series
            metric_name: Name of secondary metric

        Returns:
            Dictionary with correlation results or None
        """
        # Handle NaNs
        mask = ~(np.isnan(series1) | np.isnan(series2))
        s1 = series1[mask]
        s2 = series2[mask]

        if len(s1) < 10 or len(s2) < 10:
            return None

        # Check for constant series
        if np.std(s1) == 0 or np.std(s2) == 0:
            return None

        try:
            # Pearson correlation (no lag)
            pearson_r, pearson_p = stats.pearsonr(s1, s2)

            # Spearman correlation
            spearman_r, spearman_p = stats.spearmanr(s1, s2)

            # Cross-correlation for lag detection
            lag_result = self._compute_lag_correlation(s1, s2)

            # Use Pearson as primary (more interpretable)
            if abs(pearson_r) < self.min_correlation and abs(spearman_r) < self.min_correlation:
                return None

            result = {
                "metric": metric_name,
                "coefficient": float(pearson_r),
                "p_value": float(pearson_p),
                "spearman_coefficient": float(spearman_r),
                "sample_size": len(s1),
                "method": "pearson",
            }

            if lag_result:
                result.update({
                    "lag_hours": lag_result["lag"],
                    "lag_direction": lag_result["direction"],
                    "lag_correlation": lag_result["correlation"],
                })

            return result

        except Exception as e:
            logger.debug(f"Correlation computation failed for {metric_name}: {e}")
            return None

    def _compute_lag_correlation(
        self, s1: np.ndarray, s2: np.ndarray
    ) -> Optional[Dict]:
        """
        Compute cross-correlation to find optimal lag.

        Args:
            s1: Series 1 (primary)
            s2: Series 2 (correlated)

        Returns:
            Dictionary with lag information or None
        """
        try:
            # Normalize series
            s1_norm = (s1 - np.mean(s1)) / (np.std(s1) + 1e-10)
            s2_norm = (s2 - np.mean(s2)) / (np.std(s2) + 1e-10)

            # Compute cross-correlation
            cross_corr = correlate(s1_norm, s2_norm, mode='full')

            # Normalize by length
            n = len(s1_norm)
            cross_corr = cross_corr / n

            # Find lags to test
            max_lag = min(self.lag_range, n // 4)
            lags = np.arange(-max_lag, max_lag + 1)

            # Get correlation at each lag
            # cross_corr index 0 corresponds to lag -(n-1)
            mid_point = len(cross_corr) // 2
            correlations = {}
            for lag in lags:
                idx = mid_point + lag
                if 0 <= idx < len(cross_corr):
                    correlations[lag] = cross_corr[idx]

            # Find lag with maximum absolute correlation
            if not correlations:
                return None

            best_lag = max(correlations, key=lambda l: abs(correlations[l]))
            best_corr = correlations[best_lag]

            # Determine direction
            if best_lag > 0:
                direction = "lag"  # s2 lags s1 (s2 changes after s1)
            elif best_lag < 0:
                direction = "lead"  # s2 leads s1 (s2 changes before s1)
            else:
                direction = "synchronous"

            return {
                "lag": abs(best_lag),
                "correlation": float(best_corr),
                "direction": direction,
            }

        except Exception as e:
            logger.debug(f"Lag correlation computation failed: {e}")
            return None

    def _apply_correction(self, correlations: List[Dict]) -> List[Dict]:
        """
        Apply multiple testing correction to p-values.

        Args:
            correlations: List of correlation results

        Returns:
            Updated list with corrected p-values
        """
        n_tests = len(correlations)
        if n_tests <= 1:
            return correlations

        p_values = [c["p_value"] for c in correlations]

        if self.correction_method.lower() == "bonferroni":
            corrected_p = [min(p * n_tests, 1.0) for p in p_values]
        elif self.correction_method.lower() == "bh":
            # Benjamini-Hochberg false discovery rate
            sorted_idx = np.argsort(p_values)
            corrected_p = np.zeros(n_tests)

            for i, idx in enumerate(sorted_idx):
                rank = i + 1
                corrected_p[idx] = min(p_values[idx] * n_tests / rank, 1.0)

            # Ensure monotonicity
            for i in range(len(sorted_idx) - 2, -1, -1):
                idx = sorted_idx[i]
                next_idx = sorted_idx[i + 1]
                corrected_p[idx] = max(corrected_p[idx], corrected_p[next_idx])
        else:
            logger.warning(f"Unknown correction method: {self.correction_method}")
            return correlations

        # Update results with corrected p-values and significance
        for i, corr in enumerate(correlations):
            corr["p_value_corrected"] = float(corrected_p[i])
            corr["significant"] = corrected_p[i] <= self.significance_threshold

        return correlations


def compute_cross_correlation_matrix(
    data: pd.DataFrame,
    time_column: str,
    max_lags: int = 12
) -> pd.DataFrame:
    """
    Compute cross-correlation matrix for all numeric metrics.

    Args:
        data: Dataset with time series
        time_column: Time column name
        max_lags: Maximum lag to consider

    Returns:
        DataFrame with correlation matrix for each lag
    """
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [col for col in numeric_cols if col != time_column]

    n_cols = len(numeric_cols)
    lag_matrix = {}

    for i, col1 in enumerate(numeric_cols):
        for j, col2 in enumerate(numeric_cols):
            if i < j:  # only upper triangle
                s1 = data[col1].values
                s2 = data[col2].values

                # Handle NaNs
                mask = ~(np.isnan(s1) | np.isnan(s2))
                s1_clean = s1[mask]
                s2_clean = s2[mask]

                if len(s1_clean) < 10:
                    continue

                # Cross-correlation at lag 0
                try:
                    r, p = stats.pearsonr(s1_clean, s2_clean)
                    lag_matrix[(col1, col2)] = {
                        "lag_0": float(r),
                        "p_value": float(p)
                    }
                except:
                    pass

    return pd.DataFrame.from_dict(lag_matrix, orient='index')
