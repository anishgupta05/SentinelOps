from datetime import UTC, datetime

from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle, SourceEvidence
from sentinelops.contracts.root_cause import RootCauseAnalysis
from sentinelops.nodes.fix_proposal import propose
from sentinelops.policy.config import PolicyConfig
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def make_candidate() -> ComplaintCandidate:
    return ComplaintCandidate(
        id="c1",
        thread_id="t1",
        source_event_ids=["s1"],
        signal_types=["no_linked_ticket"],
        has_linked_ticket=False,
        summary="checkout is broken",
        confidence=0.7,
        detected_at=NOW,
    )


def make_analysis(confidence: float) -> RootCauseAnalysis:
    return RootCauseAnalysis(
        complaint_id="c1",
        hypothesis="regression in checkout",
        severity="high",
        confidence=confidence,
        evidence_refs=["s1"],
        missing_evidence_sources=[],
        generated_by="pipeshift-mock-v1",
    )


def make_evidence() -> EvidenceBundle:
    return EvidenceBundle(
        complaint_id="c1", sources=[SourceEvidence(source="slack", available=True, events=[])]
    )


def test_draft_only_policy_produces_draft_ticket() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(auto_file=False))
    proposal, decision = propose(make_candidate(), make_analysis(0.95), make_evidence(), policy)
    assert proposal.mode == "draft"
    assert decision.allowed is False
    assert proposal.policy_decision_id == decision.id


def test_auto_file_enabled_with_high_confidence_files_ticket() -> None:
    policy = ConfigDrivenIntentPolicy(
        PolicyConfig(auto_file=True, min_confidence_to_file=0.8)
    )
    proposal, decision = propose(make_candidate(), make_analysis(0.9), make_evidence(), policy)
    assert proposal.mode == "filed"
    assert decision.allowed is True


def test_auto_file_enabled_but_low_confidence_stays_draft() -> None:
    policy = ConfigDrivenIntentPolicy(
        PolicyConfig(auto_file=True, min_confidence_to_file=0.8)
    )
    proposal, decision = propose(make_candidate(), make_analysis(0.3), make_evidence(), policy)
    assert proposal.mode == "draft"
    assert decision.allowed is False
