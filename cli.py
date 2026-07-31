"""Demo entrypoint for the SentinelOps pipeline."""

import argparse

from sentinelops.connectors import GitHubConnector, GmailConnector, LinearConnector, SlackConnector
from sentinelops.contracts.events import SourceEvent
from sentinelops.demo_data import load_context, load_events
from sentinelops.graph.hydra import InMemoryHydraGraph
from sentinelops.orchestrator.pipeline import run
from sentinelops.orchestrator.rocketride import InMemoryTraceRecorder
from sentinelops.policy.config import load_default_policy
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy
from sentinelops.reasoning.pipeshift import RuleBasedTriageModel


def run_demo(context_name: str, query: str) -> None:
    context = load_context(context_name)
    all_events = load_events()
    enabled = set(context.enabled_sources)

    graph = InMemoryHydraGraph()
    graph.ingest([e for e in all_events if e.source in enabled])

    def events_for(source: str) -> list[SourceEvent]:
        return [e for e in all_events if e.source == source]

    connectors = [
        SlackConnector(events=events_for("slack"), enabled="slack" in enabled),
        GitHubConnector(events=events_for("github"), enabled="github" in enabled),
        LinearConnector(events=events_for("linear"), enabled="linear" in enabled),
        GmailConnector(events=events_for("gmail"), enabled="gmail" in enabled),
    ]

    result = run(
        query=query,
        context_label=context.label,
        graph=graph,
        connectors=connectors,
        model=RuleBasedTriageModel(),
        policy=ConfigDrivenIntentPolicy(load_default_policy()),
        recorder=InMemoryTraceRecorder(),
    )

    print(f"=== SentinelOps demo ({context.label} context) ===")
    print(f"Query: {query}\n")

    print("--- Trace ---")
    for record in result.trace.records:
        confidence = f"{record.confidence:.2f}" if record.confidence is not None else "n/a"
        print(f"[{record.node}] confidence={confidence} ({record.duration_ms:.2f}ms)")
        print(f"  in:  {record.input_summary}")
        print(f"  out: {record.output_summary}")
        if record.evidence_used:
            print(f"  evidence: {', '.join(record.evidence_used)}")
    print()

    if result.proposal is None:
        print("No unresolved complaint candidate found.")
        return

    print("--- Ticket Proposal ---")
    print(f"[{result.proposal.mode.upper()}] {result.proposal.title}")
    print(f"Severity: {result.proposal.severity} | Confidence: {result.proposal.confidence:.2f}")
    print(result.proposal.description)
    print()

    print("--- Notification ---")
    assert result.notification is not None
    print(f"Channel: {result.notification.channel_ref}")
    print(f"Message: {result.notification.message}")
    print(f"Rationale: {result.notification.rationale}")
    print(f"Sent: {result.notification.sent}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinelops")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the pipeline against a fixture context")
    demo.add_argument("--context", choices=["full", "degraded"], default="full")
    demo.add_argument("--query", required=True)

    args = parser.parse_args()

    if args.command == "demo":
        run_demo(args.context, args.query)


if __name__ == "__main__":
    main()
