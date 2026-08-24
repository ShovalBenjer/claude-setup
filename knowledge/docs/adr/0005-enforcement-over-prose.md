# ADR-0005 — Enforcement over prose (hooks/gates bind, CLAUDE.md requests)

Status: Accepted (2026-07-23)

## Context
The operator's own gap analysis diagnosed the harness's central weakness: rules,
personas, and contracts are prose in CLAUDE.md — requests the model may route
around — not enforced mechanisms. "Please don't push to main" is not a control; a
pre-push hook + branch protection is. The 2026-07-23 feedback (shallow patches,
fast "done") is the same defect on the output side.

## Decision
Every load-bearing rule in the OS has an ENFORCEMENT MECHANISM, not just prose:
a hook, a gate, a CI check, a state-machine transition, or a required file. The
Deep Work Protocol's "sticks via" column is mandatory — a rule with no stick is a
defect to be either wired or deleted. Self-improvement changes to the harness are
proposal-only and approval-gated (the OS proposes, the operator disposes).

## Consequences
+ Discipline binds on every session, including headless crons, not just cooperative ones.
+ "Done" becomes structurally defined (evidence + intent-coverage table), so
  fast-shallow-done is impossible to report.
- Every new rule now carries a wiring cost (the hook/gate), which is the point.
- Over-enforcement can block legitimate work; gates fail-open with logging by
  default, hard-block only where explicitly marked.
