# Shoval Benjer — CV Project Inventory (per-project bullets + tech stack)

> **Window:** the projects under `~/projects/`, plus `~/.claude/skills/`, `~/.codex/automations/`, and the production resources in `AZAI_group`.
> **Generated:** 2026-05-28
> **Source of truth:** `~/docs/SHOVAL-BENJER-5MO-CONTEXT-2026-05-08.md`, project CLAUDE.md / AGENTS.md / INDEX.md / README.md, Azure DevOps pipelines, Foundry agent snapshots.
> **Companion doc:** `~/docs/SHOVAL-FIT-ANALYSIS-2026-05-08.md` (positioning advice).

This is a CV scratchpad — one section per project. Each section has: what it is · what's impressive (lead with these on the CV) · skills/tech stack chips. Five cross-cutting threads are emphasized everywhere they appear: **Jira**, **Outlook / Copilot Studio**, **Azure AI Foundry**, **Microsoft Fabric / Power BI**, **Azure Pipelines (4-tier SOTA CI)**.

---

## 0. Cross-cutting threads (call these out on every CV variant)

- **Azure AI Foundry agents** in production — `seekapa`, `AxiaCS`, `Devops-reviewer` (Codex-Reviewer), Call-analyser-agent. Endpoint: `https://brn-azai.services.ai.azure.com/api/projects/seekapa_ai`. CRUD via `azure-ai-projects >= 2.0.0`. Models in rotation: GPT-5.5, gpt-5.4-mini, GPT-5.3-codex, grok-4-1-fast (eval), DeepSeek-V3.2 (audit).
- **Azure DevOps Pipelines — 4-tier SOTA CI pattern**: Tier 1 lint/types/unit (<2 min PR gate) · Tier 2 PR integration + AI review · Tier 3 nightly fuzz/load/mutation · Tier 4 deploy + smoke. Workload Identity Federation / OIDC service connections (e.g. `managecorpairegistry` ID `6d2cd8b6-…`). Branch policy: `feature/* → stage → main`, deploy only via CI.
- **Jira integration via Atlassian MCP**: `i-sdd-ai-shoval.atlassian.net`, default project `KAN`. Wired into the `Devops-reviewer` Foundry agent (v6) for cross-system linkage (ADO PR ↔ Jira key). Also have a local `jira-task-draft` skill for markdown-first draft → manual paste.
- **Outlook + Copilot Studio + M365 surface**: WorkIQMail / WorkIQTeams / WorkIQOneDrive / WorkIQCopilot MCP servers wired into the `Devops-reviewer` Foundry agent. Five Copilot Studio bot definitions authored (`General-Assistant`, `HR-Talent-Strategy-Assistant`, `Tobby`, `Stacy`, plus templates). Daily Market Overview PDFs distributed via Outlook.
- **Microsoft Fabric + Power BI**: planned BI layer of the centralized Marketing MCP (Fabric + Dataverse) per `~/.claude/projects/-home-shovalbe/memory/project_centralized_marketing_mcp.md`; Power BI reference workflow doc + `_corp-powerbi-probe` repo; BI dashboard forensic audit + reconciliation for Liron.
- **Languages**: Python (`uv`), TypeScript (`bun`), C# / .NET 10 (ASP.NET Core 9 Minimal APIs), Bash, PowerShell, Bicep, SQL.

---

## 1. `axia-seekapa-cs-agents` (cs-agent / Seekapa CS) — flagship

**What it is.** Production Chatwoot customer-service agent for Seekapa (Seychelles-regulated forex broker, GCC + LATAM markets). WhatsApp + Telegram inboxes, no test env — every commit is live.

**What's impressive (lead with this on the AI Engineer CV).**
- **210 commits in 5 months · 136 PRs across the Corp-AI org · sole owner of a production multilingual agent.**
- **Eval pass-rate lifted 24% → 64% (v107.3, KB v2)** with a cost-bounded eval pipeline (≤1500 input / ≤120 output tokens per row), grok-4-1-fast as primary judge + DeepSeek-V3.2 as audit-only.
- **12 prompt versions shipped** (v97 → v109) under TDD with vertical tracer bullets — no mocks for business logic, external services, DB, or filesystem.
- **Yasha v108 multilingual intake flow** live as agent v113. Current branch `feat/v109-yasha-multilingual` adds AR/ES/PT identity-guard + pre-classifier + repetitive-failure cross-turn counting.
- **Dead-code purge:** single PR deleting 18 unused function directories (−3,997 LOC).
- **CI pipeline ID 121** on `dev.azure.com/Corp-domain/Corp-AI/`; deploy only via CI (no `func azure functionapp publish` from CLI).
- **Foundry-only 4-phase eval pipeline** (deterministic gate → smoke 10-row → expanded 40–80 → nightly 80–150) inlined into the Deploy stage via api-key auth to bypass RBAC blocks (PR 151).
- **Pre-classifier + AR/ES/PT sanitizer** in handler code (PR 211); v109 LIVE on Foundry as `seekapa:115` (`instr_len=16761`) since 2026-05-03.

**Tech stack.** Python 3.11 · Azure Functions (Linux Python ASP-AZAIPROJECTS plan) · Chatwoot · CRM via MySQL (PandaTS, read-only) · Azure AI Foundry agents (`seekapa`, `AxiaCS`) · Azure Key Vault (`kv-seekapa-apps`) · Azure DevOps Repos + Pipelines · DeepEval · pytest · `ruff` + `mypy` · Foundry SDK auto-eval (AIAgentConverter, azure-ai-evaluation) · GPT-5.5 / grok-4-1-fast / DeepSeek-V3.2 · `uv` · `bun`.

