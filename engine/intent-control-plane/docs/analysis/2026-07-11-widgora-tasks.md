# Widgora task synthesis (2026-07-11)

Source: read-only fleet inventory (workflow wq1kdey4c). Widgora = `~/projects/ORM-AGENT/widgora`
(folder in the ORM-AGENT umbrella repo; one `.git` at the umbrella root; branch
`feature/widgora-release`; ~670 tests; has its own `docs/prd` + `docs/TODO.md`). This reconciles the
scattered widgora audits into one prioritized list. Caveat from the inventory: the widgora docs
contradict each other on done-vs-open, verify against live prod before trusting any status label.
The #1 quick win called out is D1.

## Delegable, HIGH

- D1: Earning Calendar column-overflow (widget id=13, Amit-flagged) — self-contained responsive fix.
- Security quick-wins (each small, testable, app-level): X-Content-Type-Options header; drop the
  unsanitized SVG upload path; admin token-rotate action; OAuth state param; SSRF DNS-rebind pin +
  size-cap + HMAC; per-job Postgres advisory lock.
- Diagnose + fix the auto-signals DELETE 403 in prod (capture the exact route/RBAC mismatch; the
  policy call itself is human-only, see human list).
- Postgres 3B hardening: TIMESTAMPTZ/NUMERIC typing, FK on every relation, composite/partial
  indexes, Atlas migrations, keyset pagination (dev/CI only, no prod provisioning).
- Wire the pandera FMP boundary validator (0 call sites today) into the sync jobs.
- Build a real local-vs-prod parity seed (wire `scripts/pull_prod_seed.sh` + `load_local_seed.py`),
  named repeatedly as the root cause of prior failed prod demos.
- Fix the signals widget empty feed + repair the "Generate now" action (repro: signals=0 locally).

## Delegable, MED

- Fat-file decomposition (gated by the test suite): `routes_widgets.py` (~931 LOC / 56 routes) into
  a CRUD factory; split `widget_store.py` (~781 LOC).
- Replace bare `os.environ` in `config.py` with pydantic-settings BaseSettings.
- Fix migration 0008's missing `.nontxn` CONCURRENTLY companion file.
- Add gitleaks secret-scan to CI (fail-on-hit).
- Prompt-injection shield around FMP news text flowing into the blog LLM prompts (input delimiting).
- Add hypothesis property/fuzz tests (gate_article, fmp.validate, article-JSON never crash).
- Merge `chore/widgora-pipeline-gates` (semgrep advisory SAST + 68% coverage floor) into CI.
- Publish one prod instance of each widget kind with zero live instances today (quote-cards,
  market-movers, trend-meter, IPO, auto-signals, overview).
- DEV-5080: build the News/Blog widget kind end to end (spec sketched at `docs/dev-5080/SPEC.md`).
- Blog publish/discovery: `/blog` index + sitemap (publishing the 0/62 held articles is human, Epic 5 HELD).
- SEO/GEO: analytics_snapshots table + tabs, Search Console / Bing / GEO-citation checks.

## Delegable, LOW

- D2/D3/D5/D6: RTL bidi punctuation, paginator digit order, blank NatGas icon, "Untitled" default
  title (some may already be landed at 10b1750, verify first).
- SOTA UI polish (operator sign-off only for visuals, not build): count-up KPI, delta caret glyph,
  hover-expand sparkline, glass tooltips, prefers-color-scheme dark/light.
- Reconcile prefers-reduced-motion (SOTA audit says missing, PRD WS-4 claims done).
- Rebase the stale `feat/admin-ui` cluster onto post-reorg main.
- Reseed real asset data for market-movers/quote-cards (currently synthetic tickers).

## Human-only (reserve for Shoval)

- Land `feature/widgora-release` -> main and deploy (deploy policy is explicit HOLD-ALL).
- Real brand logos: replace the 5 operator-rejected monogram placeholders.
- corp-home SSO registration (app_id/app_secret, Entra-group -> access:widgora).
- Register `azure-pipelines-deploy.yml` as a live ADO pipeline + set the widgora-secrets var group.
- Cloudflare origin-lock + custom `widgets.*` domain cutover, comp-widgora-prod SKU/capacity.
- The RBAC policy decision behind the auto-signals 403 (who may delete delivery endpoints).
- FMP/Finnhub market-data redistribution licensing (#18 in the security triage).
- DEV-4982 scheduler build-vs-integrate fork; DEV-4960 widgora-feed-into-SMA-discovery.
- Wiring CodexReview into widgora CI (needs an azureServiceConnection credential provisioned).
