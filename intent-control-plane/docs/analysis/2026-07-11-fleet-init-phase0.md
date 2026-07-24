# Fleet Init Phase 0 — read-only readiness map (2026-07-11)

Point-in-time scan (docs-control-plane: analysis/). Produced by `intent init` (structural) +
a 9-agent read-only workflow (semantic unified-TODOs). No repo was modified. Source dump:
`/tmp/.../tasks/wq1kdey4c.output`. Nothing here is implemented; this is the map that gates Phase 1.

## Totals

9 active content-bearing repos, ~265 backlog tasks: ~206 delegable, ~59 human-only.
Every repo needs the same two organize-first actions: unify 3-4 competing TODO files into one, and
add a docs/ INDEX spine. Four carry a repo-in-repo defect.

## Per repo

| Repo | delegable / human | repo-in-repo defect | top organize-first |
|---|---|---|---|
| ORM-AGENT (widgora umbrella) | 36 / 3 | social-media-agent/.git | fold nested repo; unify status docs; reconcile contradictory done/open |
| agent-call-tracker | 27 / 6 | axia-seekapa-cs-agents/.git (the stray Cursor copy) | remove the mistaken copy; unify 3 backlog files; add ADR log |
| axia-seekapa-cs-agents | 19 / 3 | none | split cross-project tasks out of auto-mode doc; delete dead codex artifacts |
| call-analyzer-frontend (Vlad's) | 10 / 2 | none | add vitest + first tests; wire CI gate; unify 2 TODOs |
| campaign-analysis (on hold) | 17 / 9 | Onesignal/.git | fold nested repo; reconcile huge untracked set; unify 4 TODOs |
| qc-telephony-api (prod) | 24 / 12 | none (clean) | unify TODOs; delete dead branch; refresh stale ops doc |
| sales-agents | 18 / 8 | none | add ruff+mypy (zero today); docs/INDEX spine; archive legacy version scripts |
| seekapa-training-platform | 27 / 9 | none | mostly organized already (docs + 172 tests); minor TODO unify |
| video-understanding (on hold) | 28 / 7 | ui-ux-pro-max-skill/.git | fold nested repo; unify 6 TODOs; add root manifest |

## Non-delegation zones (human-only, clustered)

- Auth/RBAC/OAuth: call-analyzer OAuth+RBAC+data-restrictions, agent-call-tracker webhook HMAC
  fails OPEN, training cross-user report authorization.
- Secrets/credentials: campaign-analysis has Bearer tokens pasted in a 2026-04-21 chat needing
  rotation; axia + sales-agents Key Vault variable-group wiring.
- Production deploy / pipeline / branch-policy: widgora HOLD-ALL, qc branch policies + prod Azure
  actions, training prod migrations, video-understanding deploy stages + Cloudflare lock.

## Two urgent security items surfaced (independent of the harness work)

1. campaign-analysis: rotate the Bearer tokens pasted in chat (kv-seekapa-apps).
2. agent-call-tracker: the Chatwoot webhook HMAC check fails OPEN when the secret is unset.

## Phase sequence (each step gated)

- Phase 1 Organize (additive, PR-not-push, per-repo OK): unify TODOs + docs spine per repo; fold
  the 4 nested repos (human-supervised, history-altering, with backup); remove the stray copy.
- Phase 2 Prereqs before graded spawns: fix the failing eval gate (0/20), wire gastown-spawn ->
  guardrails/rubric/archive so spawns are graded + guarded.
- Phase 3 Piloted delegation: one non-corp low-stakes repo (sales-agents), delegable tasks only,
  PR-not-push, human review, then widen.
