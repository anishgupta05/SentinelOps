from uuid import uuid4

from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle
from sentinelops.contracts.policy import IntentPolicyDecision
from sentinelops.contracts.root_cause import RootCauseAnalysis
from sentinelops.contracts.tickets import TicketProposal
from sentinelops.policy.insforge import IntentPolicy


def propose(
    candidate: ComplaintCandidate,
    analysis: RootCauseAnalysis,
    evidence: EvidenceBundle,
    policy: IntentPolicy,
    *,
    suggested_owner: str | None = None,
) -> tuple[TicketProposal, IntentPolicyDecision]:
    """Draft a ticket, then ask the intent policy whether it may actually be filed.
    The policy decision - not the model - controls whether `mode` is "filed"."""
    decision = policy.decide(
        "file_ticket",
        severity=analysis.severity,
        confidence=analysis.confidence,
        evidence_sources=evidence.available_sources,
    )

    proposal = TicketProposal(
        id=f"ticket-{uuid4().hex[:8]}",
        complaint_id=candidate.id,
        title=candidate.summary[:80],
        description=_build_description(candidate, analysis),
        root_cause_summary=analysis.hypothesis,
        evidence_links=analysis.evidence_refs,
        suggested_owner=suggested_owner,
        severity=analysis.severity,
        confidence=analysis.confidence,
        mode="filed" if decision.allowed else "draft",
        policy_decision_id=decision.id,
    )
    return proposal, decision


def _build_description(candidate: ComplaintCandidate, analysis: RootCauseAnalysis) -> str:
    lines = [
        f"Reported: {candidate.summary}",
        f"Signals: {', '.join(candidate.signal_types)}",
        f"Root cause hypothesis: {analysis.hypothesis}",
    ]
    if analysis.missing_evidence_sources:
        lines.append(f"Missing evidence from: {', '.join(analysis.missing_evidence_sources)}")
    return "\n".join(lines)
