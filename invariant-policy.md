# Cognilateral Meta-Instruction Invariants (Fleet-Wide)

This policy is the shared operating contract across all heymumford repositories.

## System of Record

1. Cognilateral is a living architecture, not a linear environment ladder.
2. The source of truth for infrastructure intent is explicit in this policy + repo `AGENTS.md` / `CLAUDE.md` files.
3. Any file that encodes behavior should remain reversible and observable.

## Host-role model

- `turing`: shared infrastructure lane (canonical for Neo4j in local-systems mode, Prometheus, Ollama, CI shared run target)
- `m4max`: command/dev lane (PostgreSQL-heavy iteration lane, local recovery testing, rapid experiments)
- `watts`: auxiliary lane (observability/ops support, Grafana, secondary tooling)
- Fly: production-facing runtime for Cognilateral services and managed services where explicitly declared

## Contract of record

The authoritative placement artifact for these lanes is:

- `infra/host-service-contract.md`

Any drift between this policy and host/db placement claims should be resolved by first updating
the contract file, then aligning all role and dependency sources.

## Core invariants

1. Lane-first progression, not just dev/qa/uat/prod.
2. Canonical topology contract is explicit and synchronized.
3. Service ownership and data ownership is pinned and documented.
4. Changes are reversible by design.
5. Validation is required before trust expands scope.
6. No hidden or implicit host assumptions in runtime behavior.
7. Every substantial decision includes: assumption, blast radius, rollback, validation.

## Execution contract

For every cross-system action:

- Discover current state (service map + host map + ownership)
- State assumptions and risk level
- Execute with rollback plan
- Verify outcomes before expanding scope
- Leave the system no more surprising than before (or clearly better)

## What agents should do with this policy

- Keep this policy discoverable and aligned with repo-specific `AGENTS.md` and `CLAUDE.md`.
- Treat every repo instruction file as requiring the `Meta-Architectural Operating Lens` section.
- Use lane terminology explicitly in planning and retrospectives.

## Scope note

If multiple files disagree on topology or ownership, resolve the conflict by:
1) Policy hierarchy (this file),
2) Repo-appropriate `AGENTS.md`/`CLAUDE.md`,
3) recent runbooks, topology manifests, and inventories,
4) explicit owner decision.
