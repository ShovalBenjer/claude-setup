# ADR-0002 — Subscription OAuth token, not metered API key, for all fleet auth

Status: Accepted (2026-07-23)

## Context
The OS runs a fleet: 22-repo PR reviews, crons, a2a bridges. Two auth paths exist:
`ANTHROPIC_API_KEY` (metered, per-token billing) and `CLAUDE_CODE_OAUTH_TOKEN` (from
`claude setup-token`, billed against the Max subscription). The operator mandate is
$0-external-cost.

## Decision
All harness auth uses the subscription OAuth token. GitHub Actions review workflow
uses `claude_code_oauth_token`. Metered `ANTHROPIC_API_KEY` is used only where a
capability is impossible on subscription and the spend is explicitly approved.

## Consequences
+ The whole fleet runs inside the Max plan; no surprise API bills (the $1.36 Apify
  lesson generalized).
- The OAuth token requires an interactive `claude setup-token` browser approval;
  it cannot be fully headless (a credential re-auth gate blocks pure automation).
- Token expiry/rotation is now an operational task (a health check watches it).
- Subscription rate/window limits, not dollars, become the throttle; crons must
  back off on window exhaustion.
