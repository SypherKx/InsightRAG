"""
Impact Attribution Module

Quantifies the contribution of different factors to an anomaly.

Methodology:
1. Decompose overall anomaly impact by segments
2. Calculate variance contributions (ANOVA-style)
3. Normalize contributions to sum to 100%
4. Apply Shapley-like value attribution for interactions
5. Calculate confidence intervals for contributions

Statistical approach:
- Sum of contributions method for additive effects
- Variance decomposition for non-additive effects
- Bootstrap for confidence intervals
- Interaction effect detection
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class AttributionAnalyzer:
    """
    Performs impact attribution analysis.

    Attributes:
        method: Attribution method ('variance', 'additive', 'interaction')
        bootstrap_samples: Number of bootstrap samples for CI
        confidence_level: Confidence level for intervals (0-1)
        min_contribution: Minimum contribution % to report
    """

    def __init__(
        self,
        method: str = "variance",
        bootstrap_samples: int = 1000,
        confidence_level: float = 0.95,
        min_contribution: float = 1.0,
    ):
        """
        Initialize attribution analyzer.

        Args:
            method: Attribution method ('variance', 'additive', 'interaction')
            bootstrap_samples: Number of bootstrap iterations
            confidence_level: Confidence level for intervals
            min_contribution: Minimum % contribution to include
        """
        self.method = method
        self.bootstrap_samples = bootstrap_samples
        self.confidence_level = confidence_level
        self.min_contribution = min_contribution

        # Critical value for confidence intervals
        self.z_critical = stats.norm.ppf((1 + confidence_level) / 2)

    def attribute_impact(
        self,
        anomaly_timestamp: pd.Timestamp,
        metric: str,
        data: pd.DataFrame,
        dimensions: List[str],
        time_column: str = "date",
        expected_value: Optional[float] = None,
    ) -> Dict:
        """
        Calculate impact attribution across dimensions.

        Args:
            anomaly_timestamp: Time of anomaly
            metric: Metric to analyze
            data: Full dataset
            dimensions: List of dimensions to attribute across
            time_column: Time column name
            expected_value: Expected value at anomaly time (if known)

        Returns:
            Dictionary with attribution results
        """
        if not dimensions:
            return {"attributions": [], "total_impact": 0}

        data[time_column] = pd.to_datetime(data[time_column])

        anomaly_data = data[data[time_column] <= anomaly_timestamp].sort_values(time_column).tail(1)
        if anomaly_data.empty:
            logger.warning("No data at anomaly timestamp")
            return {"attributions": [], "total_impact": 0}

        anomaly_value = anomaly_data[metric].iloc[0]

        if expected_value is None:
            expected_value = self._calculate_expected_value(data, anomaly_timestamp, metric, time_column)

        baseline_period = self._get_baseline_period(data, anomaly_timestamp, time_column)
        total_impact = anomaly_value - expected_value if expected_value is not None else 0

        # Calculate dimensional contributions
        attributions = []
        for dimension in dimensions:
            if dimension not in data.columns:
                continue

            dim_contributions = self._attribute_by_dimension(
                anomaly_data, baseline_period, metric, dimension, total_impact
            )
            attributions.extend(dim_contributions)

        # Multi-dimensional interaction effects
        if len(dimensions) > 1 and self.method == "interaction":
            interactions = self._calculate_interaction_effects(
                anomaly_data, baseline_period, metric, dimensions, total_impact
            )
            attributions.extend(interactions)

        # Filter and rank contributions
        attributions = [a for a in attributions if abs(a.get("contribution_pct", 0)) >= self.min_contribution]
        attributions.sort(key=lambda x: abs(x["contribution_pct"]), reverse=True)

        total_abs_contrib = sum(abs(a["contribution_pct"]) for a in attributions)
        if total_abs_contrib > 0:
            for a in attributions:
                a["contribution_pct"] = (a["contribution_pct"] / total_abs_contrib) * 100

        # Optional bootstrap confidence interval estimation
        if self.bootstrap_samples > 0 and len(data) > 20:
            ci_results = self._bootstrap_confidence_intervals(
                data, anomaly_timestamp, metric, dimensions, time_column, attributions
            )
            for a in attributions:
                key = f"{a['dimension']}_{a.get('segment', 'all')}"
                if key in ci_results:
                    a["confidence_interval"] = ci_results[key]

        return {
            "attributions": attributions,
            "total_impact": float(total_impact),
            "anomaly_value": float(anomaly_value),
            "expected_value": float(expected_value) if expected_value is not None else None,
            "attribution_method": self.method,
        }

    def _calculate_expected_value(
        self, data: pd.DataFrame, anomaly_timestamp: pd.Timestamp, metric: str, time_column: str
    ) -> float:
        """
        Calculate expected value based on recent history.

        Args:
            data: Full dataset
            anomaly_timestamp: Anomaly time
            metric: Metric name
            time_column: Time column

        Returns:
            Expected value (moving average of recent periods)
        """
        # Get data before anomaly
        historical = data[data[time_column] < anomaly_timestamp].sort_values(time_column)

        if len(historical) < 3:
            return np.nan

        # Use last 7 periods (or all if fewer)
        window = min(7, len(historical) // 2)
        recent = historical.tail(window)

        return recent[metric].mean()

    def _get_baseline_period(
        self, data: pd.DataFrame, anomaly_timestamp: pd.Timestamp, time_column: str, window: int = 7
    ) -> pd.DataFrame:
        """
        Get baseline period data.

        Args:
            data: Full dataset
            anomaly_timestamp: Anomaly time
            time_column: Time column
            window: Number of periods for baseline

        Returns:
            Baseline data
        """
        historical = data[data[time_column] < anomaly_timestamp].sort_values(time_column)
        return historical.tail(window)

    def _attribute_by_dimension(
        self,
        anomaly_data: pd.DataFrame,
        baseline_data: pd.DataFrame,
        metric: str,
        dimension: str,
        total_impact: float,
    ) -> List[Dict]:
        """
        Attribute impact by a single dimension.

        Args:
            anomaly_data: Data at anomaly time
            baseline_data: Baseline period data
            metric: Metric to analyze
            dimension: Categorical dimension
            total_impact: Total impact to distribute

        Returns:
            List of attribution dictionaries
        """
        contributions = []

        # Get unique segments
        segments = anomaly_data[dimension].dropna().unique()

        for segment in segments:
            # Get segment values
            anomaly_segment = anomaly_data[anomaly_data[dimension] == segment]
            baseline_segment = baseline_data[baseline_data[dimension] == segment]

            if len(baseline_segment) == 0:
                # No baseline data for this segment
                baseline_mean = 0
            else:
                baseline_mean = baseline_segment[metric].mean()

            segment_value = anomaly_segment[metric].sum() if len(anomaly_segment) > 0 else 0

            # Calculate segment contribution
            if len(baseline_segment) > 0:
                segment_impact = segment_value - (baseline_mean * (len(anomaly_segment) if len(anomaly_segment) > 0 else 1))
            else:
                # If no baseline, full segment value is impact (conservative)
                segment_impact = segment_value if segment_value > 0 else 0

            # Calculate contribution percentage (relative to total impact)
            if total_impact != 0:
                contribution_pct = (segment_impact / total_impact) * 100
            else:
                contribution_pct = 0

            contribution = {
                "dimension": dimension,
                "segment": str(segment),
                "segment_value": float(segment_value),
                "baseline_value": float(baseline_mean) if not pd.isna(baseline_mean) else None,
                "segment_impact": float(segment_impact),
                "contribution_pct": float(contribution_pct),
                "segment_size": len(baseline_segment),
            }

            contributions.append(contribution)

        return contributions

    def _calculate_interaction_effects(
        self,
        anomaly_data: pd.DataFrame,
        baseline_data: pd.DataFrame,
        metric: str,
        dimensions: List[str],
        total_impact: float,
    ) -> List[Dict]:
        """
        Calculate interaction effects between dimensions.

        Args:
            anomaly_data: Anomaly period data
            baseline_data: Baseline period data
            metric: Metric being analyzed
            dimensions: List of dimensions
            total_impact: Total impact

        Returns:
            List of interaction effect contributions
        """
        if len(dimensions) < 2:
            return []

        interactions = []

        # For each pair of dimensions, check interaction
        for i in range(len(dimensions)):
            for j in range(i + 1, len(dimensions)):
                dim1, dim2 = dimensions[i], dimensions[j]

                # Get segment pairs at anomaly time
                pairs = anomaly_data.groupby([dim1, dim2])[metric].sum()

                for (seg1, seg2), value in pairs.items():
                    # Simultaneous baseline (product of individual baselines)
                    baseline1 = baseline_data[baseline_data[dim1] == seg1][metric].mean()
                    baseline2 = baseline_data[baseline_data[dim2] == seg2][metric].mean()

                    if not pd.isna(baseline1) and not pd.isna(baseline2):
                        # Expected baseline for intersection (approximate)
                        expected_baseline = (baseline1 + baseline2) / 2

                        interaction_impact = value - expected_baseline

                        # If interaction is significant relative to total
                        if abs(interaction_impact) > abs(total_impact) * (self.min_contribution / 100):
                            interactions.append({
                                "dimension": f"{dim1} x {dim2}",
                                "segment": f"{seg1} + {seg2}",
                                "segment_value": float(value),
                                "baseline_value": float(expected_baseline),
                                "segment_impact": float(interaction_impact),
                                "contribution_pct": float((interaction_impact / total_impact * 100) if total_impact != 0 else 0),
                                "interaction_type": "synergistic" if interaction_impact > 0 else "diminishing",
                            })

        return interactions

    def _bootstrap_confidence_intervals(
        self,
        data: pd.DataFrame,
        anomaly_timestamp: pd.Timestamp,
        metric: str,
        dimensions: List[str],
        time_column: str,
        attributions: List[Dict],
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate bootstrap confidence intervals for attributions.

        Args:
            data: Full dataset
            anomaly_timestamp: Anomaly time
            metric: Metric name
            dimensions: Dimensions used
            time_column: Time column
            attributions: Point estimate attributions

        Returns:
            Dictionary of confidence intervals
        """
        ci_results = {}
        n = len(data)

        # For each attribution, bootstrap CI
        for attr in attributions:
            key = f"{attr['dimension']}_{attr.get('segment', 'all')}"
            attr_contributions = []

            for _ in range(self.bootstrap_samples):
                # Sample with replacement
                sample = data.sample(n=n, replace=True)

                # Re-run attribution on sample (simplified - just recalculate single factor contributions)
                try:
                    # Get anomaly in sample
                    anomaly_sample = sample[sample[time_column] <= anomaly_timestamp].sort_values(time_column).tail(1)
                    if anomaly_sample.empty:
                        continue

                    baseline_sample = sample[sample[time_column] < anomaly_timestamp].tail(7)
                    expected = baseline_sample[metric].mean()

                    dim = attr["dimension"]
                    seg = attr["segment"]

                    if dim in sample.columns:
                        seg_baseline = baseline_sample[baseline_sample[dim] == seg][metric].mean()
                        seg_value = anomaly_sample[anomaly_sample[dim] == seg][metric].sum()

                        if not pd.isna(seg_baseline):
                            seg_impact = seg_value - seg_baseline
                            original_impact = attr["segment_impact"]

                            if original_impact != 0:
                                ratio = seg_impact / original_impact
                                attr_contributions.append(ratio)
                except:
                    continue

            if len(attr_contributions) > 0:
                # Calculate percentile CI
                ci_lower = np.percentile(attr_contributions, (1 - self.confidence_level) / 2 * 100)
                ci_upper = np.percentile(attr_contributions, (1 + self.confidence_level) / 2 * 100)
                ci_results[key] = (float(ci_lower), float(ci_upper))

        return ci_results


