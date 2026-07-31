# CLAUDE.md

Guidance for AI agents working on SentinelOps.

## Project Context

SentinelOps is a hackathon project: an autonomous incident commander that finds engineering complaints that fall between Slack, GitHub, Linear, and Gmail, then turns them into grounded Linear tickets and closes the loop in Slack.

The core product is a RocketRide-hosted multi-agent pipeline backed by HydraDB context, Pipeshift triage reasoning, and InsForge intent controls.

## Current State

The repo is currently docs-first. There is no implementation scaffold yet. Preserve the project direction in `README.md` when adding code.

## Implementation Principles

- Build the pipeline as the product. Avoid reducing SentinelOps to a static dashboard or search UI.
- Keep each node independently testable: triage, root-cause, fix-proposal, and notify.
- Treat cross-tool entity resolution as a first-class concern. The important signal is in relationships across systems, not isolated records.
- Make confidence and evidence explicit in every node output.
- Keep authorization decisions separate from model reasoning. InsForge-style intent policy should gate actions such as filing tickets, tagging people, or escalating severity.
- Prefer real integration seams with small local mocks over hard-coded demo data buried in node logic.

## Expected Pipeline Shape

1. **Triage node** detects unresolved complaint candidates from the context graph.
2. **Root-cause node** gathers related Slack, GitHub, Linear, and Gmail evidence and estimates likely cause and severity.
3. **Fix-proposal node** drafts or files a Linear issue with reproduction steps, evidence links, owner, confidence, and severity.
4. **Notify node** posts back to the source Slack thread with the ticket link and concise rationale.

## Demo Requirements

The demo should support two runs of the same query:

- Full context: Slack, GitHub, Linear, and Gmail enabled.
- Degraded context: Slack-only, with GitHub and Linear unavailable.

The degraded run should visibly reduce confidence and produce a less grounded ticket proposal. Keep this behavior observable through pipeline traces, not only through final text output.

## Data Contracts To Preserve

When introducing code, define typed contracts for:

- Source events and normalized graph entities.
- Complaint candidates.
- Evidence bundles.
- Root-cause analysis results.
- Ticket proposals.
- Notification payloads.
- Intent policy decisions.

Each contract should include enough provenance to explain why the agent acted.

## Safety And Permissions

Default to draft-only behavior until an explicit intent policy allows auto-filing or tagging. Never let a model decision directly call Slack or Linear without an authorization check.

Useful policy dimensions:

- Allowed workspaces, repositories, channels, and inboxes.
- Severity thresholds.
- Confidence thresholds.
- Auto-file versus draft-only mode.
- Allowed assignees or escalation groups.
- Required evidence types before action.

## Testing Guidance

Start with fixture-driven tests that simulate cross-tool gaps:

- Slack complaint with no Linear ticket.
- Slack complaint that already has a linked Linear issue.
- Duplicate complaint matching an old GitHub issue.
- Customer escalation in Gmail matching an internal Slack thread.
- Slack-only degraded context producing lower confidence.

As integrations are added, keep unit tests around node behavior and add thin integration tests around connector adapters.

## Development Notes

- Keep generated or demo fixture data small and readable.
- Do not commit secrets, API tokens, exported Slack data, Gmail content, or customer-identifying records.
- Use environment variables for credentials.
- If adding local setup scripts, document them in `README.md`.
- If adding a frontend, make the first screen the usable operator workflow, not a marketing landing page.
