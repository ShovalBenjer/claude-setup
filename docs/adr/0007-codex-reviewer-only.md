# ADR-0007 — Codex is an independent reviewer, not an executor

Status: Accepted (2026-07-23; supersedes the "Codex is the executor" global rule)

## Context
The global CLAUDE.md said "Codex is the executor (gpt-5.5); Claude is the
orchestrator." The 2026-07-20 decision made the hiring engine claude-only and killed
the Codex execution handoff. But Codex remains valuable as a DIFFERENT model for
decorrelated review (ADR-0004).

## Decision
Codex's role in the personal OS is independent reviewer / second opinion only,
reached via `a2a-codex-call.sh` (read-only, low effort, audited). It does not execute
build tasks, does not own runtime, does not carry the loop. Claude orchestrates and
executes; Codex reviews.

## Consequences
+ Resolves the standing contradiction between the global rule and the 07-20 decision.
+ Preserves Codex's real value (model diversity for the agreement gate) without the
  dead execution handoff.
- The global CLAUDE.md line is now stale and should be updated to match.
- A2A audit must record which model reviewed, for provenance.
