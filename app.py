"""Operator-facing Streamlit view of the SentinelOps pipeline.

Run with: uv run streamlit run app.py
"""

import streamlit as st

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


st.set_page_config(page_title="SentinelOps", layout="wide")
st.title("SentinelOps")
st.caption(
    "Finds unresolved Slack complaints, investigates them across GitHub, Linear, "
    "and Gmail, and drafts a grounded Linear ticket."
)

tab_run, tab_compare = st.tabs(["Run", "Full vs Degraded"])

with tab_run:
    col_query, col_context = st.columns([3, 1])
    query = col_query.text_input("Query", value=DEFAULT_QUERY)
    context_name = col_context.selectbox(
        "Context", options=["full", "degraded"], format_func=lambda c: CONTEXT_LABELS[c]
    )

    if st.button("Run pipeline", type="primary"):
        st.session_state["run_result"] = run_demo_pipeline(context_name, query)

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
    compare_query = st.text_input("Query", value=DEFAULT_QUERY, key="compare_query")

    if st.button("Compare contexts", type="primary"):
        st.session_state["compare_result"] = (
            run_demo_pipeline("full", compare_query),
            run_demo_pipeline("degraded", compare_query),
        )

    compare = st.session_state.get("compare_result")
    if compare is not None:
        full_result, degraded_result = compare

        if full_result.analysis is not None and degraded_result.analysis is not None:
            full_confidence = full_result.analysis.confidence
            degraded_confidence = degraded_result.analysis.confidence
            metric_full, metric_degraded = st.columns(2)
            metric_full.metric("Full context confidence", f"{full_confidence:.2f}")
            metric_degraded.metric(
                "Degraded context confidence",
                f"{degraded_confidence:.2f}",
                delta=f"{degraded_confidence - full_confidence:.2f}",
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
