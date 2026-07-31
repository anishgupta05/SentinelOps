from uuid import uuid4

from sentinelops.connectors.base import SourceConnector
from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle
from sentinelops.contracts.notifications import NotificationPayload
from sentinelops.contracts.policy import IntentPolicyDecision
from sentinelops.contracts.tickets import TicketProposal
from sentinelops.policy.insforge import IntentPolicy


def notify(
    candidate: ComplaintCandidate,
    proposal: TicketProposal,
    evidence: EvidenceBundle,
    policy: IntentPolicy,
    slack_connector: SourceConnector,
) -> tuple[NotificationPayload, IntentPolicyDecision]:
    """Post back to the source Slack thread, gated by its own policy check - a
    filed/drafted ticket does not automatically authorize posting about it."""
    decision = policy.decide(
        "post_notification",
        severity=proposal.severity,
        confidence=proposal.confidence,
        evidence_sources=evidence.available_sources,
    )
    sent = decision.allowed and slack_connector.enabled

    verb = "Filed" if proposal.mode == "filed" else "Drafted"
    payload = NotificationPayload(
        id=f"notify-{uuid4().hex[:8]}",
        complaint_id=candidate.id,
        channel_ref=f"slack:{candidate.thread_id}",
        ticket_id=proposal.id if proposal.mode == "filed" else None,
        ticket_url=proposal.linear_issue_url,
        message=f"{verb} a ticket for this: {proposal.title}",
        rationale=(
            f"{proposal.root_cause_summary} (confidence {proposal.confidence:.2f}, "
            f"grounded in {len(evidence.available_sources)} source(s))"
        ),
        sent=sent,
    )
    return payload, decision
