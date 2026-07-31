from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any, Protocol

from pydantic import BaseModel, Field


class NodeTraceRecord(BaseModel):
    """One node's execution as it would show up in a RocketRide trace view."""

    node: str
    input_summary: str
    output_summary: str
    confidence: float | None = None
    evidence_used: list[str] = Field(default_factory=list)
    duration_ms: float


class PipelineTrace(BaseModel):
    """Full record of a pipeline run, in node-execution order."""

    query: str
    context_label: str
    records: list[NodeTraceRecord] = Field(default_factory=list)


class TraceRecorder(Protocol):
    """Observability seam a real RocketRide hosting layer would implement.
    Every node execution goes through this so degraded-context runs are provably
    less grounded in the trace, not just in the final text."""

    def start_trace(self, query: str, context_label: str) -> None: ...

    def record(
        self, node: str, *, input_summary: str, evidence_used: list[str] | None = None
    ) -> Any: ...

    @property
    def trace(self) -> PipelineTrace: ...


class InMemoryTraceRecorder:
    """Local mock of RocketRide's trace/observability layer."""

    def __init__(self) -> None:
        self._trace: PipelineTrace | None = None

    def start_trace(self, query: str, context_label: str) -> None:
        self._trace = PipelineTrace(query=query, context_label=context_label)

    @contextmanager
    def record(
        self, node: str, *, input_summary: str, evidence_used: list[str] | None = None
    ) -> Iterator["_NodeSpan"]:
        if self._trace is None:
            raise RuntimeError("start_trace() must be called before record()")
        span = _NodeSpan(node=node, input_summary=input_summary, evidence_used=evidence_used or [])
        start = perf_counter()
        try:
            yield span
        finally:
            duration_ms = (perf_counter() - start) * 1000
            self._trace.records.append(
                NodeTraceRecord(
                    node=node,
                    input_summary=input_summary,
                    output_summary=span.output_summary,
                    confidence=span.confidence,
                    evidence_used=span.evidence_used,
                    duration_ms=round(duration_ms, 3),
                )
            )

    @property
    def trace(self) -> PipelineTrace:
        if self._trace is None:
            raise RuntimeError("start_trace() must be called before reading trace")
        return self._trace


class _NodeSpan:
    """Mutable handle a node fills in while inside a `record()` block."""

    def __init__(self, node: str, input_summary: str, evidence_used: list[str]) -> None:
        self.node = node
        self.input_summary = input_summary
        self.evidence_used = evidence_used
        self.output_summary = ""
        self.confidence: float | None = None
