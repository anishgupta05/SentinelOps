from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from sentinelops.contracts.common import SourceName
from sentinelops.contracts.events import SourceEvent

FIXTURES_DIR = Path(__file__).parent / "fixtures"

INCIDENTS: dict[str, str] = {
    "checkout_500": "Checkout 500 on payment submission",
    "billing_escalation": "Billing overcharge — customer escalation",
}


class DemoContext(BaseModel):
    label: str
    enabled_sources: list[SourceName]


def load_events(incident: str = "checkout_500") -> list[SourceEvent]:
    if incident not in INCIDENTS:
        raise ValueError(f"unknown incident: {incident!r}; choose from {list(INCIDENTS)}")
    data = yaml.safe_load((FIXTURES_DIR / f"events_{incident}.yaml").read_text())
    return [SourceEvent.model_validate(e) for e in data]


def load_context(name: Literal["full", "degraded"]) -> DemoContext:
    data = yaml.safe_load((FIXTURES_DIR / f"context_{name}.yaml").read_text())
    return DemoContext.model_validate(data)
