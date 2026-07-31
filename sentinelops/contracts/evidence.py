from pydantic import BaseModel, Field

from sentinelops.contracts.common import SourceName
from sentinelops.contracts.events import SourceEvent


class SourceEvidence(BaseModel):
    """Evidence gathered from one source. `available=False` means the source was disabled or
    unreachable for this run, not that it had nothing relevant."""

    source: SourceName
    available: bool
    events: list[SourceEvent] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    """All cross-source evidence gathered for a complaint candidate, one entry per source."""

    complaint_id: str
    sources: list[SourceEvidence]

    @property
    def available_sources(self) -> list[SourceName]:
        return [s.source for s in self.sources if s.available]

    @property
    def missing_sources(self) -> list[SourceName]:
        return [s.source for s in self.sources if not s.available]
