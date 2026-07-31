from typing import Literal

from pydantic import BaseModel, Field

from sentinelops.contracts.common import Confidence, Severity

TicketMode = Literal["draft", "filed"]


class TicketProposal(BaseModel):
    """A Linear issue the fix-proposal node drafted or filed, per the governing intent policy."""

    id: str
    complaint_id: str
    title: str
    description: str
    root_cause_summary: str
    evidence_links: list[str] = Field(default_factory=list)
    suggested_owner: str | None = None
    severity: Severity
    confidence: Confidence
    mode: TicketMode
    policy_decision_id: str | None = None
    linear_issue_id: str | None = None
    linear_issue_url: str | None = None
