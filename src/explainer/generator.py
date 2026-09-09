"""
Explanation Generator — Main orchestrator.

Coordinates:
1. Build structured prompt from anomaly + root cause data
2. Call LLM for natural language explanation
3. Fall back to template if LLM unavailable/fails
4. Validate and format response
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .models import (
    ExplanationConfig,
    ExplanationRequest,
    ExplanationResponse,
)
from .templates import TemplateRenderer
from .llm_client import LLMClient, LLMError, LLMUnavailableError

logger = logging.getLogger(__name__)


# System prompt for the LLM
SYSTEM_PROMPT = """You are a senior business analyst AI. Your job is to explain data anomalies to business stakeholders clearly and concisely.

RULES:
1. Base your explanation STRICTLY on the provided data. Do NOT invent facts.
2. Structure your response with these sections:
   - **What Happened**: Describe the anomaly (metric, value, deviation)
   - **Where**: Which segments/dimensions are affected
   - **Why**: Root cause analysis findings with evidence
   - **Recommendations**: 2-3 actionable next steps
3. Use plain business language. Avoid jargon.
4. Be specific: include numbers, percentages, and timeframes.
5. Keep total response under 300 words.
6. If evidence is weak, say so honestly."""


def _build_user_prompt(request: ExplanationRequest) -> str:
    """Build the user prompt from structured data."""
    anomaly = request.anomaly
    root_cause = request.root_cause

    expected_mid = (anomaly.expected_min + anomaly.expected_max) / 2
    if expected_mid != 0:
        pct_change = ((anomaly.value - expected_mid) / abs(expected_mid)) * 100
    else:
        pct_change = 0

    prompt_parts = [
        "Please explain this business anomaly:\n",
        "## Anomaly Data",
        f"- Metric: {anomaly.metric}",
        f"- Timestamp: {anomaly.timestamp.isoformat()}",
        f"- Observed Value: {anomaly.value:,.2f}",
        f"- Expected Range: {anomaly.expected_min:,.2f} – {anomaly.expected_max:,.2f}",
        f"- Percentage Deviation: {pct_change:+.1f}%",
        f"- Type: {anomaly.anomaly_type}",
        f"- Severity: {anomaly.severity:.2f} (0-1 scale)",
        f"- Confidence: {anomaly.confidence:.1f}%",
    ]

    if anomaly.dimensions:
        dims = ", ".join(f"{k}={v}" for k, v in anomaly.dimensions.items())
        prompt_parts.append(f"- Affected Segments: {dims}")

    prompt_parts.append("\n## Root Cause Analysis")
    prompt_parts.append(f"- Hypothesis: {root_cause.hypothesis}")
    prompt_parts.append(f"- Analysis Confidence: {root_cause.confidence:.2f}")

    if root_cause.primary_drivers:
        prompt_parts.append("\n### Primary Drivers:")
        for d in root_cause.primary_drivers[:5]:
            segment = d.get("segment", d.get("dimension", "Unknown"))
            contrib = d.get("contribution", d.get("impact", 0))
            ratio = d.get("baseline_ratio", 1.0)
            prompt_parts.append(
                f"  - {segment}: {contrib:.1f}% contribution "
                f"(baseline ratio: {ratio:.2f})"
            )

    if root_cause.correlations:
        prompt_parts.append("\n### Correlated Metrics:")
        for c in root_cause.correlations[:5]:
            metric = c.get("metric", "Unknown")
            coeff = c.get("coefficient", 0)
            p = c.get("p_value", 1.0)
            prompt_parts.append(
                f"  - {metric}: correlation={coeff:.3f}, p-value={p:.4f}"
            )

    if root_cause.change_point:
        cp = root_cause.change_point
        prompt_parts.append(f"\n### Change Point: Detected at {cp.get('detected_at', 'N/A')}")
        prompt_parts.append(f"  - Confidence: {cp.get('confidence', 0):.2f}")
        prompt_parts.append(
            f"  - Before mean: {cp.get('before_mean', 0):,.2f}, "
            f"After mean: {cp.get('after_mean', 0):,.2f}"
        )

    # Add RAG context if available
    if request.rag_context and request.rag_context.documents:
        prompt_parts.append("\n## Business Context (from knowledge base):")
        for doc in request.rag_context.documents[:3]:
            text = doc.get("text", "")[:300]
            score = doc.get("score", 0)
            prompt_parts.append(f"  [{score:.2f}] {text}")

    prompt_parts.append(
        f"\nAudience: {request.audience} stakeholders. "
        f"{'Include actionable recommendations.' if request.include_recommendations else ''}"
    )

    return "\n".join(prompt_parts)


class ExplanationGenerator:
    """
    Main explanation generation service.

    Tries LLM first, falls back to template if unavailable or fails.
    """

    def __init__(self, config: Optional[ExplanationConfig] = None):
        """
        Initialize generator.

        Args:
            config: ExplanationConfig with LLM settings
        """
        self.config = config or ExplanationConfig()
        self.llm_client = LLMClient(self.config)
        self.template_renderer = TemplateRenderer()

        # Stats
        self._stats = {
            "total_generated": 0,
            "llm_generated": 0,
            "template_fallbacks": 0,
            "errors": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
        }

        logger.info(
            f"ExplanationGenerator initialized "
            f"(LLM: {'available' if self.llm_client.is_available else 'unavailable, using templates'})"
        )

    def generate(self, request: ExplanationRequest) -> ExplanationResponse:
        """
        Generate explanation for an anomaly.

        Pipeline:
        1. Try LLM if available
        2. Fall back to template if LLM fails or unavailable
        3. Validate and return response

        Args:
            request: ExplanationRequest with anomaly + root cause data

        Returns:
            ExplanationResponse with explanation text
        """
        self._stats["total_generated"] += 1

        # Try LLM first
        if self.llm_client.is_available:
            try:
                return self._generate_with_llm(request)
            except (LLMError, LLMUnavailableError) as e:
                logger.warning(f"LLM failed, falling back to template: {e}")
            except Exception as e:
                logger.error(f"Unexpected LLM error: {e}")

        # Fallback to template
        if self.config.fallback_to_template:
            return self._generate_with_template(request)

        # No fallback — return error response
        self._stats["errors"] += 1
        return ExplanationResponse(
            anomaly_id=request.anomaly.anomaly_id,
            explanation_text="Explanation generation failed. LLM unavailable and template fallback disabled.",
            summary="Explanation unavailable.",
            confidence=0.0,
            used_fallback=True,
        )

    def _generate_with_llm(self, request: ExplanationRequest) -> ExplanationResponse:
        """Generate explanation using LLM."""
        user_prompt = _build_user_prompt(request)

        text, metadata = self.llm_client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        self._stats["llm_generated"] += 1
        self._stats["total_tokens_input"] += metadata.get("tokens_input", 0)
        self._stats["total_tokens_output"] += metadata.get("tokens_output", 0)

        # Parse recommendations from LLM response
        recommendations = self._extract_recommendations(text)

        # Build summary (first sentence or line)
        summary = text.split("\n")[0].strip()
        if summary.startswith("**"):
            summary = summary.replace("**", "").strip()
        if len(summary) > 150:
            summary = summary[:147] + "..."

        # Evidence from the structured data
        evidence = []
        evidence.append(
            f"Observed: {request.anomaly.value:,.2f} "
            f"(expected: {request.anomaly.expected_min:,.2f} – {request.anomaly.expected_max:,.2f})"
        )
        for d in request.root_cause.primary_drivers[:3]:
            segment = d.get("segment", d.get("dimension", ""))
            contrib = d.get("contribution", d.get("impact", 0))
            evidence.append(f"Driver: {segment} ({contrib:.1f}%)")

        return ExplanationResponse(
            anomaly_id=request.anomaly.anomaly_id,
            explanation_text=text,
            summary=summary,
            recommendations=recommendations,
            confidence=request.root_cause.confidence,
            evidence_citations=evidence,
            generated_at=datetime.utcnow(),
            llm_model=metadata.get("model"),
            tokens_input=metadata.get("tokens_input", 0),
            tokens_output=metadata.get("tokens_output", 0),
            latency_ms=metadata.get("latency_ms", 0),
            used_fallback=False,
        )

    def _generate_with_template(self, request: ExplanationRequest) -> ExplanationResponse:
        """Generate explanation using template fallback."""
        self._stats["template_fallbacks"] += 1
        return self.template_renderer.render(request)

    def _extract_recommendations(self, text: str) -> list:
        """Extract recommendations from LLM response text."""
        recs = []
        lines = text.split("\n")
        in_rec_section = False

        for line in lines:
            line_lower = line.strip().lower()
            if any(k in line_lower for k in ["recommendation", "next step", "action"]):
                in_rec_section = True
                continue

            if in_rec_section and line.strip():
                # Check if it's a new section header
                if line.strip().startswith("**") and not line.strip().startswith("**-"):
                    in_rec_section = False
                    continue

                # Extract numbered or bulleted items
                cleaned = line.strip().lstrip("0123456789.-•*) ").strip()
                if cleaned and len(cleaned) > 10:
                    recs.append(cleaned)

        return recs[:5]

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return self._stats.copy()
