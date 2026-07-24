# Fleet human-only task register (2026-07-11)

The 72 non-delegation-zone / human-only items across the 9 active repos (workflow wq1kdey4c),
grouped by category. These are reserved for Shoval: an autonomous agent must not do them. The
earlier "59" undercounted; the real count of non-delegation-zone items is 72.

## Auth / RBAC / multi-tenancy

- call-analyzer-frontend: OAuth2 authorization-code flow + token handling; RBAC permission model +
  admin bypass; data restrictions by agent/provider/realm.
- agent-call-tracker: webhook HMAC fails OPEN (fix is human-gated per policy though internal/low-crit
  per operator); `/api/agents` + `/api/calls` auth contract; role-sync catalog-vs-per-user (confirm
  with Vlad); corp-home SSO DARK -> LIVE flip.
- seekapa-training-platform: admin role viewing any rep's report (J6/W2.3) — cross-user auth surface.
- widgora: RBAC decision behind the auto-signals 403.

## Secrets / credentials

- campaign-analysis: pasted Bearer token — SCRUBBED locally 2026-07-11 (was untracked, never on
  remote); rotation declined by operator, residual: token still valid until it expires.
- axia-seekapa-cs-agents: store ACS/LiveAgent/Twilio/Telegram/CRM secrets in Key Vault.
- sales-agents: rotate the plaintext market-data API key hardcoded in an ElevenLabs tool config;
  create the KV-linked `sales-agents-secrets` variable group.
- seekapa-training-platform: relocate APP-HEDG-TRAINING-JWT-SECRET from personal to kv-seekapa-apps.
- qc-telephony-api: any rotation of ELEVENLABS_API_KEY / CALLBACK_HMAC_SECRET / KV access.

## Production deploy / pipeline / branch-policy

- widgora: release -> main + deploy (HOLD-ALL); register deploy pipeline + secrets group; Cloudflare
  cutover.
- qc-telephony-api: branch policies on main (build-def 117); any prod Azure resource action; merge +
  deploy + live-smoke.
- seekapa-training-platform: apply prod migrations 019/020; corp-home SSO + role-sync go-live; App
  Insights region move + SWA rename.
- video-understanding: wire automated deploy stages + post-deploy /health gate; SCM/Kudu + Cloudflare
  IP lock; any infra/main.bicep scaling change.
- campaign-analysis: CFSync + Cloudflare allowlist + /health gate; register/retire
  azure-pipelines-intelligence.yml.
- call-analyzer-frontend: Azure Static Web Apps deploy pipeline; corp auth/manager API config values.
- sales-agents: register ADO CI pipeline; Twilio/SIP go-live; any Function App redeploy/rename.

## Destructive git-history (rewrite + force-push, corp-repo, explicit OK each)

- sales-agents: purge ~300MB committed .raw audio via git filter-repo.
- qc-telephony-api: delete the orphaned fix/session-memory-fail-soft branch.
- The 4 repo-in-repo folds: social-media-agent, agent-call-tracker's stray axia copy, Onesignal,
  ui-ux-pro-max-skill.

## Legal / compliance / cost

- sales-agents: AI-disclosure + consent wording, widget T&C, HEDG-vs-Seekapa legal entity; PII
  retention / zero-retention decision.
- widgora: FMP/Finnhub redistribution licensing.
- seekapa-training-platform: HeyGen LiveAvatar ~$3/min budget commitment; new billable ElevenLabs
  agents (W5.3); real Gulf customer PII pipeline (W5.4).

## Architecture / stakeholder decisions

- qc-telephony-api: SessionMemoryService drop-vs-migrate.
- agent-call-tracker: Vite vs Bun.serve for the #489 React migration.
- widgora: DEV-4982 scheduler build-vs-integrate; folding social-media-agent under widgora vs white-label.

## Content / QA human judgment

- axia-seekapa-cs-agents: Variant A escalation wording across 4 languages; OTP v110.1 13-section QA
  sign-off; unset SMTP_TEST_REDIRECT_EMAIL backdoor after.
- sales-agents: human warmth/naturalness listen on the Arabic voice before any real cold call.
- seekapa-training-platform: per-country GCC persona content.
