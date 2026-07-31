from datetime import UTC, datetime
from uuid import uuid4

from sentinelops.contracts.complaints import ComplaintCandidate, SignalType
from sentinelops.contracts.events import SourceEvent
from sentinelops.graph.hydra import ContextGraph

_FRUSTRATION_KEYWORDS = (
    "again",
    "still broken",
    "ugh",
    "frustrating",
    "annoying",
    "sigh",
    "not working",
)

_SIGNAL_CONFIDENCE_BASE = 0.5
_SIGNAL_CONFIDENCE_PER_SIGNAL = 0.15
_SIGNAL_CONFIDENCE_CAP = 0.9


def _has_frustration_language(events: list[SourceEvent]) -> bool:
    return any(keyword in e.text.lower() for e in events for keyword in _FRUSTRATION_KEYWORDS)


def _signals_for_thread(
    slack_events: list[SourceEvent], has_linked_ticket: bool, is_duplicate: bool
) -> list[SignalType]:
    signals: list[SignalType] = []
    if not has_linked_ticket:
        signals.append("no_linked_ticket")
    if len(slack_events) > 1:
        signals.append("repeated_mention")
    if _has_frustration_language(slack_events):
        signals.append("frustration_language")
    if is_duplicate:
        signals.append("duplicate_of_prior_incident")
    return signals


def detect_candidates(
    graph: ContextGraph, *, now: datetime | None = None
) -> list[ComplaintCandidate]:
    """Scan resolved entities for unresolved Slack complaints: repeated mentions,
    frustration language, no linked Linear ticket, or a match to a prior incident."""
    now = now or datetime.now(UTC)
    candidates: list[ComplaintCandidate] = []

    for entity in graph.resolve_entities():
        events = graph.events_for_entity(entity.id)
        slack_events = [e for e in events if e.source == "slack"]
        if not slack_events:
            continue

        has_linked_ticket = any(e.source == "linear" for e in events)
        is_duplicate = any(e.metadata.get("duplicate_of") for e in events)
        signal_types = _signals_for_thread(slack_events, has_linked_ticket, is_duplicate)
        if not signal_types:
            continue

        confidence = min(
            _SIGNAL_CONFIDENCE_BASE + _SIGNAL_CONFIDENCE_PER_SIGNAL * len(signal_types),
            _SIGNAL_CONFIDENCE_CAP,
        )
        linked_ticket_id = next(
            (e.metadata.get("duplicate_of") for e in events if e.metadata.get("duplicate_of")),
            None,
        )
        candidates.append(
            ComplaintCandidate(
                id=f"candidate-{uuid4().hex[:8]}",
                thread_id=slack_events[0].thread_id or entity.id,
                source_event_ids=[e.id for e in events],
                signal_types=signal_types,
                has_linked_ticket=has_linked_ticket,
                linked_ticket_id=linked_ticket_id,
                summary=slack_events[0].text,
                confidence=confidence,
                detected_at=now,
            )
        )

    return candidates
