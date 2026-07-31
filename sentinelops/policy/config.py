from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from sentinelops.contracts.common import Confidence, Severity, SourceName


class PolicyConfig(BaseModel):
    """InsForge-style intent policy, kept as data so it can be audited and changed
    without touching model or node code. Dimensions per CLAUDE.md's Safety section."""

    allowed_channels: list[str] = Field(default_factory=lambda: ["*"])
    allowed_repos: list[str] = Field(default_factory=lambda: ["*"])
    auto_file: bool = False
    min_confidence_to_file: Confidence = 0.8
    min_confidence_to_escalate: Confidence = 0.7
    severity_escalation_threshold: Severity = "high"
    allowed_assignees: list[str] = Field(default_factory=list)
    required_evidence_sources: list[SourceName] = Field(default_factory=lambda: ["slack"])

    @classmethod
    def from_yaml(cls, path: Path) -> "PolicyConfig":
        data = yaml.safe_load(path.read_text()) or {}
        return cls.model_validate(data)


DEFAULT_POLICY_PATH = Path(__file__).parent / "default_policy.yaml"


def load_default_policy() -> PolicyConfig:
    return PolicyConfig.from_yaml(DEFAULT_POLICY_PATH)
