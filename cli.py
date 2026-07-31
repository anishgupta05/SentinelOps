"""Demo entrypoint for the SentinelOps pipeline. Wired up in M4."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinelops")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the pipeline against a fixture context")
    demo.add_argument("--context", choices=["full", "degraded"], default="full")
    demo.add_argument("--query", required=True)

    args = parser.parse_args()

    if args.command == "demo":
        raise NotImplementedError("Pipeline orchestrator lands in M4")


if __name__ == "__main__":
    main()
