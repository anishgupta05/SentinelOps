"""Operator-facing Streamlit view of the SentinelOps pipeline.

Run with: uv run streamlit run app.py
"""

import os
from html import escape

import streamlit as st

from sentinelops.demo_data import INCIDENTS
from sentinelops.demo_runner import run_demo_pipeline
from sentinelops.orchestrator.pipeline import PipelineResult

DEFAULT_QUERY = "Which bugs did we complain about in Slack that never became tickets?"

CONTEXT_LABELS = {
    "full": "Full (Slack + GitHub + Linear + Gmail)",
    "degraded": "Degraded (Slack-only)",
}

# Status roles are fixed and never carry meaning from color alone - every badge
# pairs the color with a text label. See references/palette.md in the dataviz
# skill for the source values.
STATUS_COLOR = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}
STATUS_TEXT_ON = {
    "good": "#ffffff",
    "warning": "#3d2c00",
    "serious": "#ffffff",
    "critical": "#ffffff",
}
SEVERITY_STATUS = {"low": "good", "medium": "warning", "high": "serious", "critical": "critical"}

CSS = """
<style>
/* Streamlit's theme (light, pinned in .streamlit/config.toml) drives
   --secondary-background-color / --text-color at runtime, including if the
   viewer flips Streamlit's own Light/Dark toggle. Everything below reads
   those - not the OS prefers-color-scheme - so custom cards never mismatch
   the native chrome around them. */
:root {
  --so-border: rgba(11,11,11,0.10);
  --so-muted: #52514e;
  --so-card-bg: var(--secondary-background-color, #f0efec);
  --so-accent: #2a78d6;
  --so-track: #e1e0d9;
}
.so-section-title {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--so-muted);
  margin: 18px 0 8px 0;
}
.so-hero {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin: 4px 0 18px 0;
}
.so-hero-step {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--so-muted);
  padding: 4px 10px;
  border: 1px solid var(--so-border);
  border-radius: 999px;
}
.so-hero-arrow {
  color: var(--so-muted);
  font-size: 0.8rem;
}
.so-card {
  background: var(--so-card-bg);
  border: 1px solid var(--so-border);
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 10px;
}
.so-card-live {
  border-left: 3px solid #4a3aa7;
}
.so-step-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.so-step-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-color, #0b0b0b);
}
.so-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--so-accent);
  color: #ffffff;
  font-size: 0.72rem;
  font-weight: 700;
  flex-shrink: 0;
}
.so-duration {
  color: var(--so-muted);
  font-size: 0.76rem;
  white-space: nowrap;
}
.so-meter-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0 6px 0;
}
.so-meter-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: var(--so-track);
  overflow: hidden;
}
.so-meter-fill {
  height: 100%;
  border-radius: 4px;
}
.so-meter-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--so-muted);
  min-width: 36px;
  text-align: right;
}
.so-body-text {
  font-size: 0.85rem;
  line-height: 1.55;
  margin: 3px 0;
  color: var(--text-color, #0b0b0b);
}
.so-body-label {
  color: var(--so-muted);
  font-weight: 700;
  margin-right: 5px;
}
.so-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.so-chip {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.7rem;
  background: var(--so-track);
  color: var(--so-muted);
  padding: 2px 8px;
  border-radius: 999px;
}
.so-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  white-space: nowrap;
}
.so-title-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.so-proposal-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-color, #0b0b0b);
}
.so-stat-label {
  color: var(--so-muted);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.so-stat-value {
  font-size: 2.1rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--text-color, #0b0b0b);
}
.so-stat-sub {
  font-size: 0.78rem;
  color: var(--so-muted);
  margin-top: 2px;
}
</style>
"""


def status_for_confidence(value: float) -> str:
    if value >= 0.8:
        return "good"
    if value >= 0.6:
        return "warning"
    if value >= 0.4:
        return "serious"
    return "critical"


