"""End-to-end coverage of the cross-tool gap scenarios listed in CLAUDE.md's
Testing Guidance. Each test below maps to one bullet there:

- Slack complaint with no Linear ticket -> tests/unit/test_triage.py
- Slack complaint with an existing linked Linear issue -> tests/unit/test_triage.py
- Duplicate complaint matching an old GitHub issue -> this file
- Customer escalation in Gmail matching an internal Slack thread -> this file
- Slack-only degraded context producing lower confidence ->
  tests/integration/test_pipeline_full_vs_degraded.py
"""

from datetime import UTC, datetime

from sentinelops.connectors import GitHubConnector, GmailConnector, LinearConnector, SlackConnector
from sentinelops.contracts.events import SourceEvent
from sentinelops.graph.hydra import InMemoryHydraGraph
from sentinelops.nodes.root_cause import gather_evidence
from sentinelops.nodes.triage import detect_candidates

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def event(
    id: str, source: str, thread_id: str, text: str, **metadata: str
) -> SourceEvent:
    return SourceEvent(
        id=id,
        source=source,
        event_type="message",
        thread_id=thread_id,
        author="alice",
        text=text,
        occurred_at=NOW,
        metadata=metadata,
    )


def test_duplicate_complaint_matches_an_old_github_issue() -> None:
    """A fresh Slack complaint that references a previously-filed GitHub issue
    should be flagged as a duplicate, not investigated as a brand-new incident."""
    graph = InMemoryHydraGraph()
    graph.ingest(
        [
            event(
                "slack-1",
                "slack",
                "t1",
                "Getting the same login timeout as before",
                duplicate_of="GH-317",
            ),
        ]
    )

    candidates = detect_candidates(graph, now=NOW)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert "duplicate_of_prior_incident" in candidate.signal_types
    assert candidate.linked_ticket_id == "GH-317"


def test_gmail_escalation_matches_internal_slack_thread() -> None:
    """A Gmail customer escalation and an internal Slack thread about the same
    incident should resolve to one entity and surface together as evidence,
    even though neither source alone tells the full story."""
    graph = InMemoryHydraGraph()
    graph.ingest(
        [
            event(
                "slack-1",
                "slack",
                "t1",
                "Internal: seeing intermittent 500s on the billing endpoint",
                link_key="billing-500",
            ),
            event(
                "gmail-1",
                "gmail",
                "g1",
                "Customer escalation: Acme Corp reports failed billing charges since this morning",
                link_key="billing-500",
            ),
        ]
    )

    candidates = detect_candidates(graph, now=NOW)
    assert len(candidates) == 1
    candidate = candidates[0]

    connectors = [
        SlackConnector(
            events=[event("slack-1", "slack", "t1", "seeing 500s", link_key="billing-500")],
            enabled=True,
        ),
        GitHubConnector(events=[], enabled=True),
        LinearConnector(events=[], enabled=True),
        GmailConnector(
            events=[
                event(
                    "gmail-1",
                    "gmail",
                    "g1",
                    "Customer escalation: Acme Corp reports failed billing charges",
                    link_key="billing-500",
                )
            ],
            enabled=True,
        ),
    ]
    evidence = gather_evidence(candidate, connectors)

    assert "gmail" in evidence.available_sources
    gmail_evidence = next(s for s in evidence.sources if s.source == "gmail")
    assert len(gmail_evidence.events) == 1
    assert "Acme Corp" in gmail_evidence.events[0].text
