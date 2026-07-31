from dataclasses import dataclass

from sentinelops.connectors.base import SourceConnector
from sentinelops.contracts.complaints import ComplaintCandidate
from sentinelops.contracts.evidence import EvidenceBundle
from sentinelops.contracts.notifications import NotificationPayload
from sentinelops.contracts.root_cause import RootCauseAnalysis
from sentinelops.contracts.tickets import TicketProposal
from sentinelops.graph.hydra import ContextGraph
from sentinelops.nodes.fix_proposal import propose
from sentinelops.nodes.notify import notify
from sentinelops.nodes.root_cause import analyze, gather_evidence
from sentinelops.nodes.triage import detect_candidates
from sentinelops.orchestrator.rocketride import PipelineTrace, TraceRecorder
from sentinelops.policy.insforge import IntentPolicy
from sentinelops.reasoning.pipeshift import TriageModel


@dataclass
class PipelineResult:
    candidates: list[ComplaintCandidate]
    candidate: ComplaintCandidate | None
    evidence: EvidenceBundle | None
    analysis: RootCauseAnalysis | None
    proposal: TicketProposal | None
    notification: NotificationPayload | None
    trace: PipelineTrace
    rocketride_status: dict | None = None
    insforge_audit_row: dict | None = None


def run(
    query: str,
    context_label: str,
    graph: ContextGraph,
    connectors: list[SourceConnector],
    model: TriageModel,
    policy: IntentPolicy,
    recorder: TraceRecorder,
) -> PipelineResult:
    """Chain triage -> root-cause -> fix-proposal -> notify, recording each step
    into `recorder` so the trace shows exactly how grounded each node's output
    was. Only the highest-confidence candidate carries through past triage -
    that's the one the demo narrates end to end."""
    recorder.start_trace(query=query, context_label=context_label)

    with recorder.record("triage", input_summary=f"query={query!r}") as span:
        candidates = detect_candidates(graph)
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        top = candidates[0] if candidates else None
        span.output_summary = (
            f"{len(candidates)} candidate(s); top: {top.summary!r}"
            if top
            else "0 candidates found"
        )
        span.confidence = top.confidence if top else None

    if top is None:
        return PipelineResult(
            candidates=candidates,
            candidate=None,
            evidence=None,
            analysis=None,
            proposal=None,
            notification=None,
            trace=recorder.trace,
        )

    with recorder.record("root_cause", input_summary=top.summary) as span:
        evidence = gather_evidence(top, connectors)
        analysis = analyze(top, evidence, model)
        span.output_summary = analysis.hypothesis
        span.confidence = analysis.confidence
        span.evidence_used = analysis.evidence_refs

    with recorder.record("fix_proposal", input_summary=analysis.hypothesis) as span:
        proposal, policy_decision = propose(top, analysis, evidence, policy)
        span.output_summary = (
            f"{proposal.mode} ticket {proposal.title!r} ({policy_decision.reason})"
        )
        span.confidence = proposal.confidence
        span.evidence_used = proposal.evidence_links

    slack_connector = next(c for c in connectors if c.source == "slack")
    with recorder.record("notify", input_summary=proposal.title) as span:
        payload, notify_decision = notify(top, proposal, evidence, policy, slack_connector)
        span.output_summary = f"{payload.message} ({'sent' if payload.sent else 'not sent'})"
        span.confidence = proposal.confidence

    return PipelineResult(
        candidates=candidates,
        candidate=top,
        evidence=evidence,
        analysis=analysis,
        proposal=proposal,
        notification=payload,
        trace=recorder.trace,
    )