def calculate_shapley_values(
    data: pd.DataFrame,
    metric: str,
    anomaly_timestamp: pd.Timestamp,
    dimensions: List[str],
    time_column: str = "date",
    n_permutations: int = 1000
) -> Dict[str, float]:
    """
    Calculate Shapley values for fair attribution across dimensions.

    Uses coalition-based approach to account for interactions.

    Args:
        data: Dataset
        metric: Metric being analyzed
        anomaly_timestamp: Time of anomaly
        dimensions: List of all dimensions
        time_column: Time column
        n_permutations: Number of permutations for estimation

    Returns:
        Dictionary mapping dimension names to Shapley values (contribution percentages)
    """
    import itertools
    import random

    # Get baseline values
    baseline = data[data[time_column] < anomaly_timestamp][metric].mean()
    anomaly_data = data[data[time_column] <= anomaly_timestamp].sort_values(time_column).tail(1)
    anomaly_value = anomaly_data[metric].iloc[0]

    total_impact = anomaly_value - baseline

    shapley_values = {dim: 0.0 for dim in dimensions}
    shapley_counts = {dim: 0 for dim in dimensions}

    # Generate all permutations
    for _ in range(n_permutations):
        perm = dimensions.copy()
        random.shuffle(perm)

        # Marginal contributions for this permutation
        prev_contrib = 0

        for i, dim in enumerate(perm):
            # Coalition of first i dimensions
            coalition = perm[:i]

            # Value with coalition
            coalition_value = _predict_value(data, anomaly_timestamp, metric, coalition, time_column)

            # Value with coalition + this dimension
            coalition_with_dim = _predict_value(data, anomaly_timestamp, metric, coalition + [dim], time_column)

            marginal = coalition_with_dim - coalition_value
            shapley_values[dim] += marginal
            shapley_counts[dim] += 1

    # Average marginal contributions
    for dim in shapley_values:
        if shapley_counts[dim] > 0:
            shapley_values[dim] /= shapley_counts[dim]

    # Normalize to sum to total_impact
    sum_values = sum(shapley_values.values())
    if sum_values != 0:
        factor = total_impact / sum_values
        for dim in shapley_values:
            shapley_values[dim] *= factor

    # Convert to percentages
    if total_impact != 0:
        for dim in shapley_values:
            shapley_values[dim] = (shapley_values[dim] / total_impact) * 100

    return shapley_values


