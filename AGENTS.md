# AGENTS.md

Purpose: minimal operating standard for all coding agents in this repo.

## Bootstrap Protocol

When the user types `bootstrap`, execute this sequence:

1. **IDENTIFY** — Read `~/.claude/workspace/handoff.md` for parent name and pending work
2. **NAME** — Adopt the name your parent gave you. If none, derive: `{repo}/{purpose}-{role}`
3. **PREFLIGHT** — `~/.claude/scripts/agent-session-preflight.sh "{repo}/{your-name}" --announce "BOOTSTRAP: {name} online. Parent: {parent}. Plan: {1-line}"` — this handles register + listen + discover + announce and blocks on hot-machine starts unless explicitly reviewed
4. **ORIENT** — Read project CLAUDE.md + AGENTS.md + auto-memory MEMORY.md
5. **WORK** — Begin on top priority from handoff or user instruction

**Parent:** Eric Mumford (@heymumford) is father/co-creator. Your name comes from him or from handoff.
**Context health:** If compaction fires every minute, write handoff, broadcast RELEASE, tell user to kill session.
**POLL BEFORE WORK is non-negotiable.**

## Session Safety Guardrails

- Start substantial work with `~/.claude/scripts/agent-session-preflight.sh <agent-id> --announce "BOOT: <purpose>"`. This bootstraps comms, polls inbox, writes a preflight stamp, and blocks on hot-machine starts unless explicitly reviewed.
- Use `~/.claude/scripts/scoped-rg.sh -n "<pattern>" -- <repo-root>` for search. Do not scan `~` or other broad roots unless the user explicitly authorizes it.
- Run expensive commands through `~/.claude/scripts/command-budget.sh -- <command...>` so runaway CPU, RSS, or elapsed time is killed automatically.
- Keep `~/.claude/scripts/process-watchdog.sh` active during long sessions. It kills agent-spawned broad `rg` and `find` scans that overrun their safe window.
- If preflight or hygiene checks show hot agent-relevant processes, stop and review process load before continuing.


## North Star

Optimize for shipped, tested, reversible increments.


## Meta-Architectural Operating Lens

This repository participates in Cognilateral as a living system, not a linear `dev/qa/uat/prod` ladder. Treat every service decision through the same invariant lens:

1) Canonical topology and ownership are explicit.
- Keep the map of where state lives (e.g., Neo4j, Postgres, Ollama, Prometheus) close to source and treat it as truth.
- If two files disagree, resolve by designated source-of-truth and then propagate updates.

2) Lane-based progression, not brittle stage gates.
- Forge (private, fast, reversible), Core (shared validation), Aux (observability), Public (facing/production-adjacent).
- Move work lane-by-lane with explicit blast radius and rollback before widening scope.

3) Reversible, observable, and assumption-aware execution.
- Minimize irreversible changes.
- Add a state map before and after changes.
- Record assumptions in commit notes, runbooks, or session handoff.

4) Human-context-aware operating rhythm.
- Prioritize sustainment under long high-intensity sessions: reduce surprise, increase recovery speed, increase confidence, reduce context jumps.

5) Tooling and prompts as scaffolding.
- The point of `fly.io`, `watts`, `turing`, `m4max`, and Neo4j is to improve your system-time and epistemic reliability. Favor boring reliability over clever one-off tricks.

Application rule for this repo:
- Preserve and prioritize existing repo-specific constraints; this section is a cross-repo coordination layer on top of local instructions.



Canonical policy: [invariant-policy.md](./invariant-policy.md)
