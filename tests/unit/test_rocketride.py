import pytest

from sentinelops.orchestrator.rocketride import InMemoryTraceRecorder


def test_record_captures_node_span_into_trace() -> None:
    recorder = InMemoryTraceRecorder()
    recorder.start_trace(query="which bugs never became tickets?", context_label="full")

    with recorder.record("triage", input_summary="scan graph", evidence_used=["s1"]) as span:
        span.output_summary = "1 candidate found"
        span.confidence = 0.8

    trace = recorder.trace
    assert trace.query == "which bugs never became tickets?"
    assert len(trace.records) == 1
    record = trace.records[0]
    assert record.node == "triage"
    assert record.output_summary == "1 candidate found"
    assert record.confidence == 0.8
    assert record.evidence_used == ["s1"]
    assert record.duration_ms >= 0


def test_record_without_start_trace_raises() -> None:
    recorder = InMemoryTraceRecorder()
    with pytest.raises(RuntimeError):
        with recorder.record("triage", input_summary="scan graph"):
            pass
