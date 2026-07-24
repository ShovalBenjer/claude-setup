# Shoval Benjer — 5-Month Engineering Context

> **Window:** 2025-12-08 → 2026-05-08 (≈5 months)
> **Role:** Senior Solution Engineer, i-sdd (Tel Aviv)
> **Email:** shoval.be@i-sdd.com
> **Generated:** 2026-05-08
> **Scope:** every project I touched, what shipped to production, what I built, and the tools that made it possible. Synthesized from `git log` across 5 active Azure DevOps repos, `az` resource inventory in the U-BTech CSP subscription, and the docs/audits/reflections under `~/docs/`.

---

## 1. By the numbers

| Signal | Value |
|---|---|
| Completed PRs authored (Azure DevOps Corp-AI org) | **136** |
| Commits to flagship `axia-seekapa-cs-agents` (5 mo) | **210** |
| Active repos with ≥2 commits (5 mo) | **5** |
| Production-running Azure resources I own | **6** Function Apps + Web Apps (1 stopped) |
| Foundry agents in production | **2** (`seekapa`, `AxiaCS`) |
| Eval pass-rate jump on Seekapa CS agent (v107.3) | **24% → 64%** |
| Dead code removed in single cleanup PR | **−3,997 LOC** (18 dirs) |
| Prompt versions shipped on cs-agents | v97 → v109 (≈12 iterations) |
| Specs / reflections / audits written | **3 audits + 4 specs + 7 reflections + 1 research piece** |

---

## 2. Production deployments I own

All in `AZAI_group` resource group, Sweden Central region, U-BTech CSP subscription.

### Function Apps (Python, Azure Functions runtime)

| App | State | Purpose |
|---|---|---|
| `func-cs-agents-dev` | Running | Chatwoot conversation handler — Seekapa OTP + AxiaCS routing, dispatches to Foundry agents |
| `func-qc-telephony-prod` | Running | Telephony QC pipeline (call analyzer + scoring) |
| `func-training-prod` | Running | Seekapa AI training platform backend |

### Web Apps

| App | State | Purpose |
|---|---|---|
| `COMP-CAMPAIGN-PROD` | Running | Campaign analysis MCP server |
| `mcp-seekapa-tools` | Running | Public Streamable-HTTP MCP server (Claude Desktop / Claude.ai connectors) |
| `COMP-SEEKAPAAITRAININGAPI-PROD` | Running | Seekapa training API (frontend-facing) |
| `app-realtime-monitor` | Stopped | Real-time monitor app (idle / shut for cost) |

### Azure AI Foundry agents

- **Endpoint:** `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai`
- **Agents:** `seekapa` (FAQ + conversation), `AxiaCS` (CS escalation)
- **Models in rotation:** GPT-5.5 (primary), grok-4-1-fast-reasoning (eval), DeepSeek-V3.2 (audit)

### External SaaS surface I run

- Windsor.ai connector inventory: **40 Facebook + 37 Google Ads + 4 LinkedIn + 4 TikTok + 2 Snap + 1 Taboola + 1 Sendinblue** ad accounts wired for cross-brand reporting.

---

## 3. Repos worked on (last 5 months)

Sorted by commit volume in the window.

### `axia-seekapa-cs-agents` — 210 commits (flagship)

The Chatwoot conversation handler that powers Seekapa's customer-service AI. Single-author maintenance + feature dev. This repo is also the worktree under `$HOME` (HOME-as-repo pattern; mitigated via `.claudeignore`).

**Top file-area churn:** `azure-function-crm/` (237 file-touches), `tests/` (172), `docs/` (68), `agent-prompts/` (62), `azure-pipelines.yml` (54), `scripts/` (30).

**Commit-type breakdown:** 68 fix · 32 feat · 22 chore · 10 docs · 8 refactor · 5 ci · 2 perf · 2 test.

**Major themes:**

