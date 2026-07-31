from typing import Protocol

from sentinelops.contracts.common import SourceName
from sentinelops.contracts.events import SourceEvent


class SourceConnector(Protocol):
    """Uniform read interface every per-source connector implements.

    `enabled=False` is how the degraded-context demo drops a source without
    touching node logic: `fetch_events` just returns nothing.
    """

    source: SourceName
    enabled: bool

    def fetch_events(self, thread_id: str | None = None) -> list[SourceEvent]: ...


class FixtureConnector:
    """Connector backed by an in-memory list of events, standing in for a real API client."""

    def __init__(self, source: SourceName, events: list[SourceEvent], enabled: bool = True) -> None:
        self.source = source
        self.enabled = enabled
        self._events = events

    def fetch_events(self, thread_id: str | None = None) -> list[SourceEvent]:
        if not self.enabled:
            return []
        if thread_id is None:
            return list(self._events)
        return [e for e in self._events if e.thread_id == thread_id]
