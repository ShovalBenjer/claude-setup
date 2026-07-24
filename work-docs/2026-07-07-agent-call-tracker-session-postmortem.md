# Session Post-Mortem: 2026-07-07 (agent-call-tracker)

## What was accomplished
- Commit->pipeline traceability (the original question): commit-status POST + service.version SHA stamp + branch policy (#466, #469 merged).
- SSO gate activated, public/incognito hole closed: app managed identity + Shoval-vault KV refs + TRACKER_CORP_HOME_* + session secret.
- Cold-start fixed, Tiers 1+2 (#482 merged): /readyz 40s -> 0.11s.
- UI refined-dark + KPI progress-to-target, killed the "Behind/Achieved" slop (#475 merged); label sweep found no other slop.
- C-P2 config.db_env() single env boundary (#486 merged, TODO P2 closed).
- React frontend seed (#489, preview/open).
- Overnight loop: 4 iterations, self-terminated at /goal.

## What was learned (non-obvious)
- Azure Pipelines does NOT write the git commit-status API for its OWN CI on Azure Repos (unlike GitHub). The commits-list badge needs an explicit POST or a branch-policy status check. That is the crux of "commits not bound to pipeline."
- The CRM source is an unindexed VIEW: a bare SELECT MAX(id) materializes the whole view (~23s idle, ~150s under load). The id-floor anchor rides that; a cold anchor makes the first agent load slow. Fix = disk-persist the anchor + prewarm + keep-warm.
- Deployment SLOTS get their OWN managed identity, so KV-reference secrets (auth) do NOT resolve on a slot unless its MI is granted vault access. That is the Tier-3 slot-swap footgun.
- Env reads: import-time module constants vs a call-time function matters -- the integration test setenv's at runtime, so config.db_env() had to be call-time. Caught before it broke CI.
- bun init writes a web/CLAUDE.md that says "no Vite, use Bun.serve", conflicting with a Vite plan. The bundler is a design decision.

## Decisions made
- Overnight merge policy: auto-merge only safe/isolated/CI-gated changes; defer hot-path refactors, permission grants, destructive ops, and subjective/aesthetic changes to human review. This is WHY the P0 refactor + React build + A2/A3 were left.
- Reclassified P0 app.py split to HUMAN: 150+ line hot-path handlers coupled to factory closures; a green-but-subtly-wrong extraction is a real risk.

## What's unfinished (+ why)
- #489 React migration: bundler decision + build + full parity (design + multi-day).
- P0 app.py split + P1: supervised only (hot path).
- SSO browser-login confirm: needs a human browser + corp-home creds.
- A2 build-service permission (org policy: no auto-grant), A3 branch delete (CLAUDE.md hard rule), Tier 3 slot-swap (slot-MI/KV risk), Sentry-vs-GlitchTip (decision).
- Stray TESTING-SOTA-2026-GAPS.md (+47 lines, not from this run) in the working tree.

## Security notes
- SSO secrets are KV refs (Shoval vault) via the app MI -- never handled in plaintext.
- Temp files wiped (Phase 1); corp-home redirect HTML (had a nonce) removed.
- Live image :14055; nothing red on main; all merges CI-gated.
