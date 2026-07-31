from pydantic import BaseModel, Field

from sentinelops.contracts.common import Confidence, Severity, SourceName


class RootCauseAnalysis(BaseModel):
    """Output of the root-cause node: a hypothesis grounded in the evidence bundle it was given."""

    complaint_id: str
    hypothesis: str
    severity: Severity
    confidence: Confidence
    evidence_refs: list[str] = Field(default_factory=list)
    missing_evidence_sources: list[SourceName] = Field(default_factory=list)
    generated_by: str
