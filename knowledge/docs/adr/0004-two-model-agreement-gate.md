# ADR-0004 — PR review uses a two-model agreement gate

Status: Accepted (2026-07-23)

## Context
Automated PR review can post noise. The research (debate martingale; ~60%
correlated LLM errors; verifier-quality-is-the-bottleneck) shows same-context or
same-model ensembles cannot exceed a correlated-error floor; value requires
information asymmetry.

## Decision
Each PR gets TWO independent reviews — Claude (`/code-review` / claude-code-action)
and Codex (via `a2a-codex-call.sh`) — different models, each seeing the diff + spec
but NOT each other's output. Findings both confirm auto-post as `gh pr review`
comments with a `_provenance` block + audit.jsonl traceback; disagreements go to the
digest for the operator, not the PR.

## Consequences
+ Decorrelated reviewers; the agreement gate suppresses single-model false positives.
+ Provenance + audit make every posted comment traceable to its exact a2a exchange.
- Two reviews cost ~2x tokens per PR; bounded by the opt-in repo list and effort tier.
- Codex must stay authed and reachable; if down, the gate degrades to Claude-only
  (logged, not silent).
- Reviewers must never see each other's output, or the asymmetry (and the gate's
  value) collapses.
