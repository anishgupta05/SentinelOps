from datetime import UTC, datetime

from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.events import SourceEvent
from sentinelops.contracts.evidence import EvidenceBundle, SourceEvidence
from sentinelops.reasoning.pipeshift import RuleBasedTriageModel

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


def make_event(id: str, source: str, text: str = "it's broken") -> SourceEvent:
    return SourceEvent(
        id=id, source=source, event_type="message", author="alice", text=text, occurred_at=NOW
    )


def test_full_context_yields_higher_confidence_than_degraded() -> None:
    model = RuleBasedTriageModel()
    candidate = make_candidate()

    full_evidence = EvidenceBundle(
        complaint_id="c1",
        sources=[
            SourceEvidence(source="slack", available=True, events=[make_event("s1", "slack")]),
            SourceEvidence(source="github", available=True, events=[make_event("g1", "github")]),
            SourceEvidence(source="linear", available=True, events=[make_event("l1", "linear")]),
            SourceEvidence(source="gmail", available=True, events=[make_event("m1", "gmail")]),
        ],
    )
    degraded_evidence = EvidenceBundle(
        complaint_id="c1",
        sources=[
            SourceEvidence(source="slack", available=True, events=[make_event("s1", "slack")]),
            SourceEvidence(source="github", available=False),
            SourceEvidence(source="linear", available=False),
            SourceEvidence(source="gmail", available=False),
        ],
    )

    full_result = model.assess(candidate, full_evidence)
    degraded_result = model.assess(candidate, degraded_evidence)

    assert full_result.confidence > degraded_result.confidence
    assert degraded_result.missing_evidence_sources == ["github", "linear", "gmail"]
    assert full_result.missing_evidence_sources == []


def test_severity_inferred_from_evidence_keywords() -> None:
    model = RuleBasedTriageModel()
    candidate = make_candidate()
    evidence = EvidenceBundle(
        complaint_id="c1",
        sources=[
            SourceEvidence(
                source="slack",
                available=True,
                events=[make_event("s1", "slack", text="prod is down, total outage")],
            ),
        ],
    )
    result = model.assess(candidate, evidence)
    assert result.severity == "critical"
