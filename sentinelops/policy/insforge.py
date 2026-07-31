from typing import Protocol
from uuid import uuid4

from sentinelops.contracts.common import Severity, SourceName
from sentinelops.contracts.policy import IntentPolicyDecision, PolicyAction
from sentinelops.policy.config import PolicyConfig

_SEVERITY_RANK: dict[Severity, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class IntentPolicy(Protocol):
    """Authorization boundary, deliberately separate from model reasoning. Nodes must
    call this before any externally-visible action (filing, tagging, escalating)."""

    def decide(
        self,
        action: PolicyAction,
        *,
        severity: Severity,
        confidence: float,
        evidence_sources: list[SourceName],
        assignee: str | None = None,
    ) -> IntentPolicyDecision: ...


class ConfigDrivenIntentPolicy:
    """Local mock of InsForge: evaluates a `PolicyConfig` against the situation a
    node wants to act on. A real InsForge client would implement the same
    `decide` signature against a hosted policy instead of a local file."""

    def __init__(self, config: PolicyConfig) -> None:
        self._config = config

    def decide(
        self,
        action: PolicyAction,
        *,
        severity: Severity,
        confidence: float,
        evidence_sources: list[SourceName],
        assignee: str | None = None,
    ) -> IntentPolicyDecision:
        config = self._config
        required_evidence_met = all(
            source in evidence_sources for source in config.required_evidence_sources
        )

        if not required_evidence_met:
            return self._decision(
                action,
                allowed=False,
                reason=f"missing required evidence: {config.required_evidence_sources}",
                matched_rule="required_evidence_sources",
                required_evidence_met=False,
            )

        if action == "draft_ticket":
            return self._decision(
                action,
                allowed=True,
                reason="drafting is always permitted once required evidence is present",
                matched_rule="draft_ticket.always_allowed",
                required_evidence_met=True,
            )

        if action == "file_ticket":
            if not config.auto_file:
                return self._decision(
                    action,
                    allowed=False,
                    reason="auto_file is disabled; draft-only mode",
                    matched_rule="file_ticket.auto_file_disabled",
                    required_evidence_met=True,
                )
            if confidence < config.min_confidence_to_file:
                return self._decision(
                    action,
                    allowed=False,
                    reason=(
                        f"confidence {confidence:.2f} below "
                        f"min_confidence_to_file {config.min_confidence_to_file:.2f}"
                    ),
                    matched_rule="file_ticket.min_confidence_to_file",
                    required_evidence_met=True,
                )
            return self._decision(
                action,
                allowed=True,
                reason="auto_file enabled and confidence threshold met",
                matched_rule="file_ticket.threshold_met",
                required_evidence_met=True,
            )

        if action == "escalate_severity":
            severity_ok = (
                _SEVERITY_RANK[severity] >= _SEVERITY_RANK[config.severity_escalation_threshold]
            )
            confidence_ok = confidence >= config.min_confidence_to_escalate
            if severity_ok and confidence_ok:
                return self._decision(
                    action,
                    allowed=True,
                    reason="severity and confidence thresholds met",
                    matched_rule="escalate_severity.threshold_met",
                    required_evidence_met=True,
                )
            return self._decision(
                action,
                allowed=False,
                reason=(
                    f"severity={severity} confidence={confidence:.2f} below "
                    f"escalation thresholds"
                ),
                matched_rule="escalate_severity.threshold_not_met",
                required_evidence_met=True,
            )

        if action == "tag_user":
            allowed = assignee is not None and assignee in config.allowed_assignees
            return self._decision(
                action,
                allowed=allowed,
                reason=(
                    f"{assignee!r} in allowed_assignees"
                    if allowed
                    else f"{assignee!r} not in allowed_assignees"
                ),
                matched_rule="tag_user.allowed_assignees",
                required_evidence_met=True,
            )

        if action == "post_notification":
            return self._decision(
                action,
                allowed=True,
                reason="notifications are always permitted once required evidence is present",
                matched_rule="post_notification.always_allowed",
                required_evidence_met=True,
            )

        raise ValueError(f"unknown policy action: {action}")

    @staticmethod
    def _decision(
        action: PolicyAction,
        *,
        allowed: bool,
        reason: str,
        matched_rule: str,
        required_evidence_met: bool,
    ) -> IntentPolicyDecision:
        return IntentPolicyDecision(
            id=f"decision-{uuid4().hex[:8]}",
            action=action,
            allowed=allowed,
            reason=reason,
            matched_rule=matched_rule,
            required_evidence_met=required_evidence_met,
        )