def render_badge(text: str, status: str) -> str:
    return (
        f'<span class="so-badge" style="background:{STATUS_COLOR[status]};'
        f'color:{STATUS_TEXT_ON[status]};">● {escape(text)}</span>'
    )


def render_meter(value: float) -> str:
    color = STATUS_COLOR[status_for_confidence(value)]
    pct = max(0.0, min(1.0, value)) * 100
    return (
        '<div class="so-meter-row">'
        f'<div class="so-meter-track"><div class="so-meter-fill" '
        f'style="width:{pct:.0f}%;background:{color};"></div></div>'
        f'<div class="so-meter-label">{value:.2f}</div>'
        "</div>"
    )


def render_labeled(label: str, text: str) -> str:
    return (
        f'<div class="so-body-text"><span class="so-body-label">{label}</span>'
        f'{escape(text)}</div>'
    )


def render_stat_tile(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="so-stat-sub">{escape(sub)}</div>' if sub else ""
    return (
        '<div class="so-card">'
        f'<div class="so-stat-label">{escape(label)}</div>'
        f'<div class="so-stat-value">{escape(value)}</div>'
        f"{sub_html}"
        "</div>"
    )


def render_trace(result: PipelineResult) -> None:
    st.markdown('<div class="so-section-title">Pipeline trace</div>', unsafe_allow_html=True)
    for i, record in enumerate(result.trace.records, start=1):
        if record.confidence is not None:
            meter_html = render_meter(record.confidence)
        else:
            meter_html = (
                '<div class="so-body-text" style="color:var(--so-muted);">no candidate</div>'
            )

        evidence_html = ""
        if record.evidence_used:
            chips = "".join(
                f'<span class="so-chip">{escape(e)}</span>' for e in record.evidence_used
            )
            evidence_html = f'<div class="so-chip-row">{chips}</div>'

        node_label = record.node.replace("_", " ").title()
        in_html = render_labeled("In", record.input_summary)
        out_html = render_labeled("Out", record.output_summary)
        st.markdown(
            f"""
            <div class="so-card">
              <div class="so-step-head">
                <div class="so-step-title">
                  <span class="so-step-index">{i}</span>{escape(node_label)}
                </div>
                <div class="so-duration">{record.duration_ms:.2f} ms</div>
              </div>
              {meter_html}
              {in_html}
              {out_html}
              {evidence_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_outcome(result: PipelineResult) -> None:
    if result.proposal is None:
        st.markdown(
            '<div class="so-card">No unresolved complaint candidate found for this context.</div>',
            unsafe_allow_html=True,
        )
        return

    proposal = result.proposal
    mode_badge = render_badge(proposal.mode, "good" if proposal.mode == "filed" else "warning")
    severity_badge = render_badge(proposal.severity, SEVERITY_STATUS[proposal.severity])

    st.markdown('<div class="so-section-title">Ticket proposal</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="so-card">
          <div class="so-step-head">
            <div class="so-proposal-title">{escape(proposal.title)}</div>
            <div class="so-title-row">{mode_badge}{severity_badge}</div>
          </div>
          {render_meter(proposal.confidence)}
          <div class="so-body-text" style="white-space:pre-line;color:var(--so-muted);">
            {escape(proposal.description)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    notification = result.notification
    assert notification is not None
    sent_badge = render_badge(
        "sent" if notification.sent else "not sent", "good" if notification.sent else "warning"
    )
    st.markdown('<div class="so-section-title">Notification</div>', unsafe_allow_html=True)
    message_html = render_labeled("Message", notification.message)
    rationale_html = render_labeled("Rationale", notification.rationale)
    st.markdown(
        f"""
        <div class="so-card">
          <div class="so-step-head">
            <div class="so-proposal-title">{escape(notification.channel_ref)}</div>
            {sent_badge}
          </div>
          {message_html}
          {rationale_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result.rocketride_status is not None:
        status = result.rocketride_status
        metrics = status.get("metrics", {})
        tokens = status.get("tokens", {})
        status_html = render_labeled("Status", str(status.get("status", "n/a")))
        metrics_text = (
            f"{metrics.get('cpu_percent', 0):.1f}% CPU · "
            f"{metrics.get('cpu_memory_mb', 0):.1f} MB memory · "
            f"{tokens.get('total', 0)} billing tokens"
        )
        metrics_html = render_labeled("Usage", metrics_text)
        st.markdown('<div class="so-section-title">RocketRide (live)</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="so-card so-card-live">
              {status_html}
              {metrics_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if result.insforge_audit_row is not None:
        row = result.insforge_audit_row
        allowed = bool(row.get("allowed"))
        action_status = "good" if allowed else "warning"
        action_badge = render_badge("allowed" if allowed else "blocked", action_status)
        action_html = render_labeled("Action", str(row.get("action", "n/a")))
        reason_html = render_labeled("Reason", str(row.get("reason", "")))
        st.markdown(
            '<div class="so-section-title">InsForge (live audit)</div>', unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div class="so-card so-card-live">
              <div class="so-step-head">{action_html}{action_badge}</div>
              {reason_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="SentinelOps", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

st.title("SentinelOps")
st.caption(
    "Finds unresolved Slack complaints, investigates them across GitHub, Linear, "
    "and Gmail, and drafts a grounded Linear ticket."
)
st.markdown(
    """
    <div class="so-hero">
      <span class="so-hero-step">1 Triage</span><span class="so-hero-arrow">&rarr;</span>
      <span class="so-hero-step">2 Root cause</span><span class="so-hero-arrow">&rarr;</span>
      <span class="so-hero-step">3 Fix proposal</span><span class="so-hero-arrow">&rarr;</span>
      <span class="so-hero-step">4 Notify</span>
    </div>
    """,
    unsafe_allow_html=True,
)

hydra_key_present = bool(os.environ.get("HYDRA_DB_API_KEY"))
rocketride_key_present = bool(
    os.environ.get("ROCKETRIDE_APIKEY") or os.environ.get("ROCKETRIDE_AUTH")
)
insforge_configured = bool(
    os.environ.get("INSFORGE_API_KEY") and os.environ.get("INSFORGE_BASE_URL")
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
    use_real_insforge = st.checkbox(
        "Audit to InsForge",
        value=False,
        disabled=not insforge_configured,
        help=(
            "Set INSFORGE_API_KEY and INSFORGE_BASE_URL in the environment to "
            "enable this."
            if not insforge_configured
            else "Persists every intent policy decision to a real InsForge-hosted "
            "Postgres table. Decision logic stays local - see insforge_live.py."
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
            use_real_insforge=use_real_insforge,
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
                use_real_insforge=use_real_insforge,
            ),
            run_demo_pipeline(
                "degraded",
                compare_query,
                compare_incident,
                use_real_hydra=use_real_hydra,
                use_real_rocketride=use_real_rocketride,
                use_real_insforge=use_real_insforge,
            ),
        )

    compare = st.session_state.get("compare_result")
    if compare is not None:
        full_result, degraded_result = compare

        if full_result.analysis is not None and degraded_result.analysis is not None:
            full_confidence = full_result.analysis.confidence
            degraded_confidence = degraded_result.analysis.confidence
            delta = degraded_confidence - full_confidence
            metric_full, metric_degraded = st.columns(2)
            metric_full.markdown(
                render_stat_tile(
                    "Full context confidence",
                    f"{full_confidence:.2f}",
                    f"severity: {full_result.analysis.severity}",
                ),
                unsafe_allow_html=True,
            )
            metric_degraded.markdown(
                render_stat_tile(
                    "Degraded context confidence",
                    f"{degraded_confidence:.2f}",
                    f"{delta:+.2f} vs full · severity: {degraded_result.analysis.severity}",
                ),
                unsafe_allow_html=True,
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
