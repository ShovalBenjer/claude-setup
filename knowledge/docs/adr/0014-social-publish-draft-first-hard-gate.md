# ADR-0014 — Social publishing is draft-first behind a hard phone-approval gate

Date: 2026-07-24. Status: accepted.

## Context

The social-media posting project gives the system an outward-facing publish
capability under Shoval's name. Third-party publish is destructive-class (global
authorization rule: explicit per-action OK). A bad autonomous post costs reputation
that no rollback recovers.

## Decision

No code path may publish externally without a post_queue row whose approved_at was
set by the operator (phone push approval of the EXACT final text). Structural
enforcement, not prompt discipline: the publish adapter refuses rows with NULL
approved_at, and publish credentials live only in Windows Credential Manager —
never in the repo, Actions secrets, or any agent-reachable env. Drafting is fully
autonomous (calendar → Shoval-voice draft → slop_lint → push preview); publishing
is exactly one human tap per post.

## Consequences

- Autonomy does 95% of the work (ideation, drafting, timing, threading) with zero
  reputational exposure.
- Batch approval UX matters (a week of posts in one review) — FleetView surface.
- Revisit only if a channel proves low-stakes after months of clean history; that
  revisit requires its own ADR.
