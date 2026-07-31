# SentinelOps — Demo Video Script

Target length: ~3:00. Cut the "Real integrations" section (marked optional) to land closer to 90 seconds if your hackathon has a hard cap.

Setup before recording:
- `uv run streamlit run app.py` running locally, browser at `http://localhost:8501`, window sized so the whole page fits without scrolling if possible.
- `slides.html` open in a second tab/window for the cold open and close.
- Terminal ready with `uv run python cli.py demo --context full --query "..."` if you want a CLI cutaway (optional, see note at 1:40).

---

## 0:00–0:15 — Cold open

**[ON SCREEN: `slides.html`, slide 1 — title]**

> "Every engineering team has this problem: someone reports a bug in Slack, a few people react, and then... nothing. No ticket. No owner. Weeks later it comes back as a customer escalation, and the internal warning is gone."

**[ON SCREEN: advance to slide 2 — "Bugs die in Slack threads"]**

> "SentinelOps is an agent that closes that gap automatically."

---

## 0:15–0:40 — What it does

**[ON SCREEN: slide 3 — "A pipeline, not a dashboard"]**

> "It's a four-node pipeline. Triage scans for unresolved complaints. Root-cause pulls context from GitHub, Linear, and Gmail. Fix-proposal drafts a ticket with evidence and a confidence score. Notify closes the loop back in Slack."

**[ON SCREEN: slide 4 — architecture stepper + stack table]**

> "Under the hood it's backed by HydraDB for the cross-tool context graph, RocketRide for hosted execution, and InsForge as the permission boundary — every action gated before it happens."

---

## 0:40–1:40 — Live demo: full context

**[ON SCREEN: switch to the dashboard, "Run" tab]**

> "Let's run it. The query: which bugs did we complain about in Slack that never became tickets."

**[ACTION: leave Incident on "Checkout 500", Context on "Full", click Run pipeline]**

> "Full context — Slack, GitHub, Linear, and Gmail all available."

**[ON SCREEN: point at the Triage card as it appears]**

> "Triage finds the complaint — repeated mentions, frustration language, no linked ticket."

**[ON SCREEN: scroll to Root Cause card, point at the confidence meter and evidence chips]**

> "Root-cause pulls in evidence from all four sources — you can see exactly which events it's grounded in — and lands at 95% confidence."

**[ON SCREEN: scroll to Ticket Proposal card]**

> "Fix-proposal drafts the ticket — title, severity, root-cause summary, and it stays in draft mode by default. Filing automatically requires an explicit policy decision, not a model guess."

**[ON SCREEN: scroll to Notification card]**

> "And notify closes the loop back in the original Slack thread."

*(Optional cutaway: switch to terminal, run the same query with `cli.py`, to show this isn't UI-only — the whole thing is a real Python pipeline underneath.)*

---

## 1:40–2:15 — The core visual: full vs degraded

**[ON SCREEN: dashboard, "Full vs Degraded" tab]**

> "Here's the part that actually matters: what happens when context is missing."

**[ACTION: click Compare contexts]**

> "Same query, same incident — but now GitHub, Linear, and Gmail are unavailable, just Slack."

**[ON SCREEN: point at the two confidence stat tiles — 0.95 vs 0.35]**

> "Confidence drops from 95% to 35%. Not because the model is guessing worse — because it's honest about how little it has to go on."

**[ON SCREEN: switch to slide 6 in the deck, or select the "Billing escalation" incident and re-run compare]**

> "And on a different incident, it's not just confidence — missing context flips the severity call itself, from high to low. That's the point: degraded context should visibly degrade the output, not silently produce a worse answer that looks just as confident."

---

## 2:15–2:35 — Safety

**[ON SCREEN: slide 7 — "No unrestricted bot with API keys"]**

> "Everything stays draft-only until an explicit policy allows filing. Every action — filing, tagging, escalating — is gated by confidence, severity, and evidence thresholds. And every one of those decisions is logged to a real, inspectable audit trail."

---

## 2:35–2:55 — Real integrations *(optional — cut for a 90-second version)*

**[ON SCREEN: slide 8 — "Verified against live infrastructure"]**

> "This isn't just mocked for the demo. HydraDB, RocketRide, and InsForge are wired up to their real, live APIs — we verified graph ingestion, hosted execution, and the audit log against actual running infrastructure, not just fixtures."

**[ON SCREEN: toggle a sidebar checkbox like "Use real HydraDB" if you have credentials loaded, and re-run]**

> "Flip a switch in the dashboard and it routes through the real API instead of the local mock — same pipeline, same output, real backend."

---

## 2:55–3:00 — Close

**[ON SCREEN: slide 9 — "Questions?"]**

> "SentinelOps — the pipeline that closes the loop before it reaches customers. Thanks."

---

## Cut-for-time guide

If you need a strict 90 seconds, keep only:
- 0:00–0:15 (cold open)
- 0:40–1:40, trimmed to just the Triage → Ticket Proposal cards (skip Notify)
- 1:40–2:15 (full vs degraded — this is the section judges remember, don't cut it)
- 2:55–3:00 (close)

That's the shape README.md's own "Demo Flow" describes: one query, full context, then degraded, then the confidence/severity delta as the payoff.
