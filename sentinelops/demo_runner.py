import os

from sentinelops.connectors import GitHubConnector, GmailConnector, LinearConnector, SlackConnector
from sentinelops.connectors.base import SourceConnector
from sentinelops.contracts.events import SourceEvent
from sentinelops.demo_data import DemoContext, load_context, load_events
from sentinelops.graph.hydra import ContextGraph, InMemoryHydraGraph
from sentinelops.orchestrator.pipeline import PipelineResult, run
from sentinelops.orchestrator.rocketride import InMemoryTraceRecorder
from sentinelops.policy.config import load_default_policy
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy, IntentPolicy
from sentinelops.reasoning.pipeshift import RuleBasedTriageModel


def build_pipeline_inputs(
    context_name: str, incident: str = "checkout_500", *, use_real_hydra: bool = False
) -> tuple[ContextGraph, list[SourceConnector], DemoContext]:
    """Wire an incident fixture into a graph + connectors for the given context.
    Both the CLI and the Streamlit app run through this so full vs degraded, and
    which incident is loaded, stay defined in exactly one place.

    `use_real_hydra=True` swaps the local mock for the real HydraDB API (needs
    `HYDRA_DB_API_KEY` set) - node logic is unaffected either way, since both
    implement the same `ContextGraph` interface."""
    context = load_context(context_name)
    all_events = load_events(incident)
    enabled = set(context.enabled_sources)

    graph: ContextGraph
    if use_real_hydra:
        from sentinelops.graph.hydra_live import HydraDBClient

        graph = HydraDBClient(database="sentinelops_demo")
    else:
        graph = InMemoryHydraGraph()
    graph.ingest([e for e in all_events if e.source in enabled])

    def events_for(source: str) -> list[SourceEvent]:
        return [e for e in all_events if e.source == source]

    connectors: list[SourceConnector] = [
        SlackConnector(events=events_for("slack"), enabled="slack" in enabled),
        GitHubConnector(events=events_for("github"), enabled="github" in enabled),
        LinearConnector(events=events_for("linear"), enabled="linear" in enabled),
        GmailConnector(events=events_for("gmail"), enabled="gmail" in enabled),
    ]
    return graph, connectors, context


def _rocketride_payload(result: PipelineResult, query: str, context_label: str) -> dict:
    return {
        "query": query,
        "context": context_label,
        "candidate_summary": result.candidate.summary if result.candidate else None,
        "severity": result.analysis.severity if result.analysis else None,
        "confidence": result.analysis.confidence if result.analysis else None,
        "ticket_mode": result.proposal.mode if result.proposal else None,
        "notification_message": result.notification.message if result.notification else None,
    }


def _build_policy(use_real_insforge: bool) -> IntentPolicy:
    config = load_default_policy()
    if not use_real_insforge:
        return ConfigDrivenIntentPolicy(config)

    from sentinelops.policy.insforge_live import AuditedIntentPolicy

    base_url = os.environ.get("INSFORGE_BASE_URL")
    if not base_url:
        raise RuntimeError("use_real_insforge requires INSFORGE_BASE_URL to be set")
    return AuditedIntentPolicy(config, base_url=base_url)


def run_demo_pipeline(
    context_name: str,
    query: str,
    incident: str = "checkout_500",
    *,
    use_real_hydra: bool = False,
    use_real_rocketride: bool = False,
    use_real_insforge: bool = False,
) -> PipelineResult:
    graph, connectors, context = build_pipeline_inputs(
        context_name, incident, use_real_hydra=use_real_hydra
    )
    policy = _build_policy(use_real_insforge)
    result = run(
        query=query,
        context_label=context.label,
        graph=graph,
        connectors=connectors,
        model=RuleBasedTriageModel(),
        policy=policy,
        recorder=InMemoryTraceRecorder(),
    )

    result.insforge_audit_row = getattr(policy, "last_audit_row", None)

    if use_real_rocketride:
        from sentinelops.orchestrator.rocketride_live import publish_result

        result.rocketride_status = publish_result(
            _rocketride_payload(result, query, context.label)
        )

    return result
