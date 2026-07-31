from datetime import UTC, datetime

from sentinelops.contracts.events import SourceEvent
from sentinelops.graph.hydra import InMemoryHydraGraph

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def event(
    id: str, source: str, thread_id: str | None = None, link_key: str | None = None
) -> SourceEvent:
    metadata = {"link_key": link_key} if link_key else {}
    return SourceEvent(
        id=id,
        source=source,
        event_type="message",
        thread_id=thread_id,
        author="alice",
        text="text",
        occurred_at=NOW,
        metadata=metadata,
    )


def test_events_without_link_key_group_by_thread_id() -> None:
    graph = InMemoryHydraGraph()
    graph.ingest([event("s1", "slack", thread_id="t1"), event("s2", "slack", thread_id="t2")])
    entities = graph.resolve_entities()
    assert len(entities) == 2


def test_cross_source_events_join_on_shared_link_key() -> None:
    """A Gmail escalation and a Slack thread referencing the same customer issue
    should resolve into one cross-source entity, per CLAUDE.md's escalation scenario."""
    graph = InMemoryHydraGraph()
    graph.ingest(
        [
            event("slack-1", "slack", thread_id="t1", link_key="CUST-42"),
            event("gmail-1", "gmail", thread_id="g1", link_key="CUST-42"),
        ]
    )
    entities = graph.resolve_entities()
    assert len(entities) == 1
    entity = entities[0]
    assert set(entity.source_ids) == {"slack-1", "gmail-1"}
    assert entity.resolution_confidence > 0.5


def test_events_for_entity_returns_underlying_events() -> None:
    graph = InMemoryHydraGraph()
    graph.ingest([event("s1", "slack", thread_id="t1", link_key="LIN-1")])
    entity = graph.resolve_entities()[0]
    events = graph.events_for_entity(entity.id)
    assert [e.id for e in events] == ["s1"]
