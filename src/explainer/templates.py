"""
Template-based explanation renderer.

Produces structured, readable explanations WITHOUT any LLM.
This is the fallback when LLM is unavailable, and also used
to validate LLM responses against expected structure.
"""

import logging
from typing import List
from datetime import datetime

from .models import ExplanationRequest, ExplanationResponse

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """
    Generates explanations using pure template logic.

    No LLM calls — deterministic, fast, always available.
    """

    def render(self, request: ExplanationRequest) -> ExplanationResponse:
        """
        Render a complete explanation from structured data.

        Args:
            request: ExplanationRequest with anomaly + root cause data

        Returns:
            ExplanationResponse with template-based explanation
        """
        anomaly = request.anomaly
        root_cause = request.root_cause

        # Build explanation sections
        what_happened = self._render_what_happened(anomaly)
        where_it_happened = self._render_where(anomaly)
        why_it_happened = self._render_why(root_cause)
        recommendations = self._render_recommendations(
            anomaly, root_cause
        ) if request.include_recommendations else []

        # Compose full explanation
        sections = [what_happened, where_it_happened, why_it_happened]
        explanation_text = "\n\n".join(s for s in sections if s)

        if recommendations:
            rec_text = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(recommendations))
            explanation_text += f"\n\nRecommended Actions:\n{rec_text}"

        # One-line summary
        summary = self._render_summary(anomaly, root_cause)

        # Evidence citations
        evidence = self._collect_evidence(anomaly, root_cause)

        return ExplanationResponse(
            anomaly_id=anomaly.anomaly_id,
            explanation_text=explanation_text,
            summary=summary,
            recommendations=recommendations,
            confidence=root_cause.confidence,
            evidence_citations=evidence,
            generated_at=datetime.utcnow(),
            llm_model=None,
            used_fallback=True,
        )

    def _render_what_happened(self, anomaly) -> str:
        """Describe WHAT happened."""
        metric_name = anomaly.metric.replace("_", " ").title()
        severity_label = self._severity_label(anomaly.severity)

        expected_mid = (anomaly.expected_min + anomaly.expected_max) / 2
        if expected_mid != 0:
            pct_change = ((anomaly.value - expected_mid) / abs(expected_mid)) * 100
        else:
            pct_change = 0

        direction = "increased" if anomaly.value > expected_mid else "decreased"
        type_label = anomaly.anomaly_type.replace("_", " ")

        ts = anomaly.timestamp.strftime("%B %d, %Y at %H:%M")

        text = (
            f"**What Happened:** On {ts}, {metric_name} {direction} "
            f"to {anomaly.value:,.2f}, which is a {severity_label}-severity {type_label}. "
            f"This represents a {abs(pct_change):.1f}% {direction.rstrip('d')} from the "
            f"expected range of {anomaly.expected_min:,.2f} – {anomaly.expected_max:,.2f}."
        )

        return text

    def _render_where(self, anomaly) -> str:
        """Describe WHERE it happened (dimensions)."""
        if not anomaly.dimensions:
            return ""

        dim_parts = [
            f"{k.replace('_', ' ').title()}: {v}"
            for k, v in anomaly.dimensions.items()
        ]
        dims_str = ", ".join(dim_parts)

        return f"**Where:** This anomaly was concentrated in {dims_str}."

    def _render_why(self, root_cause) -> str:
        """Describe WHY it happened."""
        parts = []

        if root_cause.hypothesis:
            parts.append(f"**Why:** {root_cause.hypothesis}")

        # Add driver details
        if root_cause.primary_drivers:
            driver_strs = []
            for d in root_cause.primary_drivers[:3]:
                segment = d.get("segment", d.get("dimension", "Unknown"))
                contrib = d.get("contribution", d.get("impact", 0))
                driver_strs.append(f"{segment} ({contrib:.1f}% contribution)")
            parts.append(
                f"**Primary Drivers:** {'; '.join(driver_strs)}."
            )

        # Add correlation info
        if root_cause.correlations:
            corr_strs = []
            for c in root_cause.correlations[:3]:
                metric = c.get("metric", "Unknown")
                coeff = c.get("coefficient", c.get("correlation", 0))
                corr_strs.append(f"{metric.replace('_', ' ').title()} (r={coeff:.2f})")
            parts.append(
                f"**Correlated Metrics:** {'; '.join(corr_strs)}."
            )

        # Add change point
        if root_cause.change_point:
            cp = root_cause.change_point
            cp_time = cp.get("detected_at", "")
            cp_conf = cp.get("confidence", 0)
            if cp_time:
                parts.append(
                    f"**Change Point:** A behavioral shift was detected at {cp_time} "
                    f"(confidence: {cp_conf:.0%})."
                )

        if not parts:
            parts.append(
                "**Why:** Insufficient evidence to determine a definitive root cause. "
                "Consider reviewing recent operational changes or external factors."
            )

        return "\n".join(parts)

    def _render_recommendations(
        self, anomaly, root_cause
    ) -> List[str]:
        """Generate actionable recommendations."""
        recs = []

        # Based on anomaly type
        if anomaly.anomaly_type == "drop":
            recs.append(
                f"Investigate the cause of the {anomaly.metric.replace('_', ' ')} "
                f"decline in affected segments."
            )
        elif anomaly.anomaly_type == "spike":
            recs.append(
                f"Verify whether the {anomaly.metric.replace('_', ' ')} spike is "
                f"genuine or caused by data quality issues."
            )

        # Based on drivers
        if root_cause.primary_drivers:
            top = root_cause.primary_drivers[0]
            segment = top.get("segment", top.get("dimension", ""))
            if segment:
                recs.append(f"Focus investigation on the {segment} segment.")

        # Based on correlations
        if root_cause.correlations:
            top_corr = root_cause.correlations[0]
            corr_metric = top_corr.get("metric", "")
            if corr_metric:
                recs.append(
                    f"Monitor {corr_metric.replace('_', ' ')} as it shows "
                    f"strong correlation with this anomaly."
                )

        # General
        if anomaly.severity > 0.7:
            recs.append("Set up alerts for this metric to detect recurrence early.")

        recs.append("Review this finding with domain experts for business context.")

        return recs

    def _render_summary(self, anomaly, root_cause) -> str:
        """One-line summary."""
        metric_name = anomaly.metric.replace("_", " ").title()
        severity_label = self._severity_label(anomaly.severity)

        if root_cause.primary_drivers:
            top = root_cause.primary_drivers[0]
            segment = top.get("segment", top.get("dimension", ""))
            return (
                f"{severity_label}-severity {anomaly.anomaly_type} in {metric_name}, "
                f"primarily driven by {segment}."
            )

        return f"{severity_label}-severity {anomaly.anomaly_type} detected in {metric_name}."

    def _severity_label(self, severity: float) -> str:
        if severity >= 0.7:
            return "Critical"
        elif severity >= 0.4:
            return "High"
        elif severity >= 0.2:
            return "Medium"
        return "Low"

    def _collect_evidence(self, anomaly, root_cause) -> List[str]:
        """Collect evidence citations."""
        evidence = []

        evidence.append(
            f"Observed value: {anomaly.value:,.2f} "
            f"(expected: {anomaly.expected_min:,.2f} – {anomaly.expected_max:,.2f})"
        )

        for d in root_cause.primary_drivers[:3]:
            segment = d.get("segment", d.get("dimension", ""))
            contrib = d.get("contribution", d.get("impact", 0))
            evidence.append(f"Driver: {segment} contributed {contrib:.1f}%")

        for c in root_cause.correlations[:2]:
            metric = c.get("metric", "")
            coeff = c.get("coefficient", 0)
            evidence.append(f"Correlation: {metric} (r={coeff:.2f})")

        return evidence
