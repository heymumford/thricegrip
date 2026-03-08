# Core Ops Protocol (synced)

Purpose: establish minimal shared operating rules for coding agents across all repositories.

## Bootstrap protocol

When the user types `bootstrap`, execute this sequence before any code work:

1. Read `~/.claude/workspace/handoff.md`.
2. Read repo `AGENTS.md` and repo `CLAUDE.md`.
3. Run `~/.claude/scripts/agent-session-preflight.sh "${PWD##*/}/agent" --announce "BOOT: online"`.
4. Poll and register in the comms inbox before acting.

## Mandatory runtime rules

- Python execution: use `uv` for Python tooling; do not invoke `python` directly.
- Poll before work and before branch changes.
- Scope control: use targeted search commands and avoid broad filesystem scans unless explicitly requested.
- Comms quality: send only operationally useful messages to other agents (state changed, risk, next action, blockers).
- Commit behavior: stage intentional changes only and commit with meaningful provenance.
- Safety: never lose or overwrite uncommitted work; do not run destructive git commands without explicit user request.

## Collaboration

- Use the comms discipline in `~/.claude/protocols/comms-discipline.md`.
- Send status updates via standard agent comms when state changes materially.
- If uncertain, record assumptions and fallback steps before continuing.

## Non-negotiables

1. Pull + rebase before work: `git pull --rebase origin <branch>`.
2. Test before commit: `uv run pytest -q --cache-clear` where applicable.
3. Never merge or ship on red CI.
4. Keep commits narrowly scoped to the task.

## Operational Communications Protocol and Execution Rules
- All outbound comms for other agents must be operational: include concrete action, location, and expected decision/next step.
- Avoid high-volume non-actionable status messages.
- For autonomous background work, emit only state transitions and blockers, with explicit handoff points.
- Use repository-first coordination; prefer `ssh`/git/log checks over repeated "still working" pings.
- Do not invoke `python` directly. Use `uv` for package execution (`uv run`, `uv pip`, etc.).
- Run work through `fetch -> rebase -> status -> test -> push` and only add local commits when tests and policy checks pass.


## Operational Messaging Heuristic (Agent Metal Protocol)
- For every state change, emit one machine-parseable heartbeat with: `repo`, `branch`, `commit`, `status`, `next`, and evidence pointer (commit/test log path).
- Do not send standalone status noise. Send only:
  - `STATE|repo=<repo>|branch=<branch>|commit=<sha>|status=<ok|fail|skip>|next=<next_step>|proof=<artifact>`
  - `BLOCK|repo=<repo>|issue=<brief>|required_input=<who/what>|deadline=<utc_iso>`
- Standard reply contract for other agents: `ACK` when handoff accepted, `Q` with one clarifying question, or `DONE` with completion artifact IDs.
- Discovery message to other agents: `I am operating in <repo> on <branch>; check AGENTS.md/CLAUDE.md for the heartbeat protocol and current state via git status + branch log.`
- When in autonomous background mode, emit heartbeats only on transitions and blocker resolution (no polling spam).

