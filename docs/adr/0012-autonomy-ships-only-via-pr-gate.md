# ADR-0012 — Autonomous work ships ONLY through PR + review gate

Date: 2026-07-24. Status: accepted.

## Context

The system is gaining the ability to change repos with nobody watching (nightly
GitHub-scheduled Claude runs, weekly self-improve auto-apply). An autonomous direct
push to main is the single highest-blast-radius failure available to this system.

## Decision

No autonomous path may push to a default branch. Every autonomous change: branch →
PR → two-model decorrelated review (ADR-0004/0007) → merge policy. Merge policy is
class-based: `auto:low` (docs, tests, lint, comments) may auto-merge on CI green +
both-model approval; everything else requires operator approval via phone push.
Caps: 1 nightly PR/repo/day, max 3 open autonomy PRs/repo, repo auto-pauses after 2
consecutive rejections (reputation gate). The nightly workflow file itself contains
no push-to-main step — the constraint is structural, not behavioral (ADR-0005).

## Consequences

- Autonomy PRs get reviewed by the same fabric as human PRs — the loop audits itself.
- Slower than direct push; that latency IS the safety margin.
- "production means merged-and-smoked" rule applies to autonomy output unchanged.
