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
