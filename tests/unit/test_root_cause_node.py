from datetime import UTC, datetime

from sentinelops.connectors import GitHubConnector, GmailConnector, LinearConnector, SlackConnector
from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.events import SourceEvent
from sentinelops.nodes.root_cause import analyze, gather_evidence
from sentinelops.reasoning.pipeshift import RuleBasedTriageModel

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def event(id: str, source: str, thread_id: str = "t1") -> SourceEvent:
    return SourceEvent(
        id=id,
        source=source,
        event_type="message",
        thread_id=thread_id,
        author="alice",
        text="it's broken",
        occurred_at=NOW,
    )


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


def test_gather_evidence_marks_disabled_connectors_unavailable() -> None:
    candidate = make_candidate()
    connectors = [
        SlackConnector(events=[event("s1", "slack")], enabled=True),
        GitHubConnector(events=[event("g1", "github")], enabled=False),
        LinearConnector(events=[], enabled=True),
        GmailConnector(events=[], enabled=False),
    ]
    evidence = gather_evidence(candidate, connectors)
    assert evidence.available_sources == ["slack", "linear"]
    assert evidence.missing_sources == ["github", "gmail"]


def test_analyze_produces_root_cause_from_gathered_evidence() -> None:
    candidate = make_candidate()
    connectors = [
        SlackConnector(events=[event("s1", "slack")], enabled=True),
        GitHubConnector(events=[], enabled=False),
        LinearConnector(events=[], enabled=False),
        GmailConnector(events=[], enabled=False),
    ]
    evidence = gather_evidence(candidate, connectors)
    result = analyze(candidate, evidence, RuleBasedTriageModel())
    assert result.complaint_id == candidate.id
    assert result.evidence_refs == ["s1"]
