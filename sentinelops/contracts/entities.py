from typing import Literal

from pydantic import BaseModel, Field

from sentinelops.contracts.common import Confidence

EntityType = Literal["person", "thread", "repo", "ticket"]


class NormalizedEntity(BaseModel):
    """An entity resolved across two or more source systems, e.g. HydraDB's join output."""

    id: str
    entity_type: EntityType
    display_name: str
    source_ids: list[str] = Field(default_factory=list)
    resolution_confidence: Confidence
