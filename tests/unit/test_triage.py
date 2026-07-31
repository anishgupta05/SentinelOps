from datetime import UTC, datetime

from sentinelops.contracts.events import SourceEvent
from sentinelops.graph.hydra import InMemoryHydraGraph
from sentinelops.nodes.triage import detect_candidates

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def event(
    id: str, source: str, thread_id: str, text: str = "it's broken", **metadata: str
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


def test_slack_complaint_with_no_linked_ticket_is_flagged() -> None:
    graph = InMemoryHydraGraph()
    graph.ingest([event("s1", "slack", "t1", text="checkout is broken again")])
    candidates = detect_candidates(graph, now=NOW)
    assert len(candidates) == 1
    assert "no_linked_ticket" in candidates[0].signal_types
    assert candidates[0].has_linked_ticket is False


def test_slack_complaint_with_linked_ticket_is_not_flagged() -> None:
    graph = InMemoryHydraGraph()
    graph.ingest(
        [
            event("s1", "slack", "t1", text="checkout is broken"),
            event("l1", "linear", "t1", text="LIN-1 tracking checkout bug"),
        ]
    )
    candidates = detect_candidates(graph, now=NOW)
    assert candidates == []


def test_non_slack_only_threads_are_ignored() -> None:
    graph = InMemoryHydraGraph()
    graph.ingest([event("g1", "github", "t1", text="issue filed")])
    assert detect_candidates(graph, now=NOW) == []


def test_duplicate_of_prior_incident_signal() -> None:
    graph = InMemoryHydraGraph()
    graph.ingest(
        [
            event("s1", "slack", "t1", text="checkout is broken", duplicate_of="GH-42"),
        ]
    )
    candidates = detect_candidates(graph, now=NOW)
    assert len(candidates) == 1
    assert "duplicate_of_prior_incident" in candidates[0].signal_types
    assert candidates[0].linked_ticket_id == "GH-42"