---

## 2. `campaign-analysis` (FTD analysis platform + Call-analyser-agent + RL agent)

**What it is.** FTD (First-Time Deposit) analytics + Call-analyser-agent for Seekapa. Stakeholders: Liron (COO), Amit (DBA), Yasha (call quality). FastAPI MCP server (`COMP-CAMPAIGN-PROD`) + Foundry agent + offline RL policy.

**What's impressive.**
- **109 commits · the codex-driven 8-finding security review closed in 2 days** (Entra federation in Bicep, PII redaction, OAuth issuer matches App Service host, OneSignal DTO shaping, MSI to Key Vault — no env-secret prod fallback).
- **Streamable-HTTP MCP transport at `/mcp` + RFC 9728 protected-resource metadata + `aud=ISSUER` URL** (PRs 228/229/232). Server works end-to-end against Claude Desktop and Claude.ai web connectors — most teams have not shipped this.
- **Call-analyser-agent** in Foundry: 5 function-calling tools (`get_customer_calls`, `transcribe_call`, `get_transcription`, `translate_transcript`, `query_transcript`), 15-layer call quality analysis prompt, batch ELT for 738+ accounts via Azure OpenAI Global Batch (≈10× cheaper than per-call agent).
- **STT = ElevenLabs Scribe v1** (11.1% WER on Arabic FLEURS) → Azure OpenAI GPT-5 translation (ar/es/pt → en/he) via `func-qc-telephony-prod` → PostgreSQL `qc_analyzer.calls`.
- **CallAnalyzer API hardening** documented to Yasha-grade depth: `X-Api-Token` whitespace trap, `realmId` (camelCase) bug — all verified against the live server.
- **Foundry-native `evals/` skeleton** with `AIAgentConverter` + `azure-ai-evaluation` SDK — 4 built-in evaluators (IntentResolution, TaskAdherence, ToolCallAccuracy, Groundedness) + custom `DataAccuracyEvaluator` (5% relative tolerance, `rapidfuzz` fuzzy numeric match in cloud version). CI gate blocks merge to `stage` if any alpha threshold breached.
- **Ad-hoc Blob+SAS workaround** for the M365 Copilot file-type whitelist (Foundry agent reads xlsx/csv via 1-hour read-only SAS URL on `stsentimarkv2/callanalyzer-uploads`, downloads with curl-UA spoof for Cloudflare 1010).
- **Power BI / BI surface for Liron:** Beyond-CPA Player-Focused Marketing Metrics brief, BI Dashboard Discrepancy Report, Liron workbook handover (2026-05-17), Full-Funnel Intelligence Brief.

**Tech stack.** Python 3.11 · FastAPI · MCP (Streamable HTTP, RFC 9728) · Azure App Service Web App · Azure AI Foundry agents · Azure OpenAI Global Batch API · ElevenLabs Scribe v1 · GPT-5.4 · PostgreSQL · Azure Blob Storage (`stsentimarkv2`) · Azure Key Vault (`kv-shoval`, `kv-seekapa-apps`) · `azure-ai-projects >= 2.0.0b4` · `azure-ai-evaluation >= 1.16` · `httpx[http2]` · `pyjwt[crypto]` · `pandas` · `matplotlib` · `openpyxl` · `rapidfuzz` · `respx` · `hypothesis` · Power BI · Unovis (`@unovis/ts`, `@unovis/react`) · Next.js 14 · Azure DevOps Pipelines.

---

## 2a. `campaign-analysis/outputs/2026-05-27/business-rl-agent-findings-2026-05-27.md` (sim2CRM + Call Center RL policy)

**What it is.** A **local aggregate-only offline RL / contextual-bandit run** that learns the best next-best-action per state across the **call center × paid-media platform** funnel — *not* a Foundry deployment yet, deliberately local so no PII / transcripts / Foundry upload was involved.

**What's impressive (lead with this on the Data Scientist & AI Product Analyst CVs).**
- **Trained a policy on real source population: 10,260 accounts · 7,284 graded calls · 251 FTDs · 2.45% aggregate FTD rate.**
- **Reward design with hard-breach penalty** distinguishes *risky deposit-push / overpromise* talk-tracks from *compliance-safe* ones. The policy correctly stops recommending `risky_deposit_push` once the reward penalizes breaches — except in one degenerate pocket (`Meta / answered_band=11+`, ftd 36.59%, hard_breach 78.0%) that the policy flags rather than executes.
- **Counterfactual reasoning explicit:** "High-touch follow-up only looks good after 11+ answered conversations — but this is likely reverse causation: hot leads answer more. Treat as a prioritization signal, not proof that more calls cause deposits."
- **State-action recommendations are concrete and dollar-grounded.** E.g. `platform=Google, answered_band=0 → dial_no_answer` (n=163, ftd_rate=4.29%, reward=0.056, hard_breach=0.0%). Top supported segment: `TikTok / Saudi Arabia` at $51.86 net deposit per lead.
- **Honest scoping decision documented:** the deployable next-best-action is **triage + compliance-safe talk-track selection, not autonomous sales execution.** This is the "Lead-To-Money-Decision" lens — one executable, owned, dated action — applied to its own output.
- **Why not Foundry yet:** explicit RBAC + approved-training-dataset gate is named in the writeup, so the work doubles as a **training/eval spec** for the future Foundry RL deployment.
- The local policy bridges offline batch analytics → online next-best-action — the standard "sim2real" / "sim2CRM" pattern, framed in terms paying stakeholders (Liron, sales floor managers) can act on.

