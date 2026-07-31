"""Real InsForge-backed audit log for intent policy decisions, for
`pip install httpx`.

Confirmed against a live InsForge project rather than guessed. This talks to
the REST API directly with `httpx` instead of the `insforge` pip package: the
installed SDK (v0.1.0) serializes `create_table` columns with different field
names (`name`/`nullable`/`unique`) than this live server actually validates
(`columnName`/`isNullable`/`isUnique`) - confirmed by testing both against the
real API. `httpx` sidesteps that version drift.

InsForge is a general-purpose backend platform (Postgres database, auth,
storage, functions) at a project-specific subdomain, not an "intent policy"
service - there's no InsForge endpoint that could implement `decide()`'s
domain-specific logic for us. What's genuinely real here is durable storage:
every `IntentPolicyDecision` is written to a real Postgres table via
InsForge's REST API, so the intent boundary CLAUDE.md describes is an
inspectable audit trail rather than something that only ever lived in
process memory. Decision logic itself stays local and deterministic (see
`policy/insforge.py`).
"""

import os
import time

from sentinelops.contracts.common import Severity, SourceName
from sentinelops.contracts.policy import IntentPolicyDecision, PolicyAction
from sentinelops.policy.config import PolicyConfig
from sentinelops.policy.insforge import ConfigDrivenIntentPolicy

_TABLE = "sentinelops_policy_decisions"
_COLUMNS = [
    {"columnName": "decision_id", "type": "string", "isNullable": False, "isUnique": True},
    {"columnName": "action", "type": "string", "isNullable": False, "isUnique": False},
    {"columnName": "allowed", "type": "boolean", "isNullable": False, "isUnique": False},
    {"columnName": "reason", "type": "string", "isNullable": True, "isUnique": False},
    {"columnName": "matched_rule", "type": "string", "isNullable": True, "isUnique": False},
    {
        "columnName": "required_evidence_met",
        "type": "boolean",
        "isNullable": False,
        "isUnique": False,
    },
]


class AuditedIntentPolicy:
    """Drop-in replacement for `ConfigDrivenIntentPolicy` that also writes
    every decision to a real InsForge-hosted Postgres table."""

    def __init__(self, config: PolicyConfig, base_url: str, api_key: str | None = None) -> None:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "AuditedIntentPolicy requires httpx: pip install httpx"
            ) from exc

        api_key = api_key or os.environ.get("INSFORGE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "AuditedIntentPolicy needs a key: set INSFORGE_API_KEY or pass api_key=..."
            )

        self._local = ConfigDrivenIntentPolicy(config)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )
        self.last_audit_row: dict | None = None
        self._ensure_table()

    def _ensure_table(self) -> None:
        response = self._http.get("/api/database/tables")
        response.raise_for_status()
        if _TABLE in response.json():
            return
        response = self._http.post(
            "/api/database/tables",
            json={"tableName": _TABLE, "columns": _COLUMNS},
        )
        if response.status_code >= 400 and "already exists" not in response.text.lower():
            response.raise_for_status()
        self._wait_until_queryable()

    def _wait_until_queryable(self, timeout_s: float = 20.0) -> None:
        """Table creation returns before the table is actually queryable -
        confirmed live: an insert immediately after a 201 create can 404. Poll
        until reads succeed."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            response = self._http.get(f"/api/database/records/{_TABLE}", params={"limit": 1})
            if response.status_code == 200:
                return
            time.sleep(1)
        raise TimeoutError(f"InsForge table {_TABLE!r} did not become queryable in time")

    def decide(
        self,
        action: PolicyAction,
        *,
        severity: Severity,
        confidence: float,
        evidence_sources: list[SourceName],
        assignee: str | None = None,
    ) -> IntentPolicyDecision:
        decision = self._local.decide(
            action,
            severity=severity,
            confidence=confidence,
            evidence_sources=evidence_sources,
            assignee=assignee,
        )
        row = {
            "decision_id": decision.id,
            "action": decision.action,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "matched_rule": decision.matched_rule,
            "required_evidence_met": decision.required_evidence_met,
        }
        response = self._http.post(f"/api/database/records/{_TABLE}", json=[row])
        response.raise_for_status()
        self.last_audit_row = row
        return decision

    def close(self) -> None:
        self._http.close()
