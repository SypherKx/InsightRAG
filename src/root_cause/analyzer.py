"""
Root Cause Analyzer - Main Orchestrator

This module is the primary entry point for root cause analysis.
It coordinates segmentation, correlation, change point detection, and attribution.

Principles:
- NO LLM usage - pure statistical methods only
- Event-driven architecture compatible
- Production-ready with error handling and logging
- Configurable analysis parameters
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import time
import warnings

from .models import (
    RootCauseInsight,
    SegmentContribution,
    CorrelationResult,
    ChangePoint,
    AnalysisMethod,
)
from .segmenter import SegmentationAnalyzer, calculate_segment_contributions
from .correlator import CorrelationAnalyzer
from .attribution import AttributionAnalyzer

logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)


class RootCauseAnalyzer:
    """
    Main root cause analysis orchestrator.

    Coordinates multiple analysis methods to generate comprehensive root cause insights
    for anomalies. All methods are statistical - no LLM usage.

    Attributes:
        segmenter: Segmentation analysis component
        correlator: Correlation analysis component
        attribution: Impact attribution component
        min_confidence: Minimum confidence threshold for final output
        max_primary_drivers: Maximum number of primary drivers to return
        max_correlations: Maximum number of correlated metrics to return
    """

    def __init__(
        self,
        segmenter: Optional[SegmentationAnalyzer] = None,
        correlator: Optional[CorrelationAnalyzer] = None,
        attribution: Optional[AttributionAnalyzer] = None,
        min_confidence: float = 0.3,
        max_primary_drivers: int = 10,
        max_correlations: int = 10,
    ):
        """
        Initialize root cause analyzer.

        Args:
            segmenter: SegmentationAnalyzer instance (or None for default)
            correlator: CorrelationAnalyzer instance (or None for default)
            attribution: AttributionAnalyzer instance (or None for default)
            min_confidence: Minimum confidence to report results (0-1)
            max_primary_drivers: Maximum number of drivers in output
            max_correlations: Maximum number of correlations in output
        """
        self.segmenter = segmenter or SegmentationAnalyzer()
        self.correlator = correlator or CorrelationAnalyzer()
        self.attribution = attribution or AttributionAnalyzer()
        self.min_confidence = min_confidence
        self.max_primary_drivers = max_primary_drivers
        self.max_correlations = max_correlations

        # Analysis metadata
        self._analysis_count = 0
        self._total_processing_time = 0.0

    def analyze_anomaly(
        self,
        anomaly_id: str,
        anomaly_timestamp: datetime,
        metric: str,
        anomaly_value: float,
        expected_range: List[float],
        data: pd.DataFrame,
        dimensions: List[str],
        time_column: str = "date",
        dataset_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[RootCauseInsight]:
        """
        Perform comprehensive root cause analysis for a single anomaly.

        Args:
            anomaly_id: Unique identifier for the anomaly
            anomaly_timestamp: When anomaly occurred
            metric: The anomalous metric
            anomaly_value: Observed anomalous value
            expected_range: Expected range [min, max]
            data: Full dataset (including related metrics)
            dimensions: Categorical dimensions for segmentation
            time_column: Name of time column
            dataset_id: Dataset identifier (optional)
            metadata: Additional context

        Returns:
            RootCauseInsight object, or None if analysis fails
        """
        start_time = time.time()

        try:
            logger.info(f"Starting root cause analysis for anomaly {anomaly_id} on metric {metric}")

            # Validate inputs
            if data.empty:
                logger.error(f"Empty dataset for anomaly {anomaly_id}")
                return None

            if time_column not in data.columns:
                logger.error(f"Time column '{time_column}' not in dataset")
                return None

            if metric not in data.columns:
                logger.error(f"Metric '{metric}' not in dataset")
                return None

            # Calculate expected value from range
            expected_value = (expected_range[0] + expected_range[1]) / 2

            # Prepare time column
            data[time_column] = pd.to_datetime(data[time_column])

            # Get anomaly time (or closest available)
            anomaly_times = data[data[time_column] <= anomaly_timestamp][time_column]
            if len(anomaly_times) == 0:
                logger.error(f"No data before or at anomaly time {anomaly_timestamp}")
                return None

            actual_anomaly_time = anomaly_times.max()
            total_impact = anomaly_value - expected_value

            # Step 1: Segmentation Analysis
            logger.info("Running segmentation analysis...")
            segment_contributions = self.segmenter.analyze(
                anomaly_timestamp=actual_anomaly_time,
                metric=metric,
                data=data,
                dimensions=dimensions,
                time_column=time_column,
            )

            # Calculate contribution percentages
            segment_contributions = calculate_segment_contributions(
                segment_contributions, total_impact, metric
            )

            # Convert to SegmentContribution models
            primary_drivers = self._convert_segment_contributions(
                segment_contributions[:self.max_primary_drivers]
            )

            # Step 2: Correlation Analysis
            logger.info("Running correlation analysis...")
            correlations = self.correlator.analyze(
                anomaly_timestamp=actual_anomaly_time,
                primary_metric=metric,
                data=data,
                time_column=time_column,
                max_metrics=50,
            )

            # Convert to CorrelationResult models
            correlation_objects = self._convert_correlations(
                correlations[:self.max_correlations]
            )

            # Step 3: Change Point Detection
            logger.info("Running change point detection...")
            change_point = self._detect_change_point(
                data, metric, actual_anomaly_time, time_column
            )

            # Step 4: Attribution Analysis
            logger.info("Running attribution analysis...")
            attribution_result = self.attribution.attribute_impact(
                anomaly_timestamp=actual_anomaly_time,
                metric=metric,
                data=data,
                dimensions=dimensions[:3],  # Limit to top 3 dimensions
                time_column=time_column,
                expected_value=expected_value,
            )

            # Step 5: Generate Hypothesis
            hypothesis = self._generate_hypothesis(
                metric=metric,
                top_driver=primary_drivers[0] if primary_drivers else None,
                strongest_corr=correlation_objects[0] if correlation_objects else None,
                change_point=change_point,
                attribution=attribution_result,
            )

            # Step 6: Calculate Overall Confidence
            confidence = self._calculate_confidence(
                segment_contributions=segment_contributions,
                correlations=correlations,
                change_point=change_point,
                attribution=attribution_result,
            )

            # Step 7: Collect Supporting Evidence
            supporting_evidence = self._collect_supporting_evidence(
                segment_contributions=segment_contributions,
                correlations=correlations,
                change_point=change_point,
                attribution=attribution_result,
            )

            # Methods used
            methods_used = [AnalysisMethod.SEGMENTATION]
            if correlations:
                methods_used.append(AnalysisMethod.CORRELATION)
            if change_point:
                methods_used.append(AnalysisMethod.CHANGE_POINT)
            if attribution_result.get("attributions"):
                methods_used.append(AnalysisMethod.ATTRIBUTION)

            # Create RootCauseInsight model
            processing_time = time.time() - start_time

            insight = RootCauseInsight(
                anomaly_id=anomaly_id,
                anomaly_timestamp=anomaly_timestamp,
                metric=metric,
                anomaly_value=anomaly_value,
                expected_range=expected_range,
                primary_drivers=primary_drivers,
                correlations=correlation_objects,
                change_point=change_point,
                hypothesis=hypothesis,
                confidence=confidence,
                methods_used=methods_used,
                supporting_evidence=supporting_evidence,
                processing_time_sec=processing_time,
                metadata={
                    "dataset_id": dataset_id,
                    "total_impact": float(total_impact),
                    "num_data_points": len(data),
                    "num_segments_analyzed": len(segment_contributions),
                    **(metadata or {}),
                },
            )

            self._update_metrics(processing_time)
            logger.info(f"Completed root cause analysis for {anomaly_id} in {processing_time:.2f}s with confidence {confidence:.3f}")

            if confidence >= self.min_confidence:
                return insight
            else:
                logger.warning(f"Low confidence ({confidence:.3f}) for anomaly {anomaly_id}")
                return insight  # Return even if low confidence, caller can decide

        except Exception as e:
            logger.exception(f"Root cause analysis failed for anomaly {anomaly_id}: {e}")
            return None

    def _convert_segment_contributions(
        self, contributions: List[Dict]
    ) -> List[SegmentContribution]:
        """Convert dict contributions to SegmentContribution models."""
        result = []
        for c in contributions:
            try:
                segment = SegmentContribution(
                    segment=c["segment"],
                    contribution=c.get("contribution", 0.0),
                    baseline_ratio=c["baseline_ratio"],
                    segment_value=c.get("segment_value"),
                    baseline_value=c.get("baseline_value"),
                    statistical_significance=c.get("statistical_significance"),
                    segment_size=c.get("segment_size"),
                )
                result.append(segment)
            except Exception as e:
                logger.debug(f"Failed to convert segment contribution: {e}")
                continue
        return result

    def _convert_correlations(self, correlations: List[Dict]) -> List[CorrelationResult]:
        """Convert dict correlations to CorrelationResult models."""
        result = []
        for c in correlations:
            try:
                corr = CorrelationResult(
                    metric=c["metric"],
                    coefficient=c["coefficient"],
                    p_value=c.get("p_value"),
                    lag_hours=c.get("lag_hours"),
                    lag_direction=c.get("lag_direction"),
                    sample_size=c.get("sample_size"),
                    method=c.get("method", "pearson"),
                )
                result.append(corr)
            except Exception as e:
                logger.debug(f"Failed to convert correlation: {e}")
                continue
        return result

    def _detect_change_point(
        self,
        data: pd.DataFrame,
        metric: str,
        anomaly_time: pd.Timestamp,
        time_column: str,
        window: int = 60
    ) -> Optional[ChangePoint]:
        """
        Detect change point in metric leading up to anomaly.

        Uses CUSUM or Pettitt test to identify when behavior changed.

        Args:
            data: Full dataset
            metric: Metric to analyze
            anomaly_time: Anomaly timestamp
            time_column: Time column name
            window: Window size for analysis

        Returns:
            ChangePoint model if detected, else None
        """
        try:
            # Extract series around anomaly
            series_data = data.sort_values(time_column)
            anomaly_idx = series_data[series_data[time_column] <= anomaly_time].index.max()

            start_idx = max(0, anomaly_idx - window)
            window_data = series_data.loc[start_idx:anomaly_idx]

            if len(window_data) < 10:
                return None

            values = window_data[metric].values

            # Remove NaNs
            values = values[~np.isnan(values)]

            if len(values) < 10:
                return None

            # Use Pettitt test for change point
            from scipy.stats import rankdata

            # Calculate ranks
            ranks = rankdata(values)

            # Compute U statistic
            n = len(values)
            u_stats = []

            for k in range(1, n):
                rk = np.sum(ranks[:k])
                uk = rk - k * (n + 1) / 2
                u_stats.append(abs(uk))

            if not u_stats:
                return None

            max_u = max(u_stats)
            max_k = np.argmax(u_stats) + 1  # +1 because range starts at 1

            # Calculate p-value
            # Approximate using normal distribution
            expected_u = n * (n - 1) / 4
            var_u = n * (n - 1) * (2 * n + 5) / 72
            z_score = (max_u - expected_u) / np.sqrt(var_u)
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

            # If change point is significant and located before anomaly
            if p_value < 0.05 and max_k < len(values) * 0.8:
                change_time = window_data.iloc[max_k][time_column]

                # Calculate before/after stats
                before = values[:max_k]
                after = values[max_k:]

                change_point = ChangePoint(
                    detected_at=pd.to_datetime(change_time).to_pydatetime(),
                    confidence=1.0 - p_value,
                    method="pettitt_test",
                    before_mean=float(np.mean(before)),
                    after_mean=float(np.mean(after)),
                    before_std=float(np.std(before)),
                    after_std=float(np.std(after)),
                    change_magnitude=float((np.mean(after) - np.mean(before)) / (np.std(values) + 1e-10)),
                    statistical_test="pettitt",
                    test_statistic=float(max_u),
                    p_value=float(p_value),
                )

                return change_point

            return None

        except Exception as e:
            logger.debug(f"Change point detection failed: {e}")
            return None

    def _generate_hypothesis(
        self,
        metric: str,
        top_driver: Optional[SegmentContribution],
        strongest_corr: Optional[CorrelationResult],
        change_point: Optional[ChangePoint],
        attribution: Dict[str, Any],
    ) -> str:
        """
        Generate natural language hypothesis summarizing findings.

        Pure template-based - NO LLM.

        Args:
            metric: The anomalous metric
            top_driver: Top contributing segment
            strongest_corr: Strongest correlation
            change_point: Detected change point
            attribution: Attribution results

        Returns:
            Hypothesis string
        """
        parts = []

        # Start with metric and anomaly type
        metric_name = metric.replace("_", " ").title()

        if top_driver:
            driver_segment = top_driver.segment
            contrib_pct = top_driver.contribution
            baseline_ratio = top_driver.baseline_ratio

            if baseline_ratio < 0.7:  # Underperforming
                parts.append(f"{metric_name} drop primarily driven by {driver_segment} ({contrib_pct:.1f}% contribution).")
            elif baseline_ratio > 1.3:  # Overperforming
                parts.append(f"{metric_name} spike primarily driven by {driver_segment} ({contrib_pct:.1f}% contribution).")
            else:
                parts.append(f"Anomaly in {metric_name} concentrated in {driver_segment} ({contrib_pct:.1f}% contribution).")
        else:
            parts.append(f"Anomaly detected in {metric_name}.")

        # Add strongest correlation if significant
        if strongest_corr and strongest_corr.p_value and strongest_corr.p_value < 0.05:
            corr_metric = strongest_corr.metric.replace("_", " ").title()
            lag_info = f" with {abs(strongest_corr.lag_hours or 0):.0f}h lag" if strongest_corr.lag_hours else ""
            parts.append(f"Correlated with {corr_metric} (r={abs(strongest_corr.coefficient):.2f}){lag_info}.")

        # Add change point info
        if change_point and change_point.confidence > 0.7:
            parts.append(f"Behavior change detected {(change_point.detected_at - pd.Timestamp.now()).days} days ago.")

        # Add attribution summary
        if attribution.get("attributions"):
            top_attrib = attribution["attributions"][0]
            dim = top_attrib.get("dimension", "").replace("_", " ").title()
            seg = top_attrib.get("segment", "")
            pct = top_attrib.get("contribution_pct", 0)
            parts.append(f"{dim} ({seg}) accounts for {pct:.1f}% of total impact.")

        hypothesis = " ".join(parts)

        return hypothesis

    def _calculate_confidence(
        self,
        segment_contributions: List[Dict],
        correlations: List[Dict],
        change_point: Optional[ChangePoint],
        attribution: Dict[str, Any],
    ) -> float:
        """
        Calculate overall confidence in the analysis.

        Factors considered:
        - Statistical significance of top segments
        - Strength of correlations
        - Change point confidence
        - Attribution consistency
        - Number of converging lines of evidence

        Args:
            segment_contributions: Segmentation results
            correlations: Correlation results
            change_point: Change point detection
            attribution: Attribution results

        Returns:
            Confidence score (0-1)
        """
        scores = []

        # 1. Top segment significance
        if segment_contributions:
            top_seg = segment_contributions[0]
            p_value = top_seg.get("statistical_significance")
            if p_value is not None and p_value < 0.05:
                scores.append(1.0)
            else:
                scores.append(0.3)
        else:
            scores.append(0.1)

        # 2. Correlation strength (if any)
        if correlations:
            strongest = max(cors["coefficient"] for cors in correlations)
            corr_score = abs(strongest)
            scores.append(corr_score)
        else:
            scores.append(0.5)  # Neutral, not necessarily bad

        # 3. Change point detection confidence
        if change_point:
            cp_confidence = change_point.confidence
            if cp_confidence > 0.8:
                scores.append(1.0)
            elif cp_confidence > 0.6:
                scores.append(0.7)
            else:
                scores.append(0.4)
        else:
            scores.append(0.5)  # Not finding a change point is normal

        # 4. Attribution quality
        if attribution.get("attributions"):
            top_attr = attribution["attributions"][0]
            contrib_pct = abs(top_attr.get("contribution_pct", 0))
            if contrib_pct > 40:
                scores.append(1.0)
            elif contrib_pct > 20:
                scores.append(0.7)
            else:
                scores.append(0.4)
        else:
            scores.append(0.3)

        # 5. Consistency across methods
        num_methods = sum([
            len(segment_contributions) > 0,
            len(correlations) > 0,
            change_point is not None,
            len(attribution.get("attributions", [])) > 0,
        ])
        consistency_score = num_methods / 4  # Normalize to 0-1
        scores.append(consistency_score)

        # Weighted average
        weights = [0.25, 0.20, 0.15, 0.20, 0.20]  # Emphasize segmentation and attribution
        confidence = sum(s * w for s, w in zip(scores, weights))

        return min(max(confidence, 0.0), 1.0)  # Clamp to [0, 1]

    def _collect_supporting_evidence(
        self,
        segment_contributions: List[Dict],
        correlations: List[Dict],
        change_point: Optional[ChangePoint],
        attribution: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Collect supporting evidence for conclusion.

        Args:
            segment_contributions: Segmentation results
            correlations: Correlation results
            change_point: Change point detection
            attribution: Attribution results

        Returns:
            Dictionary of evidence
        """
        evidence = {
            "total_segments_analyzed": len(segment_contributions),
            "num_significant_segments": sum(
                1 for c in segment_contributions
                if c.get("statistical_significance", 1.0) < 0.05
            ),
            "avg_segment_contribution": np.mean([c.get("contribution", 0) for c in segment_contributions]) if segment_contributions else 0,
        }

        if correlations:
            evidence["correlation_analysis"] = {
                "num_correlations_found": len(correlations),
                "strongest_correlation": max(abs(c["coefficient"]) for c in correlations),
                "significant_correlations": sum(1 for c in correlations if c.get("significant", False)),
            }

        if change_point:
            evidence["change_point"] = {
                "detected": True,
                "confidence": change_point.confidence,
                "change_magnitude": change_point.change_magnitude,
                "days_before_anomaly": (change_point.detected_at - anomaly_timestamp).days if hasattr(change_point.detected_at, 'days') else 0,
            }

        if attribution.get("attributions"):
            evidence["attribution"] = {
                "total_contributing_factors": len(attribution["attributions"]),
                "top_contributor": attribution["attributions"][0]["dimension"] if attribution["attributions"] else None,
            }

        return evidence

    def _update_metrics(self, processing_time: float):
        """Update internal performance metrics."""
        self._analysis_count += 1
        self._total_processing_time += processing_time

    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        if self._analysis_count == 0:
            return {
                "total_analyses": 0,
                "avg_processing_time": 0.0,
            }

        return {
            "total_analyses": self._analysis_count,
            "avg_processing_time": self._total_processing_time / self._analysis_count,
        }

    def analyze_batch(
        self,
        anomalies: List[Dict[str, Any]],
        data: pd.DataFrame,
        dimensions: List[str],
        time_column: str = "date",
    ) -> List[RootCauseInsight]:
        """
        Analyze multiple anomalies in batch.

        Args:
            anomalies: List of anomaly dictionaries with keys:
                - anomaly_id
                - anomaly_timestamp
                - metric
                - anomaly_value
                - expected_range
            data: Full dataset
            dimensions: Categorical dimensions
            time_column: Time column name

        Returns:
            List of RootCauseInsight objects
        """
        insights = []

        for anomaly in anomalies:
            try:
                insight = self.analyze_anomaly(
                    anomaly_id=anomaly["anomaly_id"],
                    anomaly_timestamp=anomaly["anomaly_timestamp"],
                    metric=anomaly["metric"],
                    anomaly_value=anomaly["anomaly_value"],
                    expected_range=anomaly["expected_range"],
                    data=data,
                    dimensions=dimensions,
                    time_column=time_column,
                    dataset_id=anomaly.get("dataset_id"),
                    metadata=anomaly.get("metadata"),
                )
                if insight:
                    insights.append(insight)
            except Exception as e:
                logger.error(f"Failed to analyze anomaly {anomaly.get('anomaly_id', 'unknown')}: {e}")
                continue

        logger.info(f"Batch analysis complete: {len(insights)}/{len(anomalies)} successful")
        return insights

    def export_results(
        self,
        insights: List[RootCauseInsight],
        output_format: str = "json"
    ) -> Any:
        """
        Export analysis results in specified format.

        Args:
            insights: List of RootCauseInsight objects
            output_format: Format ('json', 'csv', 'dict')

        Returns:
            Formatted output
        """
        if output_format == "dict":
            return [insight.dict() for insight in insights]

        elif output_format == "json":
            import json
            return json.dumps([insight.dict() for insight in insights], indent=2, default=str)

        elif output_format == "csv":
            # Flatten to CSV format
            records = []
            for insight in insights:
                base = {
                    "anomaly_id": insight.anomaly_id,
                    "anomaly_timestamp": insight.anomaly_timestamp,
                    "metric": insight.metric,
                    "anomaly_value": insight.anomaly_value,
                    "expected_min": insight.expected_range[0],
                    "expected_max": insight.expected_range[1],
                    "overall_confidence": insight.confidence,
                    "hypothesis": insight.hypothesis,
                    "num_primary_drivers": len(insight.primary_drivers),
                    "num_correlations": len(insight.correlations),
                    "has_change_point": insight.change_point is not None,
                    "processing_time_sec": insight.processing_time_sec,
                    "methods_used": "|".join([m.value for m in insight.methods_used]),
                }

                # Add top driver if exists
                if insight.primary_drivers:
                    base["top_driver_segment"] = insight.primary_drivers[0].segment
                    base["top_driver_contribution"] = insight.primary_drivers[0].contribution
                    base["top_driver_baseline_ratio"] = insight.primary_drivers[0].baseline_ratio
                else:
                    base["top_driver_segment"] = None

                if insight.correlations:
                    base["top_correlation_metric"] = insight.correlations[0].metric
                    base["top_correlation_coeff"] = insight.correlations[0].coefficient

                records.append(base)

            return pd.DataFrame(records)

        else:
            raise ValueError(f"Unsupported output format: {output_format}")
