# CLAUDE.md

This repository previously only had an AGENTS.md file. Until a more specific CLAUDE.md is authored, use this default baseline.

## Operational Comms Standard

Operational messages must be intentionally actionable. Do not send non-operational status noise or periodic chatter.

- Use `REQUEST` only for explicit action requests, decisions, approvals, or escalations.
- Use `STATUS` only for state transitions (started/finished/blocked/handed off), not idle progress.
- Every outbound message should include:
  - `topic`: stable routing/decision area (for example `repo_sync_gate`, `handoff`, `blocker`, `task_status`)
  - `state`: `pass | running | blocked | done`
  - `delta`: what changed since the last message
  - `impact`: why this matters to downstream agents
  - `next_action`: owner + explicit next step + verification criteria
  - `risks`: blockers or open assumptions (if any)
  - `ask`: a concrete question, only when a response is required
- Keep messages concise; one objective per message.

If no actionable content exists, do not message.
