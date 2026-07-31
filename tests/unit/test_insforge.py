from sentinelops.policy.config import PolicyConfig
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy


def test_draft_ticket_allowed_with_required_evidence() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig())
    decision = policy.decide(
        "draft_ticket", severity="medium", confidence=0.3, evidence_sources=["slack"]
    )
    assert decision.allowed is True


def test_draft_ticket_blocked_without_required_evidence() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(required_evidence_sources=["slack"]))
    decision = policy.decide(
        "draft_ticket", severity="medium", confidence=0.9, evidence_sources=["github"]
    )
    assert decision.allowed is False
    assert decision.required_evidence_met is False


def test_file_ticket_blocked_when_auto_file_disabled() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(auto_file=False))
    decision = policy.decide(
        "file_ticket", severity="high", confidence=0.99, evidence_sources=["slack"]
    )
    assert decision.allowed is False
    assert decision.matched_rule == "file_ticket.auto_file_disabled"


def test_file_ticket_blocked_below_confidence_threshold() -> None:
    policy = ConfigDrivenIntentPolicy(
        PolicyConfig(auto_file=True, min_confidence_to_file=0.8)
    )
    decision = policy.decide(
        "file_ticket", severity="high", confidence=0.5, evidence_sources=["slack"]
    )
    assert decision.allowed is False
    assert decision.matched_rule == "file_ticket.min_confidence_to_file"


def test_file_ticket_allowed_when_thresholds_met() -> None:
    policy = ConfigDrivenIntentPolicy(
        PolicyConfig(auto_file=True, min_confidence_to_file=0.8)
    )
    decision = policy.decide(
        "file_ticket", severity="high", confidence=0.9, evidence_sources=["slack"]
    )
    assert decision.allowed is True


def test_tag_user_requires_allowlist_membership() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(allowed_assignees=["bob"]))
    allowed = policy.decide(
        "tag_user", severity="low", confidence=0.5, evidence_sources=["slack"], assignee="bob"
    )
    blocked = policy.decide(
        "tag_user", severity="low", confidence=0.5, evidence_sources=["slack"], assignee="eve"
    )
    assert allowed.allowed is True
    assert blocked.allowed is False


def test_escalate_severity_requires_both_thresholds() -> None:
    policy = ConfigDrivenIntentPolicy(
        PolicyConfig(severity_escalation_threshold="high", min_confidence_to_escalate=0.7)
    )
    ok = policy.decide(
        "escalate_severity", severity="critical", confidence=0.8, evidence_sources=["slack"]
    )
    low_severity = policy.decide(
        "escalate_severity", severity="medium", confidence=0.9, evidence_sources=["slack"]
    )
    low_confidence = policy.decide(
        "escalate_severity", severity="critical", confidence=0.2, evidence_sources=["slack"]
    )
    assert ok.allowed is True
    assert low_severity.allowed is False
    assert low_confidence.allowed is False
