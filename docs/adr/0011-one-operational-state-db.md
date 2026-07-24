# ADR-0011 — One operational state DB (ecosystem.db), seeded from intent-control-plane

Date: 2026-07-24. Status: accepted.

## Context

Operational state is scattered: proposals.jsonl, router_decisions.jsonl, planned
reputation.db, cron outputs, per-tool files. The work setup already solved this shape
once: intent-control-plane (imported 2026-07-24) ran intent.db as a control plane with
tower as its viewer. Excavate-before-building applies.

## Decision

ONE SQLite file, `state/ecosystem.db`, is the system-of-record for OPERATIONAL state:
sessions, proposals, runs, lessons, reputation, post_queue, repo_registry (schema in
specs/2026-07-24-autonomy-implementation.md §P1). Seed the design from
intent-control-plane's schema and redaction gateway. JSONL files remain as append-only
ingest logs that MIGRATE into the db; docs/ and memory/ remain files (prose belongs in
git, not sqlite). FleetView reads this db — it is tower's descendant.

## Consequences

- Work-claims, run history, and reputation become queryable and shared across lanes —
  the mechanical fix for duplicate work.
- One file to back up; one schema to migrate; secrets and PII never enter it
  (pii-handling rule; redaction gateway pattern from intent-control-plane).
- Rejected: per-tool DBs (sprawl), Postgres (ops burden for one operator), everything-
  as-jsonl (no cross-table queries for routing/reputation).
