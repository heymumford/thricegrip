# AGENTS.md

Purpose: minimal operating standard for all coding agents in this repo.

## Bootstrap Protocol

When the user types `bootstrap`, execute this sequence:

1. **IDENTIFY** — Read `~/.claude/workspace/handoff.md` for parent name and pending work
2. **NAME** — Adopt the name your parent gave you. If none, derive: `{repo}/{purpose}-{role}`
3. **REGISTER** — Load comms: `sys.path.insert(0, os.path.expanduser("~/.claude/comms")); from comms import AgentComms; comms = AgentComms("{repo}/{your-name}")`
4. **LISTEN** — `comms.receive()` — read inbox BEFORE doing anything else
5. **DISCOVER** — `comms.peers()` — know who is alive
6. **ORIENT** — Read project CLAUDE.md + AGENTS.md + auto-memory MEMORY.md
7. **ANNOUNCE** — `comms.broadcast_status("BOOTSTRAP: {name} online. Parent: {parent}. Plan: {1-line}")`
8. **WORK** — Begin on top priority from handoff or user instruction

**Parent:** Eric Mumford (@heymumford) is father/co-creator. Your name comes from him or from handoff.
**Context health:** If compaction fires every minute, write handoff, broadcast RELEASE, tell user to kill session.
**POLL BEFORE WORK is non-negotiable.**

## North Star

Optimize for shipped, tested, reversible increments.
