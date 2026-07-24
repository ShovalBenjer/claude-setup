# Docs Index — Claude OS

Generated-from-docs wiki spine (docs-control-plane rule). One TODO, one INDEX.

## Spine
- [CLAUDE-OS.md](../CLAUDE-OS.md) — single source of truth: layers L0-L8, deep-work
  protocol, native-feature map, dynamism loops, supersession table.
- [SESSION-BOOT.md](SESSION-BOOT.md) — any fresh session: full context from disk in 60s.
- [charters.md](charters.md) — the four session lanes (A concierge / B setup / C resume / D learning).
- [OPERATOR-RUNBOOK.md](OPERATOR-RUNBOOK.md) — manual unblock steps.
- [EXECUTION-PLAN.md](EXECUTION-PLAN.md) — P0-P4 harness build phases.

## PRDs
- [prd/claude-os.md](prd/claude-os.md) — harness acceptance table (SETUP-OS, 20 rows).
- [prd/autonomy-ecosystem.md](prd/autonomy-ecosystem.md) — next-level system (AUTO-01..20):
  repo autonomy, social pipeline, resume rails, ecosystem.db, lessons+research loops.

## Specs
- [specs/2026-07-24-autonomy-implementation.md](specs/2026-07-24-autonomy-implementation.md) — phased build w/ premortem (active).
- [specs/2026-07-24-command-center-superior.md](specs/2026-07-24-command-center-superior.md) — FleetView, CCC-superior dashboard (active).
- [specs/2026-07-23-persona-review-economy.md](specs/2026-07-23-persona-review-economy.md) — reviewer labor market (active).
- [specs/2026-07-23-slm-swarm.md](specs/2026-07-23-slm-swarm.md) — SLM leaf executors + flywheel (active).

## ADRs
- [0001](adr/0001-claude-setup-as-canonical-os-repo.md) — claude-setup = canonical OS repo
- [0002](adr/0002-subscription-oauth-over-metered-api.md) — subscription OAuth, not API key
- [0003](adr/0003-native-push-over-onesignal.md) — native push for approvals, not OneSignal
- [0004](adr/0004-two-model-agreement-gate.md) — two-model agreement gate for PR review
- [0005](adr/0005-enforcement-over-prose.md) — enforcement over prose (hooks bind)
- [0006](adr/0006-one-scheduler-topology.md) — native cron + cloud routines; WSL systemd retired
- [0007](adr/0007-codex-reviewer-only.md) — AMENDED: Codex removed; free different-family models
- [0008](adr/0008-reputation-from-external-truth-only.md) — reputation from external truth only
- [0009](adr/0009-slm-swarm-asymmetric-leaf-executors.md) — SLM swarm = leaf executors + flywheel
- [0010](adr/0010-sessions-are-ephemeral-disk-is-memory.md) — sessions ephemeral; disk is memory
- [0011](adr/0011-one-operational-state-db.md) — one ecosystem.db, seeded from intent-control-plane
- [0012](adr/0012-autonomy-ships-only-via-pr-gate.md) — autonomy ships only via PR gate
- [0013](adr/0013-session-topology-concierge-plus-lanes.md) — concierge + three chartered lanes
- [0014](adr/0014-social-publish-draft-first-hard-gate.md) — social publish behind phone-approval gate

## Analysis (point-in-time; inputs to TODO)
- [analysis/2026-07-24-work-archive-import.md](analysis/2026-07-24-work-archive-import.md) — full work-setup import inventory.
- [analysis/2026-07-23-local-model-stress-test.md](analysis/2026-07-23-local-model-stress-test.md) — local model ceiling (14B-Q4).
- Research digests (harness depth, PR-review, MCP) — agent runs 2026-07-23; papers in CLAUDE-OS §2b.

## State (operational, ADR-0010/0011)
- `../state/lessons.jsonl` — lessons ledger (seeded 8).
- `../state/compact-log.md` — PreCompact snapshots.
- `../tools/selfimprove/proposals.jsonl` — ranked open work.

## TODO
- [TODO.md](../TODO.md) — grouped by layer, ticket-tagged.