- **Prompt-engineering ladder.** Iterated through v97 → v101 → v105 → v107 → v107.1 → v107.3 → v108 → v109, each version backed by an eval baseline. v107.3 lifted pass rate from **24% → 64%** by introducing KB v2 alongside the new prompt.
- **Eval infrastructure.** Replaced a broken hand-rolled eval gate with the Foundry SDK auto-eval (PR 149), then inlined evaluation into the Deploy stage via api-key auth to bypass RBAC blocks (PR 151). Cost-bounded to ≤1500 input / ≤120 output tokens per row.
- **CI/CD plumbing.** Source eval keys from per-engineer Key Vault (PR 156), AAD bearer auth for Foundry prompt-sync (PR 154), soft-fail when SP lacks RBAC (PR 155), drop the AIReview stage and dead Codex variables (PR 166).
- **Conversation handler hardening.** Banned-verb deduplication, escalation-aware identity strip, contact extractor (PR 178). Yasha-style sanitizers and v109 Foundry config (PR 165).
- **Yasha collaboration.** v108 yasha intake flow live with agent v113 (PR 184); current branch `feat/v109-yasha-multilingual` continues that arc into multilingual.
- **Refactor / dead-code purge.** Split chatwoot handler into a package (-300 LOC, PR 161). Deleted **18 dead function dirs (-3,997 LOC)** in PR 164.
- **Production observability.** Documented Foundry agent vs application endpoint divergence (PR 167) — the kind of runbook future-me thanks past-me for.

### `campaign-analysis` — 109 commits

MCP server exposing CRM/Chatwoot/OneSignal tools to Claude Desktop and Claude.ai web connectors.

**Recent theme: codex-driven security review.** Eight ranked findings (F-01 through F-08) shipped across two days:
- F-01 enforce Entra federation in Bicep (board mandate)
- F-02 CRM redaction + scoped `crm_get_customer_summary` tool
- F-03 Chatwoot mask PII + gate private-note content
- F-04 per-tool scope matrix on all 21 tools
- F-05 OAuth issuer matches App Service host
- F-06 OneSignal DTO shaping + ACC namespace + null-strip
- F-08 MSI to Key Vault, no env-secret prod fallback

**Protocol work:** added Streamable HTTP transport at `/mcp` (PR 228), RFC 9728 protected-resource metadata + `aud=ISSUER` URL (PR 229), aliased bare `/` to `/mcp` for Claude.ai web connectors (PR 232). This is what made the MCP server actually work end-to-end against Anthropic's clients.

### `seekapa-training-platform` — 107 commits

The training platform backend (FastAPI / Azure Functions). Local repo on disk (no Azure DevOps remote pull on this machine), but `seekapa-training-platform` exists upstream.

**Recent themes:**
- **Build/runtime fixes for Azure Functions.** Pin manylinux2014 wheels to fix GLIBC mismatch on the Function App runtime (PR 205). Bundle Python deps into `.python_packages/` before zip-deploy (PR 197). Add WeasyPrint to `requirements.txt`.
- **CI hardening.** Replace skipif-only `ai_analyzer` test, fix smoke `list-levels` to assert 401 (PR 208). Live-prod smoke against `training.corp-domain.com`.
- **Repo hygiene.** Clean up root dir, archive stale docs, remove dead shared/reference/example/validator modules (PR 198). DB migration 015 column-name fix + commit runbook with prod-server correction (PR 231).

### `social-intelligence-unit` — 90 commits

Video / content pipeline for marketing intelligence. Most activity sat in Feb–Mar.

**Highlights:**
- Apify query expansion + Creative Hub (Sprint 3).
- **Honest data-quality audit:** `feat(data-quality): implement P0 fixes from audit - freshness threshold and template detection` after `docs: comprehensive data quality audit - 640 records, 90% failure rate`. Diagnosed → committed → fixed.
- 4-tier SOTA CI on Azure DevOps with Playwright marketer-journey tests.
- Cohere endpoint fallback + TabPFN scorer + media gate fix.
- Foundry agent orchestration design spec + architecture diagram.
- Consolidated architecture rewrite "with honest audit" — that's how I name docs that won't lie to me later.

### `figma-4-all` — 2 commits (March)

Brief touch on `ashley` UI component: clamp LAND/PORT bleed, simplify Alpha UI.

### Repos I steward but didn't actively edit in window

Visible in the Corp-AI org (28 repos total) and tied to my deploy lane: `aeo`, `aeo-docker-deploy`, `automation-fabric`, `automation-fabric-docker-deploy`, `client-evaluation`, `client-eval-docker-deploy`, `compliance-exam-docker-deploy`, `cs-agents-docker-deploy`, `qc-telephony-api`, `real-time-monitor`, `realtime-docker-deploy`, `sales-agents`, `Seekapa-AI-Assistance`, `seekapa-compliance-exam`, `seekapa-training-docker-deploy`, `sentimark`, `sentimark-docker-deploy`, `taqyeem-broker-website`. Several of these are running production code that depends on flows I built.

---

## 4. Cross-cutting accomplishments

### Eval discipline → measurable agent quality

