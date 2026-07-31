from sentinelops.connectors import GitHubConnector, GmailConnector, LinearConnector, SlackConnector
from sentinelops.connectors.base import SourceConnector
from sentinelops.contracts.events import SourceEvent
from sentinelops.demo_data import DemoContext, load_context, load_events
from sentinelops.graph.hydra import InMemoryHydraGraph
from sentinelops.orchestrator.pipeline import PipelineResult, run
from sentinelops.orchestrator.rocketride import InMemoryTraceRecorder
from sentinelops.policy.config import load_default_policy
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy
from sentinelops.reasoning.pipeshift import RuleBasedTriageModel


def build_pipeline_inputs(
    context_name: str,
) -> tuple[InMemoryHydraGraph, list[SourceConnector], DemoContext]:
    """Wire the shared incident fixture into a graph + connectors for the given
    context. Both the CLI and the Streamlit app run through this so full vs
    degraded stays defined in exactly one place."""
    context = load_context(context_name)
    all_events = load_events()
    enabled = set(context.enabled_sources)

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


def run_demo_pipeline(context_name: str, query: str) -> PipelineResult:
    graph, connectors, context = build_pipeline_inputs(context_name)
    return run(
        query=query,
        context_label=context.label,
        graph=graph,
        connectors=connectors,
        model=RuleBasedTriageModel(),
        policy=ConfigDrivenIntentPolicy(load_default_policy()),
        recorder=InMemoryTraceRecorder(),
    )
