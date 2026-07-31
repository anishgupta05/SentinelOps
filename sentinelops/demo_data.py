from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from sentinelops.contracts.common import SourceName
from sentinelops.contracts.events import SourceEvent

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DemoContext(BaseModel):
    label: str
    enabled_sources: list[SourceName]


def load_events() -> list[SourceEvent]:
    data = yaml.safe_load((FIXTURES_DIR / "events.yaml").read_text())
    return [SourceEvent.model_validate(e) for e in data]


def load_context(name: Literal["full", "degraded"]) -> DemoContext:
    data = yaml.safe_load((FIXTURES_DIR / f"context_{name}.yaml").read_text())
    return DemoContext.model_validate(data)