def _predict_value(
    data: pd.DataFrame,
    anomaly_timestamp: pd.Timestamp,
    metric: str,
    dimensions: List[str],
    time_column: str
) -> float:
    """
    Predict value given a subset of dimensions at anomaly time.

    Approximates value by interpolating from baseline dimensions.

    Args:
        data: Dataset
        anomaly_timestamp: Anomaly time
        metric: Metric name
        dimensions: Subset of dimensions to use
        time_column: Time column

    Returns:
        Predicted value
    """
    if not dimensions:
        # No dimensions: use overall baseline
        baseline = data[data[time_column] < anomaly_timestamp][metric].mean()
        return baseline

    # Get anomaly data with grouping by available dimensions
    anomaly_data = data[data[time_column] <= anomaly_timestamp].sort_values(time_column).tail(1)

    # Group by specified dimensions and sum
    if dimensions:
        grouped = anomaly_data.groupby(dimensions)[metric].sum().reset_index()
    else:
        return anomaly_data[metric].sum()

    # For baseline, use historical average per segment
    baseline = data[data[time_column] < anomaly_timestamp]
    baseline_grouped = baseline.groupby(dimensions)[metric].mean().reset_index()

    # Merge to get predicted per segment
    merged = grouped.merge(baseline_grouped, on=dimensions, how='left', suffixes=('_actual', '_baseline'))

    # Fill missing with overall average
    overall_baseline = baseline[metric].mean()
    merged['metric_baseline'] = merged['metric_baseline'].fillna(overall_baseline)

    # Sum predictions
    predicted = merged['metric_baseline'].sum()

    return predicted