- Standing up the Foundry-only 4-phase eval pipeline (deterministic gate → smoke 10-row → expanded 40–80 → nightly 80–150) with primary/audit judge separation (`grok-4-1-fast-reasoning` primary, `DeepSeek-V3.2` audit-only).
- Cost ceilings enforced per row to keep judge spend bounded as eval-set grows.
- Specs at `~/docs/specs/2026-04-15-silver-eval-dataset.md` and the v108 yasha intake flow spec.

### Forge Loop — 8-axis weekly self-audit

I score every implementation on 8 binary axes (SPEC, PREMORTEM, RED, GREEN, REFACTOR, COVERAGE, REFLECT, CI BIND) and audit weekly. The audit lives under `~/.codex/automations/prompts/a09-forge-loop-compliance-score.md` and the related skills (`premortem`, `coverage-enforcer`, `heidegger-reflect`) hard-block missing axes when I push code.

### Honest reflections, not vanity write-ups

- 2026-03-22 — chatwoot production hardening
- 2026-03-30 — escalation perf v39
- 2026-04-01 — chatwoot conversation event handler
- 2026-04-13 — v99 session analysis fixes
- 2026-05-04 — A2A v1 + wire gap closure
- 2026-05-04 — Claude setup session structure + wire gaps
- 2026-05-04 — PST extraction Path A run

Every reflection names what worked, what I missed, and the next-action list. They are written for past-me's future-self.

### Audits

- 2026-05-03 dor-cohen-sentimark-email — internal incident write-up
- 2026-05-03 dormancy audit — Azure resource cost / stale-resource check
- 2026-05-07 cs-agent access boundaries — security review

### Specs

- 2026-04-15 silver eval dataset
- 2026-04-28 v108 yasha intake flow
- 2026-05-04 frontier governance axes
- 2026-05-04 PST extraction v1 run

### Research

- 2026-05-07 — AI bot security best practices

---

## 5. Tools and technologies (last 5 months, hands-on)

### Languages / runtimes
- **Python 3.10–3.12** — primary on cs-agents, training, MCP server. `uv` for env management.
- **TypeScript / JS** — MCP servers and tooling. `bun` / `bunx`, never `npm`.
- **Bash 4+** — shell scripting, CI glue, hooks, and (this week) the claude-meme-hooks installer.
- **PowerShell** for Azure CLI scripting on Windows-side bridges.

### Cloud / infra
- **Azure Functions** (Linux Python plan ASP-AZAIPROJECTS) — primary serverless host.
- **Azure App Service Web Apps** for the MCP server, training API, campaign tool.
- **Azure Container Apps + Container App Environments** — `sentimark-env` migration plan (newsletter func to Docker).
- **Azure AI Foundry** — agent CRUD via `azure-ai-projects` SDK, agent runs streamed with reasoning + tool steps.
- **Azure Key Vault + MSI / Entra federation** — board-mandated secret hygiene.
- **Bicep** infrastructure-as-code.
- **Azure DevOps** — Repos, Pipelines (4-tier SOTA CI), `az repos pr` flows.

### AI / agent stack
- **Anthropic Claude SDK** — orchestration model in this loop.
- **OpenAI / Codex CLI (gpt-5.5, codex-5.3)** — executor model. Two-model orchestrator/executor split is a deliberate separation of concerns.
- **MCP (Model Context Protocol)** — built and shipped a Streamable-HTTP server with RFC 9728 metadata for Claude Desktop and Claude.ai web connectors.
- **A2A (Agent-to-Agent)** v1 — sync dispatch bridge between Claude orchestrator and Codex / Foundry agents.
- **DeepEval, Foundry SDK eval, custom JSON schema judges** for agent evaluation.

### Data / ML
- **LanceDB** (vector DB), **sentence-transformers / all-MiniLM-L6-v2** (embeddings).
- **TabPFN** scorer for tabular tasks in social-intelligence-unit.
- **Apify** for scraping orchestration.
- **Cohere** API for fallback retrieval.
- **yfinance / statsmodels / autogluon** for the daily-market-reports rebuild.
- **WeasyPrint** for HTML→PDF (training platform).

### Quality / verification
- **ruff, mypy, pytest** (Python); **ESLint, knip, vitest** (JS/TS).
- **Playwright** end-to-end tests for marketer-journey flows.
- **TDD with vertical tracer bullets** — RED→GREEN per behavior, no horizontal slicing. No mocks for business logic, external services, DB, or filesystem.

