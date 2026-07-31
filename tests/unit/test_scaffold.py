import importlib

import sentinelops


def test_package_imports() -> None:
    assert importlib.import_module("sentinelops") is sentinelops


def test_subpackages_import() -> None:
    for name in [
        "contracts",
        "graph",
        "reasoning",
        "connectors",
        "policy",
        "nodes",
        "orchestrator",
    ]:
        importlib.import_module(f"sentinelops.{name}")
