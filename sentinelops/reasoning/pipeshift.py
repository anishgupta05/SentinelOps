from typing import Protocol

from sentinelops.contracts.common import Severity
from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle
from sentinelops.contracts.root_cause import RootCauseAnalysis

# How much each available source contributes to root-cause confidence. Slack is
# where the signal originates so it's weighted highest; the others each add
# grounding a Slack-only run can't have. Chosen so slack-only tops out well
# below the auto-file threshold in the default policy, making the
# full-vs-degraded demo delta visible without a real model in the loop.
SOURCE_WEIGHTS: dict[str, float] = {
    "slack": 0.35,
    "github": 0.25,
    "linear": 0.2,
    "gmail": 0.2,
}

_SEVERITY_KEYWORDS: dict[Severity, tuple[str, ...]] = {
    "critical": ("down", "outage", "data loss", "can't login", "cannot login"),
    "high": ("crash", "broken", "blocked", "failing"),
    "medium": ("slow", "confusing", "annoying", "bug"),
}


def _infer_severity(text: str) -> Severity:
    lowered = text.lower()
    for severity, keywords in _SEVERITY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return severity
    return "low"


class TriageModel(Protocol):
    """Root-cause reasoning over an evidence bundle. Model-agnostic on purpose: a
    real Pipeshift client implements this same signature."""

    def assess(
        self, candidate: ComplaintCandidate, evidence: EvidenceBundle
    ) -> RootCauseAnalysis: ...


class RuleBasedTriageModel:
    """Deterministic stand-in for a Pipeshift-hosted triage model. Confidence is a
    weighted sum over available evidence sources, so missing sources visibly
    lower confidence rather than just producing thinner text."""

    generated_by = "pipeshift-mock-v1"

    def assess(
        self, candidate: ComplaintCandidate, evidence: EvidenceBundle
    ) -> RootCauseAnalysis:
        available = evidence.available_sources
        confidence = round(sum(SOURCE_WEIGHTS[s] for s in available), 2)
        confidence = max(0.1, min(confidence, 0.95))

        severity_text = " ".join(
            e.text for s in evidence.sources if s.available for e in s.events
        ) or candidate.summary
        severity = _infer_severity(severity_text)

        evidence_refs = [
            e.id for s in evidence.sources if s.available for e in s.events
        ]

        hypothesis = (
            f"Likely cause relates to: {candidate.summary!r}. "
            f"Grounded in {len(available)}/{len(SOURCE_WEIGHTS)} source(s): "
            f"{', '.join(available) if available else 'none'}."
        )

        return RootCauseAnalysis(
            complaint_id=candidate.id,
            hypothesis=hypothesis,
            severity=severity,
            confidence=confidence,
            evidence_refs=evidence_refs,
            missing_evidence_sources=evidence.missing_sources,
            generated_by=self.generated_by,
        )
