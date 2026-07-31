"""Demo entrypoint for the SentinelOps pipeline."""

import argparse

from sentinelops.demo_data import INCIDENTS
from sentinelops.demo_runner import run_demo_pipeline


def print_demo(
    context_name: str,
    query: str,
    incident: str,
    *,
    use_real_hydra: bool,
    use_real_rocketride: bool,
    use_real_insforge: bool,
) -> None:
    result = run_demo_pipeline(
        context_name,
        query,
        incident,
        use_real_hydra=use_real_hydra,
        use_real_rocketride=use_real_rocketride,
        use_real_insforge=use_real_insforge,
    )

    print(f"=== SentinelOps demo ({result.trace.context_label} context) ===")
    print(f"Incident: {INCIDENTS[incident]}")
    print(f"Graph backend: {'HydraDB (live)' if use_real_hydra else 'mock'}")
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

    if result.rocketride_status is not None:
        print()
        print("--- RocketRide (live) ---")
        print(f"Status: {result.rocketride_status.get('status')}")
        metrics = result.rocketride_status.get("metrics", {})
        print(f"CPU: {metrics.get('cpu_percent')}% | Memory: {metrics.get('cpu_memory_mb'):.1f}MB")
        tokens = result.rocketride_status.get("tokens", {})
        print(f"Billing tokens: {tokens.get('total')}")

    if result.insforge_audit_row is not None:
        print()
        print("--- InsForge (live audit) ---")
        print(f"Persisted decision: {result.insforge_audit_row}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinelops")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the pipeline against a fixture context")
    demo.add_argument("--context", choices=["full", "degraded"], default="full")
    demo.add_argument("--incident", choices=list(INCIDENTS), default="checkout_500")
    demo.add_argument("--query", required=True)
    demo.add_argument(
        "--graph-backend",
        choices=["mock", "hydradb"],
        default="mock",
        help="'hydradb' uses the real API (needs HYDRA_DB_API_KEY set)",
    )
    demo.add_argument(
        "--publish-rocketride",
        action="store_true",
        help="Also publish the result through a real RocketRide-hosted pipeline "
        "(needs ROCKETRIDE_APIKEY set)",
    )
    demo.add_argument(
        "--audit-insforge",
        action="store_true",
        help="Also persist the policy decision to a real InsForge-hosted audit "
        "table (needs INSFORGE_API_KEY and INSFORGE_BASE_URL set)",
    )

    args = parser.parse_args()

    if args.command == "demo":
        print_demo(
            args.context,
            args.query,
            args.incident,
            use_real_hydra=args.graph_backend == "hydradb",
            use_real_rocketride=args.publish_rocketride,
            use_real_insforge=args.audit_insforge,
        )


if __name__ == "__main__":
    main()
