"""Demo entrypoint for the SentinelOps pipeline."""

import argparse

from sentinelops.demo_data import INCIDENTS
from sentinelops.demo_runner import run_demo_pipeline


def print_demo(context_name: str, query: str, incident: str) -> None:
    result = run_demo_pipeline(context_name, query, incident)

    print(f"=== SentinelOps demo ({result.trace.context_label} context) ===")
    print(f"Incident: {INCIDENTS[incident]}")
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
    demo.add_argument("--incident", choices=list(INCIDENTS), default="checkout_500")
    demo.add_argument("--query", required=True)

    args = parser.parse_args()

    if args.command == "demo":
        print_demo(args.context, args.query, args.incident)


if __name__ == "__main__":
    main()
