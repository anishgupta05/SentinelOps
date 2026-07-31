from datetime import UTC, datetime

from sentinelops.connectors import SlackConnector
from sentinelops.contracts.events import SourceEvent

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def make_event(id: str, thread_id: str) -> SourceEvent:
    return SourceEvent(
        id=id,
        source="slack",
        event_type="message",
        thread_id=thread_id,
        author="alice",
        text="broken again",
        occurred_at=NOW,
    )


def test_fetch_events_filters_by_event_id() -> None:
    connector = SlackConnector(
        events=[make_event("s1", "t1"), make_event("s2", "t2")], enabled=True
    )
    assert [e.id for e in connector.fetch_events(event_ids=["s1"])] == ["s1"]


def test_fetch_events_with_no_filter_returns_all() -> None:
    connector = SlackConnector(
        events=[make_event("s1", "t1"), make_event("s2", "t2")], enabled=True
    )
    assert {e.id for e in connector.fetch_events()} == {"s1", "s2"}


def test_disabled_connector_returns_nothing() -> None:
    connector = SlackConnector(events=[make_event("s1", "t1")], enabled=False)
    assert connector.fetch_events() == []
    assert connector.fetch_events(event_ids=["s1"]) == []
