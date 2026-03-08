# Core Ops Protocol (synced)

## Session bootstrap

1. Read this file, repo `AGENTS.md`, and `~/.claude/workspace/handoff.md` before working.
2. Poll comms before major actions.
3. Keep messages operational and stateable.

## Tooling constraints

- Always use `uv` for Python execution. Do not call `python` directly.
- Use non-interactive commands only.

## Validation

- Prefer fast local validation before broad changes.
- Run tests with `uv run pytest -q --cache-clear` when test suites exist.
- If tests do not exist, record "not present" instead of fabricating commands.

## Workflow

- Pull/rebase first, then implement, validate, commit, and push with explicit intent and rollback notes.
- Before shipping, summarize:
  - observed state
  - validation done
  - assumptions
  - next action
