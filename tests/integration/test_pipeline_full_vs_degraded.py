from sentinelops.connectors import GitHubConnector, GmailConnector, LinearConnector, SlackConnector
from sentinelops.demo_data import load_context, load_events
from sentinelops.graph.hydra import InMemoryHydraGraph
from sentinelops.orchestrator.pipeline import run
from sentinelops.orchestrator.rocketride import InMemoryTraceRecorder
from sentinelops.policy.config import load_default_policy
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy
from sentinelops.reasoning.pipeshift import RuleBasedTriageModel


def run_demo(context_name: str):
    context = load_context(context_name)
    all_events = load_events()
    enabled = set(context.enabled_sources)

    graph = InMemoryHydraGraph()
    graph.ingest([e for e in all_events if e.source in enabled])

    def events_for(source: str):
        return [e for e in all_events if e.source == source]

    connectors = [
        SlackConnector(events=events_for("slack"), enabled="slack" in enabled),
        GitHubConnector(events=events_for("github"), enabled="github" in enabled),
        LinearConnector(events=events_for("linear"), enabled="linear" in enabled),
        GmailConnector(events=events_for("gmail"), enabled="gmail" in enabled),
    ]

    return run(
        query="Which bugs did we complain about in Slack that never became tickets?",
        context_label=context.label,
        graph=graph,
        connectors=connectors,
        model=RuleBasedTriageModel(),
        policy=ConfigDrivenIntentPolicy(load_default_policy()),
        recorder=InMemoryTraceRecorder(),
    )


def test_full_context_finds_and_grounds_the_complaint() -> None:
    result = run_demo("full")
    assert result.candidate is not None
    assert result.analysis is not None
    assert result.analysis.missing_evidence_sources == []
    assert result.proposal is not None
    assert result.notification is not None
    assert result.notification.sent is True


def test_degraded_context_has_lower_confidence_and_missing_evidence() -> None:
    full = run_demo("full")
    degraded = run_demo("degraded")

    assert degraded.analysis is not None and full.analysis is not None
    assert degraded.analysis.confidence < full.analysis.confidence
    assert degraded.analysis.missing_evidence_sources == ["github", "linear", "gmail"]
    assert len(degraded.analysis.evidence_refs) < len(full.analysis.evidence_refs)

    assert degraded.proposal is not None and full.proposal is not None
    assert degraded.proposal.confidence < full.proposal.confidence


def test_trace_records_all_four_nodes_for_both_contexts() -> None:
    for context_name in ("full", "degraded"):
        result = run_demo(context_name)
        assert [r.node for r in result.trace.records] == [
            "triage",
            "root_cause",
            "fix_proposal",
            "notify",
        ]
