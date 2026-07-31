from typing import Literal

from pydantic import BaseModel

PolicyAction = Literal[
    "file_ticket",
    "draft_ticket",
    "tag_user",
    "escalate_severity",
    "post_notification",
]


class IntentPolicyDecision(BaseModel):
    """An InsForge-style authorization decision, kept separate from model reasoning.
    Nodes must check this before taking any externally-visible action."""

    id: str
    action: PolicyAction
    allowed: bool
    reason: str
    matched_rule: str | None = None
    required_evidence_met: bool
