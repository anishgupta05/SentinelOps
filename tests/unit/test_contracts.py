from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from sentinelops.contracts import (
    ComplaintCandidate,
    EvidenceBundle,
    IntentPolicyDecision,
    NormalizedEntity,
    NotificationPayload,
    RootCauseAnalysis,
    SourceEvent,
    SourceEvidence,
    TicketProposal,
)

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def make_event(id: str = "slack-1", source: str = "slack") -> SourceEvent:
    return SourceEvent(
        id=id,
        source=source,
        event_type="message",
        thread_id="thread-1",
        author="alice",
        text="this is broken again",
        occurred_at=NOW,
    )


def test_source_event_roundtrip() -> None:
    event = make_event()
    assert SourceEvent.model_validate(event.model_dump()) == event


def test_complaint_candidate_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        ComplaintCandidate(
            id="c1",
            thread_id="thread-1",
            source_event_ids=["slack-1"],
            signal_types=["no_linked_ticket"],
            has_linked_ticket=False,
            summary="repeated complaint",
            confidence=1.5,
            detected_at=NOW,
        )


def test_evidence_bundle_tracks_missing_sources() -> None:
    bundle = EvidenceBundle(
        complaint_id="c1",
        sources=[
            SourceEvidence(source="slack", available=True, events=[make_event()]),
            SourceEvidence(source="github", available=False),
            SourceEvidence(source="linear", available=False),
            SourceEvidence(source="gmail", available=False),
        ],
    )
    assert bundle.available_sources == ["slack"]
    assert bundle.missing_sources == ["github", "linear", "gmail"]


def test_root_cause_analysis_carries_provenance() -> None:
    analysis = RootCauseAnalysis(
        complaint_id="c1",
        hypothesis="Regression in auth middleware",
        severity="high",
        confidence=0.4,
        evidence_refs=["slack-1"],
        missing_evidence_sources=["github", "linear", "gmail"],
        generated_by="pipeshift-mock",
    )
    assert analysis.missing_evidence_sources == ["github", "linear", "gmail"]


def test_ticket_proposal_defaults_to_draft_mode() -> None:
    proposal = TicketProposal(
        id="t1",
        complaint_id="c1",
        title="Auth middleware regression",
        description="Repro steps...",
        root_cause_summary="Likely a regression in auth middleware.",
        severity="high",
        confidence=0.4,
        mode="draft",
    )
    assert proposal.mode == "draft"
    assert proposal.linear_issue_id is None


def test_notification_payload_and_policy_decision_construct() -> None:
    policy_decision = IntentPolicyDecision(
        id="p1",
        action="draft_ticket",
        allowed=True,
        reason="confidence below auto-file threshold",
        required_evidence_met=False,
    )
    payload = NotificationPayload(
        id="n1",
        complaint_id="c1",
        channel_ref="slack:thread-1",
        message="Drafted a ticket for this.",
        rationale="Low confidence due to missing GitHub/Linear/Gmail context.",
        sent=True,
    )
    assert policy_decision.allowed is True
    assert payload.sent is True


def test_normalized_entity_requires_confidence() -> None:
    entity = NormalizedEntity(
        id="e1",
        entity_type="thread",
        display_name="auth middleware regression thread",
        source_ids=["slack-1", "github-42"],
        resolution_confidence=0.8,
    )
    assert entity.source_ids == ["slack-1", "github-42"]
