# SentinelOps

SentinelOps is an autonomous incident commander for the gaps between engineering tools. It watches Slack, GitHub, Linear, and Gmail context, finds complaint-shaped issues that never became tickets, investigates them, files grounded Linear tickets, and closes the loop in the original Slack thread.

This repository currently captures the hackathon project brief and implementation direction for the **Agents You Love** hackathon at Frontier Tower.

## Problem

Engineering teams lose signal in the space between tools. A teammate reports a bug in Slack, a few people react, and the thread goes quiet. Because filing a ticket is friction, no one creates a Linear issue. Weeks later the same problem resurfaces through a customer escalation, and the original internal warning is effectively gone.

Slack can find Slack messages. Linear can find Linear tickets. The useful operational question lives across systems:

> Which bugs did we complain about in Slack that never became tickets?

SentinelOps is designed to keep answering that question continuously, then act before the gap reaches customers.

## What SentinelOps Does

SentinelOps runs a multi-agent pipeline over a synced cross-tool context graph:

1. Detects unresolved complaints in Slack.
2. Resolves related context across Slack, GitHub, Linear, and Gmail.
3. Reasons about severity, likely root cause, and ownership.
4. Drafts or files a Linear ticket with concrete reproduction context.
5. Replies in the original Slack thread so the reporter sees the loop close.

The product is the agentic operations pipeline, not a dashboard around manual search.

## Architecture

The intended pipeline is a four-node chain.

### Triage Node

Continuously scans the HydraDB graph for unresolved complaints:

- Repeated mentions of the same issue.
- Frustration or breakage language.
- Threads with no linked GitHub issue or Linear ticket after a defined time window.
- Similar historical incidents that may indicate duplicates or regressions.

HydraDB provides the entity-resolved join across systems that a single connector cannot provide.

### Root-Cause Node

When triage flags a candidate, this node pulls cross-source context:

- Original Slack thread.
- Related commits, PRs, and code ownership signals.
- Existing or prior Linear tickets.
- Gmail escalation history.

It then estimates severity, summarizes evidence, and forms a likely root-cause hypothesis. The concept calls for this reasoning to run on a Pipeshift model tuned for dev-ops triage.

### Fix-Proposal Node

Creates the operational artifact:

- Linear ticket title.
- Reproduction steps from the thread.
- Root-cause hypothesis.
- Evidence links.
- Suggested owner based on repository ownership or blame signals.
- Severity and confidence.

Depending on the configured intent policy, this node can either draft the ticket or file it automatically.

### Notify Node

Posts back to the original Slack thread with:

- Confirmation that a ticket was created or drafted.
- Link to the Linear issue.
- Suggested owner or escalation target.
- Brief summary of why SentinelOps acted.

This makes the system visible to the person who raised the issue and reduces the chance that useful internal signal disappears.

## Intent And Permissions

InsForge is the authorization layer for the pipeline. It should define what SentinelOps is allowed to do at each stage, including:

- Draft-only versus auto-file behavior.
- Which channels or teams can be monitored.
- Who the agent may tag.
- Severity thresholds for escalation.
- When to create backlog items instead of urgent incidents.
- What evidence must be present before taking action.

The intent layer is part of the product boundary. SentinelOps should not behave like an unrestricted bot with API keys.

## Demo Flow

The 90-second demo should make the cross-tool dependency visible:

1. Ask: "Which bugs did we complain about in Slack that never became tickets?"
2. Run the full Slack, GitHub, Linear, and Gmail pipeline in RocketRide.
3. Show all four nodes executing in the RocketRide trace view.
4. End with a real Linear ticket and a Slack reply in the original thread.
5. Disable the GitHub and Linear context.
6. Re-run the same query with Slack-only context.
7. Show confidence and output quality degrade in RocketRide observability.

The key visual is not just better versus worse text. It is the trace showing the root-cause and fix-proposal nodes lose grounding when the graph loses source context.

## Stack

| Component | Role |
| --- | --- |
| HydraDB | Entity-resolved context graph across Slack, GitHub, Linear, and Gmail |
| Pipeshift | Dev-ops triage model for root-cause reasoning |
| RocketRide Cloud | Multi-node agent orchestration, production hosting, and observability |
| InsForge | Intent and permission boundary for agent actions |

## Stretch Goal

Expose the finished pipeline as an MCP tool so it can be triggered directly from Claude Desktop, Cursor, or another agent client without a custom frontend.

## Repository Status

The pipeline is implemented end to end in Python, backed by local fixture-driven mocks for all four sponsor integrations (HydraDB, Pipeshift, RocketRide, InsForge) behind typed adapter interfaces, so real clients can be swapped in without changing node logic.

```
sentinelops/
  contracts/     # typed data contracts (pydantic)
  graph/         # HydraDB adapter + mock (entity-resolved context graph)
  reasoning/      # Pipeshift adapter + mock (root-cause/severity scoring)
  connectors/      # slack, github, linear, gmail (fixture-backed, enable/disable per source)
  policy/           # InsForge adapter + mock (intent policy: draft-only by default)
  nodes/             # triage, root_cause, fix_proposal, notify
  orchestrator/       # pipeline runner + RocketRide trace mock
  fixtures/            # demo incident data + full/degraded context configs
```

Run the demo:

```
uv sync
uv run sentinelops demo --context full --query "Which bugs did we complain about in Slack that never became tickets?"
uv run sentinelops demo --context degraded --query "Which bugs did we complain about in Slack that never became tickets?"
```

The full-context run grounds its root-cause analysis in all four sources; the degraded (Slack-only) run visibly drops confidence and lists the missing sources directly in the printed trace, matching the Demo Flow above.

For presenting the demo, there's also a Streamlit frontend (`app.py`) with a "Run" tab (the operator workflow: pick a context, run the pipeline, see the trace and resulting ticket/notification) and a "Full vs Degraded" tab that runs both contexts side by side with a confidence comparison, for the moment in the Demo Flow above:

```
uv run streamlit run app.py
```

### Real HydraDB integration

The HydraDB adapter has a real implementation (`sentinelops/graph/hydra_live.py`), verified against the live API, alongside the local mock (`InMemoryHydraGraph`). It ingests events as HydraDB knowledge sources with explicit forceful relations between events that share a `link_key` - the same cross-source grouping the mock does locally, now computed as real graph edges in HydraDB's backend. Node logic is unaffected either way, since both implementations satisfy the same `ContextGraph` interface.

```
uv sync --extra hydra
HYDRA_DB_API_KEY=... uv run --extra hydra python cli.py demo --context full --graph-backend hydradb --query "..."
```

The Streamlit app has a matching "Use real HydraDB" toggle in the sidebar (enabled once `HYDRA_DB_API_KEY` is set in the environment). Pipeshift, RocketRide, and InsForge remain mock-only until their credentials/docs are available.

Remaining stretch work: exposing the pipeline as an MCP tool (see Stretch Goal), and wiring the other three sponsor clients in behind their existing adapter interfaces.

Run tests with `uv run pytest -q`; lint with `uv run ruff check .`.