**Tech stack.** Python · pandas · NumPy · offline RL / contextual bandits (tabular) · reward shaping with hard-breach constraint · platform-grain attribution (Meta / Google / Taboola / TikTok / Snapchat / `<null>`) · GCC + LATAM geo cuts (Saudi Arabia, UAE, Qatar, Kuwait, Jordan) · CRM funnel modeling (FTD, net deposit per lead, answered conversation bands) · Windsor.ai spend (period-matched ROAS) · stakeholder-ready markdown report under `outputs/YYYY-MM-DD/`.

---

## 3. `azure-devops-agent` (Devops-reviewer / Codex-Reviewer on Foundry) — **Jira + Outlook + M365 thread headliner**

**What it is.** Azure-Foundry agent that reviews PRs on `dev.azure.com/Corp-domain` and *also* manages Jira issues on `i-sdd-ai-shoval.atlassian.net`. Runs on `gpt-5.3-codex-CI-Reviewer` with `reasoning.effort=high`. Six MCP tools wired in. Auto-invoked on PRs with >5 source-file changes.

**What's impressive (lead with this on every CV — it is the most "enterprise stack" project).**
- **Six MCP servers wired to one Foundry agent**: `Corp_domain_Devops` (`mcp.dev.azure.com/Corp-domain`) · `WorkIQCopilot` (M365) · `WorkIQMail` (Outlook) · `WorkIQTeams` · `WorkIQOneDrive` · plus Code Interpreter.
- **Jira MCP integration (v6, proposed and verified):** explicit cross-system linkage rules — when an ADO PR or work item references a Jira key (`KAN-####`), surface in Result; when a request mentions both `#1234` (ADO) and `KAN-1234` (Jira), confirm before linking (do not assume they're the same item).
- **Risky-action gate** extended to Jira transitions, assignee changes, and bulk JQL edits — explicit confirmation + target keys shown before execution.
- **Cross-platform routing policy** documented: ADO MCP for repos/PRs/pipelines/work items/tests/wiki · Jira MCP for issues/sprints/boards/JQL/comments/transitions · WorkIQCopilot for internal M365 discovery when source unknown · WorkIQTeams/Mail/OneDrive for collaboration · Code Interpreter for analysis.
- **Live Foundry snapshot diff workflow:** `verify-v6.sh` + `watch-and-publish.sh` to compare v5 → v6 instruction strings before publishing.
- **PPT briefing artifact** (`azureops-copilot-agent.pptx`) — stakeholder-ready.

**Tech stack.** Azure AI Foundry (Agents v2 / Responses API) · `azure-ai-projects >= 2.0.0` · Atlassian MCP (Jira Cloud, JQL, sprints, boards, transitions) · Microsoft 365 Agents SDK · Copilot Studio · WorkIQ M365 MCP suite (Mail/Teams/OneDrive/Copilot) · GPT-5.3-codex · Bash · Azure DevOps MCP (`mcp.dev.azure.com`).

---

## 4. `copilot-agent` (Copilot Studio bot definitions)

**What it is.** Five Microsoft Copilot Studio bot definition packages, authored directly in the platform's YAML schema (`kind: BotDefinition`, `template: kickStartTemplate-1.0.0`).

**What's impressive.**
- **Five distinct Copilot Studio agents shipped:** `General-Assistant` (Generative Actions enabled, CRM lead-comment instructions) · `HR-Talent-Strategy-Assistant` · `Tobby` · `Stacy` (zipped, sealed) · plus template-content topics (`MultipleTopicsMatched`, `OnError`).
- **Authentication mode `Integrated`** with `accessControlPolicy: GroupMembership` — wired to Entra ID groups, not anonymous.
- **Generative Actions enabled** on the General-Assistant — the Power Platform's LLM-driven action planner that lets the bot pick actions across connected systems without hand-coded topics.
- Custom dialog topics built in the Copilot Studio expression language (`init:Topic.IntentOptions`, `=System.Recognizer.IntentOptions`, `Topic.NoneOfTheseDisplayName`, etc.) — most "Copilot Studio users" never go below the canvas.
- Companion **CRM-lead-comment instructions** doc grounding the General-Assistant in i-sdd's lead-flow domain.

**Tech stack.** Microsoft Copilot Studio · Power Platform · YAML BotDefinition schema · Microsoft Entra ID (GroupMembership ACL) · Generative Actions · `pac` CLI (Power Platform) · M365 Agents SDK.

---

## 5. `seekapa-training-platform` (Voice training for sales reps)

**What it is.** Voice-based training platform for Seekapa sales reps with ElevenLabs AI voice agents, real-time scoring, and performance analytics. **15 training levels** (5 EN + 5 AR + 5 ES-LATAM). Two backends — Function App `func-training-prod` + frontend SPA `COMP-SEEKAPAAITRAININGAPI-PROD`.

**What's impressive.**
- **107 commits** in 5 months · WCAG 2.1 AA accessibility compliance baked in · Playwright marketer-journey E2E suite.
- **Real prod-runtime fixes:** pin `manylinux2014` wheels to fix GLIBC mismatch on Azure Functions runtime (PR 205) · bundle Python deps into `.python_packages/` before zip-deploy (PR 197) · live-prod smoke against `training.corp-domain.com` (PR 208).
- **Azure Pipelines 3-tier flow** documented in `azure-pipelines.yml`: Tier 1 (PR gate <2 min) · Tier 2 (AI review) · Tier 3 (deploy + smoke). Service connection via Workload Identity Federation (`managecorpairegistry` ID `6d2cd8b6-…`).
- **Routing matrix per task type** (in CLAUDE.md): content → GPT-5 Pro · UI/UX → Gemini + `design-to-code` · code → Codex Max · a11y → Codex Max with a11y focus · learning design → GPT-5 Pro.
- **DB migration runbook with prod-server correction** (PR 231) — migration 015 column-name fix surfaced *after* deploy and corrected in the runbook.

**Tech stack.** React + Vite (frontend) · Azure Functions v1 + Python 3.11 (backend) · ElevenLabs voice agents · PostgreSQL (training DB) · Playwright · WeasyPrint (HTML→PDF) · Azure DevOps Pipelines (3-tier) · `bun` · `uv` · `func` Core Tools · Docker · GPT-5 Pro / Gemini / Codex Max routing.

---

## 6. `social-intelligence-unit` (SIU — marketing content/creative pipeline)

**What it is.** Social signal + creative pipeline. Apify-driven scraping, signal scoring (`0.0..5.0`, tier `S|A|B|C`, confidence `high|degraded`), creative-hub generation, brief→ad→experiment workflow.

**What's impressive.**
- **90 commits · honest data-quality audit:** `feat(data-quality): implement P0 fixes from audit — freshness threshold and template detection` shipped after `docs: comprehensive data quality audit — 640 records, 90% failure rate`. Diagnose → spec → fix in one week.
- **4-tier SOTA CI on Azure DevOps** (Tier 1 lint/types/unit <60s · Tier 2 PR integration/regression <5m · Tier 3 nightly fuzz/load/chaos + mutation · Tier 4 deploy). Schema → freshness → geo → relevance → media quality gate sequence.
- **Architecture documents under source-of-truth discipline:** `SIU_SOURCE_OF_TRUTH.md` is the *authority*; ADR records under `docs/adr/`; live execution tracker; unified architecture paper v3.
- **Geo policy explicit:** key priority markets `SA|AE|QA|BR|MX|AR`, broader allowlist GCC + LATAM — not "we'll figure it out later".
- **Cohere endpoint fallback + TabPFN scorer + media gate fix** in one rolling iteration.
- **PostgreSQL migration plan + professional-grade Azure pipeline architecture doc.**

**Tech stack.** Python 3.12 (`uv`) · TypeScript/Node 20 (`bun`) · Apify · TabPFN (tabular scorer) · Cohere (retrieval fallback) · SQLite (dev) → PostgreSQL (target) · Pydantic (boundary validation) · Playwright · `ruff` + `mypy` · Azure Container Apps + ACR · Azure DevOps Pipelines (4-tier).

---

## 7. `qc` (Telephony QC — `func-qc-telephony-prod`)

**What it is.** Telephony QC pipeline. Two sub-projects: `qc-telephony-api` (translate + Q&A `ar/es/pt → en/he` via Azure Functions on `func-qc-telephony-prod`) and `qc-call-analyzer` (full audio pipeline + 15-layer scoring + UI).

**What's impressive.**
- **ElevenLabs Scribe v1 STT** (11.1% WER on Arabic FLEURS) + **Azure OpenAI GPT-5** translation pipeline · PostgreSQL `qc_analyzer.calls` storage.
- **Liron's business request (2026-03-19)** turned into a working pipeline + Yasha-domain-expert review loop for scoring thresholds.
- **15-layer call-quality analysis** schema · agent scorecard generation · matplotlib chart pack (12 charts in `callanalyzer_pipeline.py`, 45K LOC).
- **Forge-loop discipline** enforced via `~/.claude/rules/forge-loop.md` — BRAINSTORM → RED → GREEN → REFACTOR → VERIFY → REFLECT → REVIEW.

**Tech stack.** Python 3.11 · Azure Functions · Azure OpenAI (GPT-5) · ElevenLabs Scribe · PostgreSQL · `pandas` + `matplotlib` + `openpyxl` · VCR.py (no mocks for API recordings) · `uv` · Playwright.

---

## 8. `ORM-AGENT` (Real-time social comment moderation)

**What it is.** Real-time AI moderation of comments on **organic posts + paid ads** across Facebook, Instagram, and X. Replaces the manual "check pages every few hours" loop for Mohammad Da (i-sdd Social Media Manager). Multilingual EN/AR/HE/ES.

**What's impressive.**
- **Fork of Microsoft Foundry's `microsoft-foundry/foundry-agent-webapp` template** — auth (Entra ID app reg via Bicep), SSE chat, Foundry SDK, OBO flow, App Insights all pre-wired. Deployed via `azd up` to Azure Container Apps.
- **ASP.NET Core 9 Minimal APIs** (C#) — not yet-another-FastAPI. `/api/webhook/meta` + `/api/webhook/x` with HMAC verification, dedupe, Service Bus enqueue, `BackgroundService` worker.
- **Knowledge Base reuse**: 9 sheets · ~3,200 EN/AR/ES curated canned replies (`Celine's Draft`, `Ticket Canned Responses EN-AR`, `Canned Responses EN-ES`, etc.) indexed into Azure AI Search OR Cosmos vector index, retrieved top-k by semantic similarity, then **adapted** by Foundry agent (pick + adapt — not freeform generation).
- **Severity classifier** (`good review` / `complaint` / `misinformation` / `abusive language & hatred`) gates auto-reply vs. human review.
- **Three-platform fanout** (FB, IG, X) — Meta Graph API + Webhooks for FB/IG; X API v2 with filtered-stream / account-activity for X.

**Tech stack.** ASP.NET Core 9 Minimal APIs (C#) · .NET 10 SDK · Azure Container Apps + ACR · Microsoft Entra ID (app reg via Bicep) · Azure Service Bus topic (`orm-events`) · Azure AI Search OR Cosmos DB vector index · `azd up` (Azure Developer CLI) · Bicep IaC · App Insights · Foundry SDK · Meta Graph API · Instagram Graph API · X API v2 · OnBehalfOf (OBO) flow.

---

## 9. `HR-agent` (Talent sourcing + candidate evaluation)

**What it is.** Structured decision support for talent acquisition at Be Z Online. Seven modes: Role Design / Candidate Analysis / Candidate Comparison / Communication / Enrichment Planning / Candidate Sourcing / Company Sourcing.

**What's impressive.**
- **Apify LinkedIn enrichment pipeline** (`apify_linkedin_profiles_20260406.json` — 1MB of structured profiles, plus `all_candidates_links.json`).
- **Email Campaign Manager Sourcing Report** (xlsx) — ad-tech-flavored DS hiring funnel for the i-sdd marketing org.
- **30-page deep-research report** (`research_report_20260405_hr_sourcing_pipeline.md`) — comparative analysis of sourcing tools + Apify actors + enrichment APIs.
- **Evidence-only assessment policy**: "agent does not make hiring decisions, does not rank or score individuals personally" — all outputs require human review. Compliance-first DS posture.

**Tech stack.** Apify (LinkedIn Profile Detail actor) · OpenAI / Azure OpenAI · structured JSON output schemas · markdown report pipeline.

---

## 10. `video-understanding` (Trading-content video QA + auto-bead)

**What it is.** Video understanding pipeline for trading content. Streamlit UI + `extractor/bot/main.py` + Telegram bot via `Shoval/V-A-PIPELINE-KEY`. Web App `app-video-understanding-prod` (Managed Identity `363713a8-…`).

**What's impressive.**
- **Lint + test Azure Pipeline** documented to explicitly NOT build/push/deploy — re-add only when ACA deployment wanted. Cost-aware CI design.
- **Service connection + ACR borrowed from `campaign-analysis` pipeline** (proven working in Corp-AI project) — pattern reuse across repos.
- **Read-only / no-mutation policy** — scheduled Codex runs are review and bead-creation; do not deploy or mutate Azure resources without explicit human approval.
- ACR is `sentimarkregistry` (correcting earlier `acrazaivideogen` assumption).
- PRs #270 merged, #271 + #272 pending (per memory).

**Tech stack.** Python 3.12 (`uv`) · Streamlit · Telegram bot · ElevenLabs (audio + video composition) · Azure Web App · Azure Container Registry (`sentimarkregistry`) · Azure DevOps Pipelines.

---

## 11. `video-generations` (ElevenLabs Flows — Gulf Gold UA pipeline)

**What it is.** **15-node ElevenLabs Flows DAG** building the "Gulf Gold UA v2" video pipeline (Avatar + lipsync + B-roll + composition + upscale).

**What's impressive.**
- **First-principles documentation** of ElevenLabs Flows (public-alpha since March 2026) for non-experts — from concept ("it's NOT a timeline editor, it's NOT a chatbot, it's a DAG") through to a shippable Gulf-UA video.
- 15-node visual pipeline · non-destructive run model · per-node re-execution.
- Bilingual creative work for the GCC / Arabic UA audience.

**Tech stack.** ElevenLabs Flows · ElevenLabs Voices (`nano-banana-2`, `seedance-2-0`, `sync-3`) · Gemini Generated Image · DAG-based media generation.

---

## 12. `openai-usage-audit` (FinOps + compliance log ingest)

**What it is.** Local tooling for three audits: (1) OpenAI API usage and cost by project/user/model, (2) ChatGPT Compliance Logs ingestion for raw prompt/output records, (3) domain classification and token-equivalent cost reporting.

**What's impressive.**
- **Two distinct OpenAI surfaces** wired up correctly: `OPENAI_ADMIN_KEY` for org usage/cost endpoints + `COMPLIANCE_API_KEY` for ChatGPT Compliance Logs Platform.
- **Sensitive-data discipline** — raw compliance logs may contain user prompts/outputs/filenames/sensitive business content; `data/raw/` access is restricted.
- **Pricing JSON pinned** at a date (`pricing.openai.standard.2026-04-28.json`) for reproducibility.
- Probe / live-probe / collect commands with explicit event-type plumbing (`CONVERSATION_LOG`).
- **FinOps lens** — exact thing CFO / governance wants visibility into.

**Tech stack.** Python · `uv` · OpenAI Admin API · ChatGPT Compliance Logs Platform · domain rule classifier · JSON pricing tables · pytest.

---

## 13. `claude-meme-hooks` (DevEx side project — public-portfolio candidate)

**What it is.** Open-sourced Claude Code hooks system that plays meme clips on workflow lifecycle events (test fail → Thanos · recovery → Matrix dodge · large diff → slap bet · Friday deploy → warning). 49 clips total, 400×260 popup, 60s cooldown.

**What's impressive (lead with this on the GitHub public profile per `SHOVAL-FIT-ANALYSIS:144-156`).**
- **Reusable signal-detection pattern beyond the memes**: alerting on diffs >500 LOC (scope creep), turn-count ≥ 20 (agent stuck — distinct from "working hard"), workflow phase transitions (RED→GREEN→REFACTOR), Friday-afternoon deploy nudges.
- **Hook system architecture** documented for a wider audience — `PostToolUse` + `Stop` hooks reading tool JSON from stdin, pattern-matching, calling `ffplay`.
- **yt-dlp `--download-sections "*1:23-1:28"`** for surgical clip-cutting · `memes.json` event registry · `download-memes.sh` batch downloader.
- **3-hour sourcing pass** for 49 clips — productivity story is publishable.

**Tech stack.** Bash · `yt-dlp` · `ffplay` (FFmpeg) · JSON event registry · Claude Code hooks API · public GitHub repo · MIT license.

---

## 14. `daily-marketing-overview` (Daily market report → Outlook delivery)

**What it is.** Daily Market Overview PDF pipeline delivered to Oded Ben Yair via Outlook. Sub-projects: `automation-fabric/`, `market-daily-reports/`. Reference baseline for the daily-market-reports v2 rebuild on `gpt-5.4-mini` + yfinance + statsmodels + autogluon (per memory: Oded's `func-market-reports-prod` was stopped 2026-05-06).

**What's impressive.**
- **Outlook-distributed PDF artifact** — example: `Daily Market Overview - January 26, 2026 - Oded Ben Yair - Outlook.pdf`.
- **Asset validation report** + 26-Jan / 29-Jan screenshot eval batches (multi-day visual regression).
- Source/AppsFlyer links inventory (`Appsflyer_Links.{csv,pdf,xlsx}`) — attribution side of the pipeline.

**Tech stack.** Python · Azure Functions (`func-market-reports-prod` — now stopped, v2 rebuild planned) · yfinance · statsmodels · autogluon · matplotlib · WeasyPrint (PDF) · Outlook distribution · AppsFlyer · Azure DevOps Pipelines.

---

## 15. `compliance-exam-docker-deploy` (Seekapa compliance exam orchestration)

**What it is.** Dockerized Azure Functions deployment for the Seekapa compliance exam flow. Twelve named functions including `start_exam`, `evaluate_exam`, `generate_report`, `list_exams`, `send_report`, `sync_conversations`, `webhook_exam`, `get_exam_result`.

**What's impressive.**
- **Docker-deploy pattern for Azure Functions** — pairs the `seekapa-compliance-exam` codebase with deployment artifacts.
- **`azure-pipelines.yml` + `docker-compose.yml` + `host.json` + `requirements.txt`** all checked in — full CI surface.
- Twelve functions composed into one exam flow; webhook + sync + report all wired.

**Tech stack.** Python · Azure Functions (Linux container) · Docker · Azure DevOps Pipelines · Webhook receivers · Azure Storage.

---

## 16. `openclaw-poc` (Foundry + Telegram + ACA scale-to-zero PoC)

**What it is.** Telegram-only OpenClaw PoC routing through Foundry (`gpt-5.2-chat2`) + Azure Container Apps with scale-to-zero (min replicas = 0, idle = $0).

**What's impressive.**
- **Honest model-fallback discipline:** Kimi K2 / 2.5 not in `brn-azai` catalog as of 2026-04-20, so fell back to GPT-5.2 fallback. Did not pretend Kimi was working.
- **ACA free grant** (180k vCPU-sec + 360k GiB-sec/month) sized for the PoC — explicit cost reasoning.
- Secrets via Azure Key Vault → ACA secret refs (no `.env` in production).
- **What's NOT yet wired** documented up-front (Composio Hobby tier, camoufox scraping, Kimi 2.5 custom deployment) — honest scope.

**Tech stack.** Python · Azure Container Apps · Azure AI Foundry (`gpt-5.2-chat2`) · Telegram Bot API · Docker · Azure Key Vault · `azd` CLI.

---

## 17. `figma-4-all` (Figma plugin — `ashley` UI component, banner-analyzer)

**What it is.** Figma plugin work. ES2017-compatible plugin runtime (no optional chaining / nullish coalescing / BigInt). Critical workflow: font load → constraint sanitize → clone/resize → semantic analysis → aspect-ratio lock → constraint solve → bounds clamp.

**What's impressive.**
- **Runtime-aware engineering** — knowing the plugin sandbox doesn't support ES2017+ features and adapting code accordingly is uncommon discipline.
- **QA VABB metrics** (Visual / Accessibility / Behavior / Bounds) maintained within configured thresholds.
- **TDD + no-mocks** with explicit `global.figma` mock exception (boundary mock only).
- Banner-analyzer skill packaged under `.codex/skills/`.

**Tech stack.** TypeScript · Figma Plugin API · `bun` · ES2017 strict subset · automated QA gates · `.codex/skills/`.

---

## 18. `shovaldesk` (cmux-inspired local cockpit)

**What it is.** cmux-inspired safe local workspace cockpit. Discovers projects under `~/projects`, surfaces automation reports from `~/.claude/docs`, opens lightweight PTY-backed shell panes.

**What's impressive.**
- **Hard safety boundary** — allowed write locations restricted to `~/.config/shovaldesk`, `~/.local/state/shovaldesk`, `~/.cache/shovaldesk`, `~/projects/shovaldesk`. Everything else read-only in v1.
- `doctor` + `snapshot` modes for verification without starting the TUI.
- Does not edit shell startup files, Claude hooks, Codex hooks, systemd, or aliases — composable, not invasive.

**Tech stack.** Python · `uv` · PTY · Textual / Rich TUI · `pyproject.toml` packaging.

---

## 19. `mcp-seekapa-tools` (production Streamable-HTTP MCP server)

**What it is.** Public-internet Streamable-HTTP MCP server (Web App `mcp-seekapa-tools`) wired to Claude Desktop and Claude.ai web connectors. (Code lives inside `campaign-analysis` under `app_mcp/`.)

**What's impressive.**
- **8-finding board-mandated security review closed in 2 days** (F-01 Entra federation in Bicep · F-02 CRM redaction + scoped `crm_get_customer_summary` · F-03 Chatwoot PII masking + private-note gating · F-04 per-tool scope matrix on all 21 tools · F-05 OAuth issuer matches App Service host · F-06 OneSignal DTO shaping + ACC namespace + null-strip · F-08 MSI to Key Vault, no env-secret prod fallback).
- **Streamable-HTTP MCP transport at `/mcp`** + RFC 9728 protected-resource metadata + dual-trailing-slash `aud=ISSUER` URL — works against Anthropic clients.
- **21 tools** across CRM / Chatwoot / OneSignal / CallAnalyzer.

**Tech stack.** Python (`fastapi`, `uvicorn[standard]`, `mcp>=1.4,<2.0`) · `python-multipart` (Form parser for `/oauth/token`) · `pyjwt[crypto]` · `httpx[http2]` · Azure App Service · Microsoft Entra ID (federated identity) · Azure Key Vault MSI · OAuth 2.1 + RFC 9728.

---

## 20. `_corp-powerbi-probe` + Power BI workflow notes (`powerbi_ref.txt`)

**What it is.** Power BI probe scaffolding + reference workflow doc for Claude Code + Power BI MCP integration. Sits alongside the Fabric+Dataverse BI layer per the centralized Marketing MCP plan.

**What's impressive (lead on the AI Product Analyst / Data Analyst CVs).**
- **BI Dashboard Discrepancy Report** + **Data Reconciliation Green/Red** workbook — owned reconciliation between Liron's exported BI workbook (22-03-2026) and the live system.
- **Beyond CPA — High-Impact Marketing Metrics for a Player-Focused Company** + **Full-Funnel Intelligence Brief** + **CMO Audit Seekapa Full Funnel Intelligence System v2.1** — stakeholder-facing strategy artifacts, not just plots.
- **Liron workbook handover (2026-05-17)** — when a stakeholder hands off a working book, you got the trust right.
- **Centralized Marketing MCP architecture plan**: Microsoft-native enterprise plan — APIM + per-platform ACA MCP servers + Entra role-gated access · Fabric + Dataverse as BI layer.

**Tech stack.** Power BI · DAX · Power Query · Microsoft Fabric (planned BI layer) · Dataverse · APIM (planned) · Azure Container Apps (per-platform MCPs).

---

## 21. `meta-ads-cli` (Campaign-analysis Meta-MCP scaffolding)

**What it is.** Meta Ads CLI / MCP scope reserved for the campaign-analysis Meta-MCP container (phase P1, `kv-mcp-platforms`). Per memory (`project_meta_ads_cli_scope`), this is NOT a personal `$HOME` install — it's reserved for the centralized Marketing MCP gateway.

**What's impressive.**
- **Scope-correction memory shows discipline** — caught that a personal install would have polluted the production phase P1 plan and re-routed.
- Lives under the planned centralized gateway pattern: APIM + per-platform ACA MCP servers + Entra role-gated access for CRM/CallAnalyzer/GAds/Meta/Taboola/Snap/YT/X.

**Tech stack.** Meta Ads API · MCP · Azure Container Apps · Azure Key Vault (`kv-mcp-platforms`) · APIM gateway (planned).

---

## 22. Side / utility projects

| Project | One-line | Stack chips |
|---|---|---|
| `article-generation` | LLM article scaffolding (empty top-level, work elsewhere). | — |
| `lp-creation` | Landing-page generation scaffolding (empty top-level). | — |
| `football` | Side football analytics project — `bun` + Node ecosystem. | TS · `bun` · Node |
| `personal` | Personal scratch / experiments (`jsq-slq`). | — |
| `big-brother` | Single Python file + requirements — observability probe. | Python |
| `_inherited` | Inherited code from prior owners (`automation-fabric`, `market-daily-reports`). | — |

---

## 23. Personal AI infrastructure (`~/.claude/` + `~/.codex/`) — meta-stack worth mentioning

**What it is.** A personal, two-model, hooks-driven AI engineering harness. Claude orchestrator + Codex executor (gpt-5.5 / codex-5.3), with audited A2A dispatch.

**What's impressive (mention in cover letter, not on CV body — too inside-baseball).**
- **29 custom Claude skills authored** (`~/.claude/skills/`): `eval-runner`, `agent-builder`, `azure-runtime`, `azure-audit`, `azure-activity-watch`, `code-simplifier`, `commit-push-pr`, `coverage-enforcer`, `premortem`, `heidegger-reflect`, `dispatch`, `claude-api`, `humanize`, `voice-explainer`, `visual-explainer`, `meeting-notes`, `jira-task-draft`, `red-team-review`, `deep-research`, `LTMD`, `grill-me`, `testing-pyramid`, `refactor-pre-push`, `meme-control`, `persona`, `openai-agents`, `shoval-voice-draft`, `cdp`, `verify`.
- **24 custom Codex skills** under `~/.codex/skills/` mirroring + extending the Claude side (`apify-mcp`, `azure-devops`, `azure-keyvault-secrets`, `cleanup-crew`, `feature-investor`, `kill-stale`, `mcp-activation`, `mutation-runner`, `ops-status`, `property-test-gen`, `red-team`, `triage-tests`, `watchdog`, `web-inspect`, `workspace-brain`, `elevenlabs-mcp`, `heygen-mcp`).
- **Forge Loop 8-axis weekly self-audit**: SPEC · PREMORTEM · RED · GREEN · REFACTOR · COVERAGE · REFLECT · CI BIND — automation under `~/.codex/automations/prompts/a09-forge-loop-compliance-score.md`. Hard-blocks pushes when axes are missing.
- **A2A v1 sync dispatch bridge** between Claude orchestrator and Codex / Foundry agents. Audit log at `~/.claude/cache/a2a/audit.jsonl`. One peer per call, 60s timeout.
- **Layer-7 observability** at `~/.claude/cache/layer7/` with `sessions.db` (sentrux-inspired sensor) — DB-backed session snapshot + metrics + `.layers.toml` per project.

---

## 24. Quick role-aligned summary

| Role | Lead with these projects | Skip / de-emphasize |
|---|---|---|
| **AI Engineer** (strongest) | `cs-agent` flagship · `campaign-analysis` MCP + Call-analyser · `azure-devops-agent` (Jira/M365) · `mcp-seekapa-tools` · `ORM-AGENT` · `~/.claude/` + `~/.codex/` skills | `personal`, `big-brother` |
| **Data Scientist / Analyst** | **`campaign-analysis` RL agent (sim2CRM)** · `social-intelligence-unit` data-quality audit · `campaign-analysis` BI/reconciliation (Liron) · `qc` call-quality scoring · `HR-agent` Apify pipeline · `_corp-powerbi-probe` · `openai-usage-audit` | model-finetuning-only framing — your DS is *applied analytics + eval engineering*, not research-ML |
| **AI Product Analyst** | `azure-devops-agent` (Jira+Outlook+Copilot Studio cross-system) · `copilot-agent` (5 Copilot Studio bots) · `campaign-analysis` (Liron handover + Belfort KPI brief) · `seekapa-training-platform` (multilingual + a11y) · `daily-marketing-overview` (Outlook delivery) · `claude-meme-hooks` (DevEx storytelling) | pure infra/Bicep work — keep it as supporting evidence, not headline |

---

## 25. CV-grade chips to drop into the Skills section

**Cloud / platforms**
Azure AI Foundry · Azure Functions (Linux Python) · Azure App Service · Azure Container Apps + ACR · Azure Key Vault + MSI · Microsoft Entra ID (federated identity, OBO) · Azure Service Bus · Azure Blob + ADLS · Cosmos DB · Bicep · `azd` CLI · `az` CLI · Azure DevOps (Repos + Pipelines, Boards) · Workload Identity Federation / OIDC

**AI / agent stack**
Azure AI Foundry agents (CRUD via `azure-ai-projects`) · MCP (Streamable-HTTP, RFC 9728, OAuth 2.1) · A2A v1 · Anthropic Claude SDK · OpenAI / Codex CLI · Microsoft 365 Agents SDK · Copilot Studio · `pac` CLI · DeepEval · `azure-ai-evaluation` (AIAgentConverter, IntentResolution, TaskAdherence, ToolCallAccuracy, Groundedness, custom DataAccuracy) · QLoRA fine-tuning (gemma-3-270m on HF) · Foundry-native eval pipeline (4-phase, cost-bounded)

**Microsoft 365 / Office surface**
WorkIQMail (Outlook MCP) · WorkIQTeams · WorkIQOneDrive · WorkIQCopilot · Copilot Studio BotDefinition YAML · Generative Actions · Power Platform · Power BI · Microsoft Fabric (Dataverse, OneLake) · Atlassian Jira MCP (Cloud, JQL, sprints, boards, transitions)

**Languages / runtimes**
Python 3.10–3.12 (`uv`) · TypeScript / JS (`bun`) · C# / .NET 10 (ASP.NET Core 9 Minimal APIs) · Bash · PowerShell · Bicep · SQL · Rust (side project)

**Data / ML**
pandas · NumPy · scikit-learn · statsmodels · autogluon · yfinance · TabPFN-3 · Cohere · sentence-transformers (`all-MiniLM-L6-v2`) · LanceDB · TimeGEN-1 · Apify · ElevenLabs Scribe v1 STT · ElevenLabs Voices + Flows (DAG) · WeasyPrint · matplotlib

**Quality / testing**
TDD vertical tracer bullets (no horizontal slicing) · `ruff` + `mypy` + `pytest` · `hypothesis` (property tests) · `respx` (HTTP recordings, no mocks for business logic) · `eslint` + `knip` + `vitest` · Playwright E2E · 4-tier SOTA CI · Forge-Loop 8-axis audit · Heidegger-reflect end-of-task introspection

**Languages spoken**
Hebrew (native) · English (C2) · Arabic (working — production AR/ES/PT multilingual agent for GCC accounts)

---

*This inventory is a personal scratchpad — verify-able against `git log` per project, `az functionapp list`, `az webapp list`, and `~/docs/audits/` before quoting on a public CV.*
