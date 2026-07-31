import hashlib
from collections import defaultdict
from typing import Protocol

from sentinelops.contracts.entities import EntityType, NormalizedEntity
from sentinelops.contracts.events import SourceEvent


class ContextGraph(Protocol):
    """Entity-resolved join across Slack, GitHub, Linear, and Gmail.

    A single connector can't tell you a Slack thread, a GitHub issue, and a Gmail
    escalation are about the same incident. This is the seam that can.
    """

    def ingest(self, events: list[SourceEvent]) -> None: ...

    def resolve_entities(self) -> list[NormalizedEntity]: ...

    def events_for_entity(self, entity_id: str) -> list[SourceEvent]: ...


def _link_key(event: SourceEvent) -> str:
    """Cross-source join key: an explicit link (e.g. a ticket ID quoted in a Slack
    message, or a customer ref shared by a Gmail thread and a Slack thread) takes
    priority; otherwise fall back to the source's own thread_id."""
    linked = event.metadata.get("link_key")
    if linked:
        return str(linked)
    return event.thread_id or event.id


class InMemoryHydraGraph:
    """Local mock of HydraDB: groups ingested events into resolved entities by
    join key. A real HydraDB client would do this with proper entity resolution
    instead of exact key matching, but the interface stays the same."""

    def __init__(self) -> None:
        self._events: list[SourceEvent] = []

    def ingest(self, events: list[SourceEvent]) -> None:
        self._events.extend(events)

    def resolve_entities(self) -> list[NormalizedEntity]:
        groups: dict[str, list[SourceEvent]] = defaultdict(list)
        for event in self._events:
            groups[_link_key(event)].append(event)

        entities = []
        for key, events in groups.items():
            sources = {e.source for e in events}
            entity_type: EntityType = "thread"
            confidence = 0.5 + 0.15 * (len(sources) - 1) if len(sources) > 1 else 0.6
            key_hash = hashlib.sha1(key.encode()).hexdigest()[:8]
            entities.append(
                NormalizedEntity(
                    id=f"entity-{key_hash}",
                    entity_type=entity_type,
                    display_name=key,
                    source_ids=[e.id for e in events],
                    resolution_confidence=min(confidence, 0.95),
                )
            )
        return entities

    def events_for_entity(self, entity_id: str) -> list[SourceEvent]:
        entity = next((e for e in self.resolve_entities() if e.id == entity_id), None)
        if entity is None:
            return []
        return [e for e in self._events if e.id in entity.source_ids]

    def all_events(self) -> list[SourceEvent]:
        return list(self._events)