### Productivity / dev tooling
- **Claude Code** with custom skills, hooks, sub-agents, A2A bridge.
- **Codex CLI** for second-opinion review and batch test generation.
- Custom skills authored: `commit-push-pr`, `eval-runner`, `red-team-review`, `azure-runtime`, `azure-audit`, `agent-builder`, `coverage-enforcer`, `premortem`, `heidegger-reflect`, `dispatch`, `claude-api`, `simplify`, `humanize`, `voice-explainer`, `visual-explainer`.
- **gh CLI / az CLI** for GitHub and Azure work.
- **Foundry agent CRUD via SDK**; **Microsoft 365 Agents SDK** for Teams/Copilot bridging.

---

## 6. Skills demonstrated (with concrete evidence)

- **Solo-ownership of a production AI agent.** 210 commits in 5 months on `axia-seekapa-cs-agents`, with 12 prompt iterations measured against an eval suite, deployed via my own CI/CD.
- **Eval-driven prompt engineering.** v107.3 took the same agent from 24% to 64% pass rate by attacking the prompt + KB jointly, with eval data to prove the lift.
- **Security hardening under board mandate.** 8-finding codex review on `campaign-analysis` MCP server closed in two days: PII redaction, OAuth issuer assertion, Entra federation, MSI to Key Vault, per-tool scope matrix.
- **Protocol implementation.** Streamable-HTTP MCP transport + RFC 9728 protected-resource metadata + dual-trailing-slash `aud` claim — the MCP server works against Claude Desktop and Claude.ai web connectors because of debugging at this layer.
- **CI/CD remediation under operational pressure.** Manylinux2014 wheel pinning to fix GLIBC mismatch on the Function App; bundling Python deps into `.python_packages/` for zip-deploy; soft-fail of Foundry prompt-sync when SP lacks RBAC; AAD bearer auth migration.
- **Aggressive dead-code removal.** Single PR deleting 18 unused function directories (-3,997 LOC). Routine.
- **Cross-brand ad-tech leverage.** 40 FB + 37 Google Ads accounts on a single Windsor.ai pipe — set up to flag spend outliers across MENA + LATAM regions.
- **Multilingual product work.** Yasha intake flow shipped in v108; v109 multilingual is the current branch. Native Hebrew + Arabic + English handling.
- **Self-measurement / forge-loop discipline.** 8-axis weekly audit, with skills that hard-block pushes when axes are missing.
- **Honest documentation.** Every reflection names what missed, not just what shipped.

---

## 7. What's currently open (active branches / WIP)

On `axia-seekapa-cs-agents`:

- `feat/v109-yasha-multilingual` ← current branch
- `feat/v110-account-verification`
- `feat/callanalyzer-mcp-integration`
- `feat/chatwoot-webhook-handler`
- `feat/align-test-connector-to-production`
- `fix/codex-ci-endpoint`, `fix/codex-foundry-agent`
- `fix/escalation-perf-v39`
- `tmp/stage-align-pr97`

Strategic carryovers (per `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`):

- Marketing-newsletter container migration off the EP1 plan onto Docker on `sentimark-env` (Yasha ask, 2026-05-06 — biggest persistent cost line).
- Daily market reports v2 rebuild on gpt-5.4-mini via Foundry + yfinance / statsmodels / autogluon (Oded's `func-market-reports-prod` was stopped 2026-05-06).
- Layer-7 observability buildout: Stop-hook → JSONL session log → embedding store (LanceDB) → DeepEval LLM-judge sample (deferred until ≥100 sessions logged).

---

## 8. Verification sources

Everything in this document is reproducible against:

- **Git history:** `git -C ~ log --since=2025-12-08 --pretty=format:'%h %ai %s'` and equivalent under `~/projects/{campaign-analysis,seekapa-training-platform,social-intelligence-unit}`.
- **Azure DevOps PR count:** `az repos pr list --org https://dev.azure.com/Corp-domain --project Corp-AI --status completed --creator shoval.be@i-sdd.com --query 'length(@)'` → **136**.
- **Azure resource inventory:** `az functionapp list`, `az webapp list` against the `U-BTech - CSP (Z-Online)` subscription (sub id `08b0ac81-a17e-421c-8c1b-41b59ee758a3`), resource group `AZAI_group`.
- **Foundry endpoint:** `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai`.
- **Docs:** `~/docs/audits/`, `~/docs/specs/`, `~/docs/reflections/`, `~/docs/research/`.
- **Master plans:** `~/CLAUDE-CODE-MASTER-PLAN-2026-05-03.md`, `~/claude-setup-master-plan-2026-05-02.md` (superseded).

---

*This document is meant as a portable context page — for performance reviews, role conversations, or my own future-self orientation. It will go stale; the verification commands above will not.*
