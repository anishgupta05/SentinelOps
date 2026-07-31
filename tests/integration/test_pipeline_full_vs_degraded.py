from sentinelops.demo_runner import run_demo_pipeline

QUERY = "Which bugs did we complain about in Slack that never became tickets?"


def test_full_context_finds_and_grounds_the_complaint() -> None:
    result = run_demo_pipeline("full", QUERY)
    assert result.candidate is not None
    assert result.analysis is not None
    assert result.analysis.missing_evidence_sources == []
    assert result.proposal is not None
    assert result.notification is not None
    assert result.notification.sent is True


def test_degraded_context_has_lower_confidence_and_missing_evidence() -> None:
    full = run_demo_pipeline("full", QUERY)
    degraded = run_demo_pipeline("degraded", QUERY)

    assert degraded.analysis is not None and full.analysis is not None
    assert degraded.analysis.confidence < full.analysis.confidence
    assert degraded.analysis.missing_evidence_sources == ["github", "linear", "gmail"]
    assert len(degraded.analysis.evidence_refs) < len(full.analysis.evidence_refs)

    assert degraded.proposal is not None and full.proposal is not None
    assert degraded.proposal.confidence < full.proposal.confidence


def test_trace_records_all_four_nodes_for_both_contexts() -> None:
    for incident in ("checkout_500", "billing_escalation"):
        for context_name in ("full", "degraded"):
            result = run_demo_pipeline(context_name, QUERY, incident)
            assert [r.node for r in result.trace.records] == [
                "triage",
                "root_cause",
                "fix_proposal",
                "notify",
            ]


def test_billing_escalation_severity_changes_with_missing_evidence() -> None:
    """A second, differently-shaped incident: a low-key internal Slack mention
    only reads as high severity once GitHub's evidence is available - missing
    context changes the *assessment*, not just the confidence number."""
    full = run_demo_pipeline("full", QUERY, "billing_escalation")
    degraded = run_demo_pipeline("degraded", QUERY, "billing_escalation")

    assert full.analysis is not None and degraded.analysis is not None
    assert full.analysis.severity == "high"
    assert degraded.analysis.severity == "low"
    assert degraded.analysis.confidence < full.analysis.confidence
