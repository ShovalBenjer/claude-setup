---
name: "phase-gate"
description: "Run multi-phase agent work with explicit transition checklists: Implementation, Review/Test, Deploy, Debug. No phase starts until the previous phase's checklist is fully verified. Unknowns are named and asked, never guessed. Use for any task with distinct build-then-verify-then-ship stages."
---

> Source: mechanism extracted from `platform-engineer` / `platform-compliance` in joatmon08/platform-infrastructure-skills (Rosemary Wang, MIT License). Terraform/AWS content removed; the phase-gate, never-guess, and justify-or-remediate mechanisms preserved and generalized.

# Phase Gate

## The rule

Work runs in phases. Each phase ends with a **transition checklist** of verifiable items. The next phase does not start until every item is checked — checked means *verified by running something*, not asserted.

## Phases

### 1. Implementation

Build the thing. Before leaving this phase, verify:
- [ ] All inputs the build needed were actually known — **never guess a default**. Any unknown is named explicitly and asked, not filled in silently.
- [ ] Output follows the project's structural conventions (file layout, naming, config placement).

### 2. Review and Test

- [ ] Static checks pass (format, lint, type-check — the project's own commands, run for real).
- [ ] Tests pass, including at least one test that would fail if the implementation were wrong (no near-tautologies).
- [ ] Findings are separated by channel: each finding class goes to its own record. Do not mix classes into one document.

### 3. Deploy / Ship

- [ ] The deploy target and its configuration are confirmed (not assumed).
- [ ] Every high-priority finding from Phase 2 is either **remediated or justified in writing** — a bare violation with no justification blocks this phase.
- [ ] The human has reviewed the ship output where the project's policy requires it.

### 4. Debug

When something fails after shipping, follow this order:
1. Collect the actual error evidence (logs, output, traces) — never diagnose from memory of what "usually" fails.
2. Fix from evidence, re-run the Phase 2 checklist on the fix.
3. **Escalation criteria**: write down in advance which failure classes get escalated to a human (or another team) instead of retried — e.g. missing platform-level resources, permission/credential problems, flaky external services. When a failure matches a criterion, escalate immediately; do not loop.

## Recovery

If a phase's checklist cannot be completed, stop and report exactly which item failed and what is needed — do not carry a broken phase forward.
