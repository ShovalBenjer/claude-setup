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
Caps: 1 nightly PR/repo/day, max 3 open autonomy PRs/repo (counted by `auto/*`
branch prefix, failing CLOSED on API error), repo auto-pauses after 2 consecutive
rejections (reputation gate).

The structural control (corrected 2026-07-24 after adversarial review): branch
protection is unavailable on a private free-plan repo, so the guard is built into
the workflow shape instead — the agent step has NO Bash (file edits only); all
git/gh operations run in deterministic shell steps; the only push is the literal
`git push origin HEAD` of an `auto/*` branch; review is guaranteed by an in-run
review job (GITHUB_TOKEN-created PRs never trigger pull_request workflows, so
relying on claude-code-review.yml alone would silently skip review). If the repo
ever goes public or Pro, add branch protection and simplify.

## Consequences

- Autonomy PRs get reviewed by the same fabric as human PRs — the loop audits itself.
- Slower than direct push; that latency IS the safety margin.
- "production means merged-and-smoked" rule applies to autonomy output unchanged.
