from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sentinelops.contracts.common import SourceName


class SourceEvent(BaseModel):
    """A single raw event as it was observed in one source system."""

    id: str
    source: SourceName
    event_type: str
    thread_id: str | None = None
    author: str
    text: str
    url: str | None = None
    occurred_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
