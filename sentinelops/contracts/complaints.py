from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from sentinelops.contracts.common import Confidence

SignalType = Literal[
    "repeated_mention",
    "frustration_language",
    "no_linked_ticket",
    "duplicate_of_prior_incident",
]


class ComplaintCandidate(BaseModel):
    """A thread the triage node flagged as an unresolved complaint worth investigating."""

    id: str
    thread_id: str
    source_event_ids: list[str] = Field(default_factory=list)
    signal_types: list[SignalType]
    has_linked_ticket: bool
    linked_ticket_id: str | None = None
    summary: str
    confidence: Confidence
    detected_at: datetime
