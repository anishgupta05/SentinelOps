"""Operator-facing Streamlit view of the SentinelOps pipeline.

Run with: uv run streamlit run app.py
"""

import os

import streamlit as st

from sentinelops.demo_data import INCIDENTS
from sentinelops.demo_runner import run_demo_pipeline
from sentinelops.orchestrator.pipeline import PipelineResult

DEFAULT_QUERY = "Which bugs did we complain about in Slack that never became tickets?"

CONTEXT_LABELS = {
    "full": "Full (Slack + GitHub + Linear + Gmail)",
    "degraded": "Degraded (Slack-only)",
}


def render_trace(result: PipelineResult) -> None:
    st.subheader("Pipeline trace")
    for record in result.trace.records:
        header = record.node
        if record.confidence is not None:
            header += f" — confidence {record.confidence:.2f}"
        with st.expander(header, expanded=True):
            if record.confidence is not None:
                st.progress(record.confidence)
            st.markdown(f"**In:** {record.input_summary}")
            st.markdown(f"**Out:** {record.output_summary}")
            if record.evidence_used:
                st.markdown(f"**Evidence:** {', '.join(record.evidence_used)}")
            st.caption(f"{record.duration_ms:.2f} ms")


def render_outcome(result: PipelineResult) -> None:
    if result.proposal is None:
        st.warning("No unresolved complaint candidate found for this context.")
        return

    st.subheader("Ticket proposal")
    st.markdown(f"**[{result.proposal.mode.upper()}]** {result.proposal.title}")
    st.markdown(
        f"Severity: **{result.proposal.severity}** | "
        f"Confidence: **{result.proposal.confidence:.2f}**"
    )
    st.text(result.proposal.description)

    st.subheader("Notification")
    assert result.notification is not None
    st.markdown(f"**Channel:** {result.notification.channel_ref}")
    st.markdown(f"**Message:** {result.notification.message}")
    st.markdown(f"**Rationale:** {result.notification.rationale}")
    st.markdown(f"**Sent:** {result.notification.sent}")

    if result.rocketride_status is not None:
        st.subheader("RocketRide (live)")
        status = result.rocketride_status
        metrics = status.get("metrics", {})
        tokens = status.get("tokens", {})
        col_status, col_cpu, col_mem, col_tokens = st.columns(4)
        col_status.metric("Status", status.get("status", "n/a"))
        col_cpu.metric("CPU", f"{metrics.get('cpu_percent', 0):.1f}%")
        col_mem.metric("Memory", f"{metrics.get('cpu_memory_mb', 0):.1f} MB")
        col_tokens.metric("Billing tokens", tokens.get("total", 0))


st.set_page_config(page_title="SentinelOps", layout="wide")
st.title("SentinelOps")
st.caption(
    "Finds unresolved Slack complaints, investigates them across GitHub, Linear, "
    "and Gmail, and drafts a grounded Linear ticket."
)

hydra_key_present = bool(os.environ.get("HYDRA_DB_API_KEY"))
rocketride_key_present = bool(
    os.environ.get("ROCKETRIDE_APIKEY") or os.environ.get("ROCKETRIDE_AUTH")
)
with st.sidebar:
    st.header("Settings")
    use_real_hydra = st.checkbox(
        "Use real HydraDB",
        value=False,
        disabled=not hydra_key_present,
        help=(
            "Set HYDRA_DB_API_KEY in the environment to enable this."
            if not hydra_key_present
            else "Routes graph ingestion and entity resolution through the live "
            "HydraDB API instead of the local mock. Each run makes real network "
            "calls, so it's slower."
        ),
    )
    use_real_rocketride = st.checkbox(
        "Publish to RocketRide",
        value=False,
        disabled=not rocketride_key_present,
        help=(
            "Set ROCKETRIDE_APIKEY in the environment to enable this."
            if not rocketride_key_present
            else "Publishes the finished result through a real RocketRide-hosted "
            "pipeline and shows the engine's live task status. Does not run "
            "SentinelOps' own reasoning on RocketRide - see rocketride_live.py."
        ),
    )

tab_run, tab_compare = st.tabs(["Run", "Full vs Degraded"])

with tab_run:
    col_query, col_incident, col_context = st.columns([3, 2, 2])
    query = col_query.text_input("Query", value=DEFAULT_QUERY)
    incident = col_incident.selectbox(
        "Incident", options=list(INCIDENTS), format_func=lambda i: INCIDENTS[i]
    )
    context_name = col_context.selectbox(
        "Context", options=["full", "degraded"], format_func=lambda c: CONTEXT_LABELS[c]
    )

    if st.button("Run pipeline", type="primary"):
        st.session_state["run_result"] = run_demo_pipeline(
            context_name,
            query,
            incident,
            use_real_hydra=use_real_hydra,
            use_real_rocketride=use_real_rocketride,
        )

    result = st.session_state.get("run_result")
    if result is not None:
        render_trace(result)
        render_outcome(result)

with tab_compare:
    st.write(
        "Runs the same query against full and degraded context side by side — "
        "the demo's core visual: confidence and grounding drop when GitHub, "
        "Linear, and Gmail become unavailable."
    )
    col_compare_query, col_compare_incident = st.columns([3, 2])
    compare_query = col_compare_query.text_input(
        "Query", value=DEFAULT_QUERY, key="compare_query"
    )
    compare_incident = col_compare_incident.selectbox(
        "Incident",
        options=list(INCIDENTS),
        format_func=lambda i: INCIDENTS[i],
        key="compare_incident",
    )

    if st.button("Compare contexts", type="primary"):
        st.session_state["compare_result"] = (
            run_demo_pipeline(
                "full",
                compare_query,
                compare_incident,
                use_real_hydra=use_real_hydra,
                use_real_rocketride=use_real_rocketride,
            ),
            run_demo_pipeline(
                "degraded",
                compare_query,
                compare_incident,
                use_real_hydra=use_real_hydra,
                use_real_rocketride=use_real_rocketride,
            ),
        )

    compare = st.session_state.get("compare_result")
    if compare is not None:
        full_result, degraded_result = compare

        if full_result.analysis is not None and degraded_result.analysis is not None:
            full_confidence = full_result.analysis.confidence
            degraded_confidence = degraded_result.analysis.confidence
            metric_full, metric_degraded = st.columns(2)
            metric_full.metric(
                "Full context confidence",
                f"{full_confidence:.2f}",
                help=f"Severity: {full_result.analysis.severity}",
            )
            metric_degraded.metric(
                "Degraded context confidence",
                f"{degraded_confidence:.2f}",
                delta=f"{degraded_confidence - full_confidence:.2f}",
                help=f"Severity: {degraded_result.analysis.severity}",
            )
            if full_result.analysis.severity != degraded_result.analysis.severity:
                st.info(
                    f"Severity assessment also changes: **{degraded_result.analysis.severity}** "
                    f"(degraded) vs **{full_result.analysis.severity}** (full) — missing evidence "
                    f"changed the read on how bad this is, not just how confident."
                )

        col_full, col_degraded = st.columns(2)
        with col_full:
            st.header(CONTEXT_LABELS["full"])
            render_trace(full_result)
            render_outcome(full_result)
        with col_degraded:
            st.header(CONTEXT_LABELS["degraded"])
            render_trace(degraded_result)
            render_outcome(degraded_result)
