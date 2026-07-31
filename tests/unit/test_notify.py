from datetime import UTC, datetime

from sentinelops.connectors import SlackConnector
from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle, SourceEvidence
from sentinelops.contracts.tickets import TicketProposal
from sentinelops.nodes.notify import notify
from sentinelops.policy.config import PolicyConfig
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def make_candidate() -> ComplaintCandidate:
    return ComplaintCandidate(
        id="c1",
        thread_id="t1",
        source_event_ids=["s1"],
        signal_types=["no_linked_ticket"],
        has_linked_ticket=False,
        summary="checkout is broken",
        confidence=0.7,
        detected_at=NOW,
    )


def make_proposal(mode: str = "draft") -> TicketProposal:
    return TicketProposal(
        id="ticket-1",
        complaint_id="c1",
        title="checkout is broken",
        description="...",
        root_cause_summary="regression in checkout",
        severity="high",
        confidence=0.9,
        mode=mode,
    )


def make_evidence() -> EvidenceBundle:
    return EvidenceBundle(
        complaint_id="c1", sources=[SourceEvidence(source="slack", available=True, events=[])]
    )


def test_notify_sends_when_policy_allows_and_connector_enabled() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(required_evidence_sources=["slack"]))
    slack = SlackConnector(events=[], enabled=True)
    payload, decision = notify(make_candidate(), make_proposal(), make_evidence(), policy, slack)
    assert decision.allowed is True
    assert payload.sent is True
    assert payload.channel_ref == "slack:t1"


def test_notify_does_not_send_when_connector_disabled() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(required_evidence_sources=["slack"]))
    slack = SlackConnector(events=[], enabled=False)
    payload, decision = notify(make_candidate(), make_proposal(), make_evidence(), policy, slack)
    assert decision.allowed is True
    assert payload.sent is False


def test_notify_does_not_send_when_required_evidence_missing() -> None:
    policy = ConfigDrivenIntentPolicy(PolicyConfig(required_evidence_sources=["github"]))
    slack = SlackConnector(events=[], enabled=True)
    payload, decision = notify(make_candidate(), make_proposal(), make_evidence(), policy, slack)
    assert decision.allowed is False
    assert payload.sent is False
