# Stack Modernization & Hive Upgrade — Decision Report

**Date:** 2026-06-09
**Author:** automated audit sweep (research + per-project audit + upgrade plans + hive self-improvement)
**Reader:** Shoval (operator). Bottom-line-first. No secret values appear in this report.
**Stack reality assumed:** Azure Functions (Python) + Azure Container Apps + Bicep + Azure DevOps Pipelines (some GitHub Actions). No Kubernetes, no Terraform, no self-hosted Grafana/Prometheus.

---

## 1. Executive Summary

1. **uv adoption is split, not done.** uv is the source of truth in `cs-agent-main`, `campaign-analysis`, `social-intelligence-unit` (uv.lock present), and `ORM-AGENT` listener. But `video-understanding`, `video-generations`, `seekapa-training-platform`, `qc`, `compliance-exam-docker-deploy`, and `daily-marketing-overview` are still pip-only with no lockfile. Even uv-adopting repos run **bare pip inside their Dockerfiles**, defeating reproducibility. Action: standardize on uv multi-stage in Docker + `uv export --format requirements-txt` for the Oryx remote-build bridge that Azure Functions still requires.

2. **Secretless CI/CD (OIDC/WIF) is the exception, not the rule.** Only `seekapa-training-platform` uses ADO Workload Identity Federation. Every other ADO pipeline (`cs-agent-main`, `campaign-analysis`, `video-understanding`, `video-generations`, `qc`, `compliance-exam-docker-deploy`, `daily-marketing-overview`) uses classic service-principal connections or Kudu basic-auth. ADO WIF has been GA since 2024-02-12 with an in-product 7-day-revert conversion tool. SP secrets on ARM connections expire at 2 years — this is a silent mid-sprint deploy-failure time bomb.

3. **Observability is the deepest cross-cutting gap.** Most projects wire App Insights only via `host.json` sampling with **no SDK instrumentation in code**. `cs-agent-main` declares deprecated `opencensus-ext-azure` but never imports it. `compliance-exam-docker-deploy` declares `structlog` but never wires it. No project has verified end-to-end OTel tracing. The one-call fix is `azure-monitor-opentelemetry` (`configure_azure_monitor()`, GA 1.8.8) + `structlog` JSON via the stdlib backend.

4. **k8s / Terraform / Grafana+Prometheus verdict: DO NOT ADOPT any of the three for this shop.** You do not run them, and the research decision rules confirm you should not. Bicep + AVM beats Terraform for an Azure-only shop; Managed Prometheus + Grafana is only justified on AKS/Arc, high-cardinality PromQL needs, or non-Azure unification — none of which apply. App Insights via the OTel Distro is the correct default. (Full rule in §2.)

5. **IaC coverage is bimodal.** `campaign-analysis`, `video-understanding`, `video-generations`, `ORM-AGENT`, and `daily-marketing-overview` have Bicep. `cs-agent-main`, `social-intelligence-unit`, `qc`, and `compliance-exam-docker-deploy` have **zero IaC** (hand-provisioned). `seekapa-training-platform` uses an imperative shell script, not declarative IaC. None apply IaC from CI with a what-if gate.

6. **The 2026 Python library map is verified and applicable** across data/ETL paths: Polars (lazy + streaming) over pandas, orjson drop-in / msgspec for typed Structs, structlog for prod JSON, Optuna over GridSearchCV, deltalake (Spark-free), Pandera contracts, Hypothesis property tests, instructor (extraction) vs pydantic-ai (typed agents, now stable v1). Highest-leverage on Azure Functions: **Polars streaming engine + msgspec Structs** given the 4GB Flex Consumption RAM ceiling.

7. **One map correction:** pydantic-ai reached **stable v1.0 on 2025-09-04** with a 6-month no-breaking-change guarantee — the "pre-1.0 risk" framing is outdated. instructor remains the lighter single-call extraction choice; they are complementary, not competitors.

8. **Duplicate / dead repos:** `video-generations` is a dead predecessor of `video-understanding` (6-stage vs 7-stage, insecure az-CLI KV hack vs SDK, no tests, no independent git remote — untracked inside HOME-as-repo). Recommendation: archive. `cs-agent` resolves to `$HOME/.git` (same repo as the HOME worktree), and `cs-agent-main` is a separate clone of the same ADO remote — a three-way clone of one codebase.

9. **Container hardening is weak fleet-wide.** Most Dockerfiles are single-stage, run as **root**, and bundle dev dependencies into the production image. No project has a Trivy/Defender CI scan gate. Azure Functions custom containers must keep the `mcr.microsoft.com/azure-functions/*` base (no distroless), but ACA images can adopt non-root + multi-stage + Docker Hardened Images.

10. **Eval gates exist but are not wired.** `cs-agent-main` (YashaEvalGate Stage 5) and `campaign-analysis` (`evals/run_eval.py`) have full eval infrastructure that **no pipeline stage runs** — quality regressions merge undetected. `social-intelligence-unit` and `compliance-exam-docker-deploy` have no eval harness at all.

11. **Hardcoded credentials are a P0 in `seekapa-training-platform`:** a committed admin DB password, an unauthenticated `set_manager_role` endpoint returning a hardcoded password in its JSON body, and a test credential in a shared module. `social-intelligence-unit` and `ORM-AGENT` have committed/known fallback secrets. (Reported as `HARDCODED=security-risk`; no values reproduced here.)

12. **Connection-string auth instead of Managed Identity** recurs across `qc` (Storage), `compliance-exam-docker-deploy` (OpenAI/Storage/ACS), `daily-marketing-overview` (`listKeys` storage key + Service Bus root key in Bicep output), and `seekapa-training-platform` (Postgres password env var).

13. **Silent-failure auth patterns:** `cs-agent-main` HMAC gate no-ops when the webhook secret is unset; `qc` `CALLBACK_HMAC_SECRET` defaults to empty string (verification passes for any payload); both ship wildcard CORS or anonymous endpoints.

14. **Hive has two CRITICAL wiring bugs:** `UserPromptSubmit` and `PostToolUse` are **empty in settings.json**. Voice/visual auto-trigger and meme feedback never fire from Claude Code, despite CLAUDE.md claiming they are "already wired." The firing copies live in `.codex/hooks/` (Codex only). Single-line config fixes.

15. **Hive bead bus is a creation log, not a work tracker:** 67 of 70 beads (96%) are open and unclaimed since May 2026. The claim→close loop is broken; a `bead-reaper` + nightly cron is the highest-leverage hive infra fix.

---

## 2. k8s / Terraform / Grafana+Prometheus Verdict

You do not run Kubernetes, Terraform, or self-hosted Grafana/Prometheus. The explicit decision rules from the research, applied to an Azure-only Functions + ACA + Bicep + ADO shop:

### Kubernetes — DO NOT ADOPT
- **Rule:** k8s is justified only when you outgrow ACA's serverless/managed model (need full cluster control, custom CNI/operators, multi-tenant node pools, or GPU scheduling beyond ACA workload profiles). ACA already gives scale-to-zero, revisions, Dapr, KEDA scaling, and managed environments.
- **Verdict:** Nothing in the estate needs cluster-level control. ACA + Container App Jobs cover every containerized/long-running/batch workload. Adopting k8s would add an operational tier with no offsetting benefit. **No.**

### Terraform / OpenTofu — DO NOT ADOPT; use Bicep + AVM
- **Decision rule (Microsoft + 2026 independent analyses):** Choose **Bicep** for an Azure-only / Microsoft-native shop. Keep Terraform/OpenTofu **only if** multi-cloud, on-prem, or hybrid enters the roadmap. Bicep is stateless (no `terraform.tfstate` to secure/back up/corrupt), gets **day-zero** support for new Azure features via ARM (Flex Consumption `functionAppConfig`, ACA `2026-01-01` API), and integrates natively with `az` CLI + Azure Pipelines. Terraform's AzureRM provider lags new Azure features by weeks.
- **2026 enablers that closed the old gaps:** Azure Verified Modules (AVM) for Bicep are **GA** and the default starter in the ALZ Accelerator (classic ALZ-Bicep removed 2026-02-16); `.bicepparam` per environment; `what-if` previews; Deployment Stacks for lifecycle + deny-settings drift protection.
- **Verdict:** Bicep + AVM is correct. **Do not introduce Terraform.** Migrating an existing well-run Bicep estate to Terraform would be pure cost. (The decisive factor is discipline, not the tool — apply what-if gates and Deployment Stacks.)

### Managed Prometheus + Grafana — DO NOT ADOPT (default to App Insights)
- **Decision rule:** Default to **Application Insights via the Azure Monitor OpenTelemetry Distro** for app-level traces/logs on both Functions and ACA. Add **Managed Prometheus ONLY when** ANY of:
  1. You need dimensional/high-cardinality custom metrics with PromQL, recording rules, or Prometheus-style alerting that App Insights' metric model handles poorly; **OR**
  2. You already run **AKS or Arc-enabled Kubernetes** (Managed Prometheus scrapes directly only from AKS/Arc — there is no first-party direct scrape from Functions or ACA); **OR**
  3. You must unify Azure with non-Azure / open-source metrics in one Grafana pane.
- **None of these three triggers apply.** No AKS/Arc, no PromQL/recording-rule requirement surfaced, no non-Azure metric unification mandate.
- **Important ACA caveat (load-bearing):** the ACA managed OTel agent sends **logs+traces to App Insights but NOT metrics** — the App Insights destination does not accept OTel metrics. If you ever need ACA OTel *metrics* in an Azure-native store, that is the one scenario that would force a Managed-Prometheus-via-collector hop. Until then, platform/custom metrics through App Insights suffice.
- **Dashboards:** if you ever want Prometheus-style dashboards, start with the **free in-portal Azure Monitor dashboards with Grafana** (public preview, reads Managed Prometheus directly, no per-user cost) before paying for Azure Managed Grafana. **Do NOT self-host Grafana/Prometheus.**
- **Verdict:** App Insights + OTel Distro only. **No Managed Prometheus, no Grafana** at this time.

---

## 3. Cross-Cutting Upgrade Themes (Ranked)

### Theme 1 — Testing depth (eval gates, contracts, property, mutation)
Wire the eval gates that already exist (`cs-agent-main` YashaEvalGate, `campaign-analysis` `run_eval.py`) as hard CI gates with a pinned judge model + versioned dataset. Add Schemathesis OpenAPI contract/fuzz tests against HTTP-trigger and MCP surfaces. Add Hypothesis property/stateful tests for deterministic glue (chunking, HMAC, parsers, scorers). Extend mutation testing to production code and to the eval graders themselves (guard against reward gaming). Report task-success + trajectory-trustworthiness + cost together; use `pass^k` not single-shot accuracy.
- **Citations:** Azure AI Foundry agent evaluators (Tool Call Accuracy, Task Adherence, Task Navigation Efficiency) `https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/agent-evaluators`; Promptfoo CI/CD `https://www.promptfoo.dev/docs/integrations/ci-cd/`; pydantic-evals `https://pydantic.dev/docs/ai/overview/`; Hypothesis stateful `https://hypothesis.readthedocs.io/en/latest/stateful.html`; Schemathesis `https://schemathesis.io/`; mutmut/Cosmic Ray `https://github.com/sixty-north/cosmic-ray`; tau-bench pass^k `https://arxiv.org/abs/2406.12045`.

### Theme 2 — Secretless CI/CD via OIDC / Workload Identity Federation
Migrate every ADO ARM service connection from stored SP secret (or Kudu basic-auth) to Workload Identity Federation. Use the in-product conversion tool (7-day revert). Scope the UAMI to the resource group, not the subscription. For GitHub repos use `azure/login@v2` OIDC with `id-token: write` and three non-secret IDs. Gate prod behind environment approvals + what-if.
- **Note:** Flex Consumption **cannot** use a publish profile (Kudu/SCM absent → 401) — OIDC + remote build (`Azure/functions-action@v1`, `remote-build: true`) is the only supported path. Any Flex migration breaks without WIF.
- **Citations:** ADO WIF GA `https://devblogs.microsoft.com/devops/workload-identity-federation-for-azure-deployments-is-now-generally-available/`; configure WIF service connection `https://learn.microsoft.com/en-us/azure/devops/pipelines/release/configure-workload-identity?view=azure-devops`; GitHub OIDC `https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect`; functions-action `https://github.com/Azure/functions-action`.

### Theme 3 — IaC: Bicep + AVM + azd, with what-if gates and Deployment Stacks
Author/complete Bicep using AVM resource modules (`avm/res/web/site` for Flex Consumption, `avm/res/app/container-app` + `avm/res/app/managed-environment` for ACA, `avm/res/key-vault/vault`, `avm/res/insights/component`). One `.bicepparam` per env. Version-pin every `br/public:avm/...` ref. Run `az deployment group what-if` as a PR gate. Drive deploys with azd (`azure.yaml`, `host: function` / `host: containerapp`). Wrap prod in Deployment Stacks with `denyWriteAndDelete` (directly mitigates the prior "service stopped without notice" incident class). Use identity-based storage (`allowSharedKeyAccess: false`, `AzureWebJobsStorage__blobServiceUri`).
- **Citations:** AVM `https://azure.github.io/Azure-Verified-Modules/`; Functions IaC `https://learn.microsoft.com/en-us/azure/azure-functions/functions-infrastructure-as-code`; Bicep vs Terraform `https://learn.microsoft.com/en-us/azure/developer/terraform/comparing-terraform-and-bicep`; Deployment Stacks `https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deployment-stacks`; azd March 2026 `https://devblogs.microsoft.com/azure-sdk/azure-developer-cli-azd-march-2026/`; Flex Consumption plan `https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan`.

### Theme 4 — Container hardening
ACA images: uv multi-stage build (copy uv binary from a pinned `ghcr.io/astral-sh/uv` tag, `uv sync --locked --no-editable` with cache mount, `UV_COMPILE_BYTECODE=1`, copy only `.venv` into a slim/distroless runtime), non-root numeric UID, dropped capabilities, read-only root FS with tmpfs. Prefer Docker Hardened Images (Apache-2.0, free, SLSA L3 + SBOM since 2025-12-17) or Chainguard/Wolfi over python:slim. Azure Functions custom containers MUST keep `mcr.microsoft.com/azure-functions/*` (host embedded) — harden via pinning + monthly rebuilds + non-root + scanning, not base swap. Trivy CI gate (fail HIGH/CRITICAL) + SBOM + Defender for Containers + ACR quarantine + Notation/AKV signing (DCT retiring).
- **Citations:** uv Docker `https://docs.astral.sh/uv/guides/integration/docker/`; DHI `https://mrcloudbook.com/docker-hardened-images-the-2026-architects-guide-to-supply-chain-compliance/`; distroless comparison `https://safeguard.sh/resources/blog/distroless-vs-chainguard-vs-wolfi-base-images`; Functions custom container `https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-custom-container`; Trivy/Defender `https://trivy.dev/docs/latest/tutorials/integrations/azure-devops/`; Notation+AKV `https://learn.microsoft.com/en-us/azure/container-registry/container-registry-tutorial-sign-build-push`.

### Theme 5 — Observability / OTel → App Insights
Install `azure-monitor-opentelemetry` (1.8.8) and call `configure_azure_monitor()` once at startup (ACA/Web Apps) or set `host.json telemetryMode: OpenTelemetry` (Functions — do not also call the Distro inside the worker, avoid duplicate request telemetry). Route `structlog` (26.x) JSON through the stdlib backend (`ProcessorFormatter`) so logs reach the OTel `LoggingHandler` and auto-correlate to TraceId/SpanId. Bind per-request context (conversation_id, language, session_id, call_id). Trace-only sampling via `OTEL_TRACES_SAMPLER=microsoft.fixed_percentage` / `microsoft.rate_limited`. Remember the ACA-agent-no-metrics-to-App-Insights limitation.
- **Citations:** Enable OTel in App Insights `https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable`; OTel config/sampling `https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration`; Functions OTel `https://learn.microsoft.com/en-us/azure/azure-functions/opentelemetry-howto`; ACA OTel agent `https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents`; structlog stdlib integration `https://www.structlog.org/en/stable/standard-library.html`; azure-monitor-opentelemetry PyPI `https://pypi.org/project/azure-monitor-opentelemetry/`.

### Theme 6 — The 2026 Python library map
Polars lazy `scan_*` + streaming `collect(engine="streaming")` as the default for >100MB ETL (keep pandas for <~100MB, sklearn-return, GeoPandas, statsmodels); deltalake/delta-rs for Spark-free Arrow Delta; orjson drop-in (~10x stdlib) / msgspec typed Structs (decode+validate faster than orjson decode alone); instructor (single-call extraction) vs pydantic-ai (typed agents, **stable v1**); Optuna TPE + pruning over GridSearchCV (prefer SuccessiveHalving/Hyperband over MedianPruner for serious tuning); Pandera (Polars-native, lazy) schema contracts; Hypothesis property tests; Numba `@njit` only for non-vectorizable numeric kernels; uv over pip+venv; structlog prod / loguru dev.
- **Highest-leverage on Azure Functions:** Polars streaming engine + msgspec Structs (4GB Flex Consumption ceiling = fit-vs-OOM).
- **Citations:** Polars streaming `https://docs.pola.rs/user-guide/concepts/streaming/`; Polars memory vs pandas `https://pythonspeed.com/articles/polars-memory-pandas/`; orjson `https://github.com/ijl/orjson`; msgspec `https://github.com/jcrist/msgspec`; pydantic-ai v1 `https://pydantic.dev/articles/pydantic-ai-v1`; instructor `https://github.com/567-labs/instructor`; Optuna pruners `https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/003_efficient_optimization_algorithms.html`; deltalake `https://delta.io/blog/delta-lake-without-spark/`; Pandera Polars `https://pandera.readthedocs.io/en/latest/polars.html`; uv `https://github.com/astral-sh/uv`; Python on App Service (uv/pyproject) `https://techcommunity.microsoft.com/blog/appsonazureblog/what%E2%80%99s-new-for-python-on-app-service-for-linux-pyproject-toml-uv-and-more/4468903`.

---

## 4. Per-Project Sections

### 4.1 cs-agent-main
Seekapa/AxiaCS support agents on Azure Functions v4. uv-based, Python 3.11.

| Dimension | State |
|---|---|
| Stack | Python 3.11, uv (CI ad-hoc `uv pip install`; Dockerfile bare pip), Functions v4 consumption |
| Testing | pytest + pytest-asyncio + hypothesis + deepeval; ~634 test fns; property+integration+eval+mutation(pilot, evaluators only) |
| CI | ADO Pipelines, 4 stages; classic SP service connection; eval gate (Stage 5) **commented out** |
| IaC | **None** — all hand-provisioned |
| Docker | single-stage, **root**, bare pip, deprecated `apt-key add` |
| Observability | App Insights via host.json only; `opencensus-ext-azure` declared but **never imported**; stdlib logging, no bound context |

**Top risks:** (1) HMAC gate silently no-ops when `CHATWOOT_WEBHOOK_SECRET` unset on an anonymous public webhook — unauth POST triggers agent execution; (2) YashaEvalGate fully manual — no behavior regression gate; (3) hardcoded fallback IP for `AXIA_CRM_HOST`; (4) zero IaC; (5) opencensus dead dependency / no structured context; (6) three-way clone of one repo.

**Ranked upgrades:** 1) Hard-fail HMAC on missing secret (S/low). 2) Remove hardcoded CRM IP default → raise at startup (S/low). 3) Migrate service connection to WIF (S/low). 4) Wire YashaEvalGate as hard gate w/ pinned judge (M/med). 5) opencensus→azure-monitor-opentelemetry + structlog bound context (M/low). 6) Bicep+AVM baseline + what-if PR gate (L/med). 7) Schemathesis contract tests vs existing OpenAPI specs (M/low). 8) Dockerfile → uv multi-stage + non-root + `signed-by=` keyring (M/low). 9) CI `uv sync --frozen` + `uv export` for Oryx; fix 3.11/3.12 mypy mismatch (S/low). 10) Pydantic v2 inbound webhook validation + orjson hot path (M/low). 11) Extend mutation testing to `_gates.py`/`_pre_classifier.py` + graders (M/low). 12) Run integration tests on PRs via cassettes (M/low).

### 4.2 campaign-analysis
Marketing MCP gateway + call-quality scoring (FastAPI MCP on Web App for Containers + Next.js funnel-UI + ACA jobs). uv + Bicep.

| Dimension | State |
|---|---|
| Stack | Python 3.11 (mcp CI 3.13) + TS; uv; Web App for Containers + ACA |
| Testing | pytest + hypothesis + respx + pytest-benchmark; ~927 test fns; unit+property+integration |
| CI | ADO Pipelines (4 YAML); service connection by GUID; KV task for Foundry key; eval gate **not wired** |
| IaC | **Bicep** (mcp.bicep, jobs.bicep, funnel-ui.bicep); jobs marked not-deployed; ACR/plan/ACA-env out of band |
| Docker | multi-stage, non-root UID 1000 (root + sales Dockerfiles); **legacy app_mcp/Dockerfile** uses ~1GB devcontainer base + pip, Python 3.12 vs 3.13, UID 10001 |
| Observability | **None** — custom JsonFormatter, no App Insights, no OTel, no tracing |

**Top risks:** (1) eval gate exists but unwired; (2) GHCR PAT (org-level write:packages) in ADO variable library, not KV-rotated; (3) ACR admin creds in App Service appSettings instead of MSI AcrPull; (4) two divergent Dockerfiles for app_mcp; (5) no observability; (6) `pandas` imported at module top-level in production scoring path (`agent_scoring_round6.py`) but declared dev-only → sealed `--no-dev` venv import failure.

**Ranked upgrades:** 1) Wire `evals/run_eval.py` as stage gate (S/low). 2) Replace GHCR PAT with WIF for ACR push; KV-rotate or drop GHCR (M/low). 3) ACR admin creds → MSI AcrPull role (S/low). 4) Fix pandas import (lazy or add to prod deps) (S/low). 5) Delete/canonicalize legacy app_mcp Dockerfile (M/low). 6) App Insights via azure-monitor-opentelemetry (M/low). 7) Custom JsonFormatter → structlog + orjson backend (M/low). 8) Trivy scan stage + SARIF (S/low). 9) Replace respx mocks w/ VCR cassettes; raise coverage 70→80% (M/low). 10) Schemathesis vs MCP OpenAPI (M/low). 11) what-if PR gate + App Insights in mcp.bicep (M/low). 12) KV access-policy → RBAC (M/med). 13) orjson in `_logging.py`/`oauth.py` (S/low). 14) funnel-ui Dockerfile npm→bun (S/low). 15) Pandera contracts on eval dataset + scoring frames (M/low).

### 4.3 video-understanding
Streamlit + Telegram bot, 7-stage AI pipeline (ffmpeg→ElevenLabs STT→voice→Azure DI OCR→GPT-5.4-SIU→Jinja HTML) + Remotion tier. Bicep, pip-only, Python 3.12.

| Dimension | State |
|---|---|
| Stack | Python 3.12 + TS; **pip only** (no uv.lock/pyproject); ACA + Web App |
| Testing | pytest>=8 + hypothesis + playwright; 172 test fns; unit+property+contract+e2e+smoke — but only 4 test files run in CI |
| CI | ADO Pipelines; **no build/push/deploy stage** (deploy fully manual); classic service connection GUID in plain variable |
| IaC | **Bicep** (main.bicep + bicepparam): ACA + Log Analytics + 3 RBAC; Web App target absent from IaC |
| Docker | multi-stage, non-root UID 10001, **pip**; hypothesis/yt-dlp/python-telegram-bot **missing from requirements.txt** |
| Observability | **None** — pipeline.py uses `print()`; Log Analytics gets stdout only |

**Top risks:** (1) no build/deploy pipeline — manual deploys, no audit/rollback; (2) test/runtime deps missing from requirements.txt (image can't run full suite or bot); (3) `continueOnError:true` on Cloudflare IP-lock stage → raw `*.azurewebsites.net` origin can silently expose; (4) `print()` logging — no correlation IDs; (5) classic service connection.

**Ranked upgrades:** 1) Add build/push/deploy stage w/ WIF + Trivy gate (M/med). 2) Remove `continueOnError:true` on Cloudflare lock + 403 smoke test (S/low). 3) `print()`→structlog + azure-monitor-opentelemetry (S/low). 4) Add missing deps + Dockerfile uv multi-stage (S/low). 5) Wire eval dataset + video-gen JS gates; Pandera on brief schema (M/low). 6) Bicep for the Web App + what-if (M/low). 7) Move service-connection GUID to secret variable group (S/low). 8) stdlib json→orjson (4 callsites) (S/low). 9) Hypothesis stateful pipeline-invariant tests (M/low). 10) Pin Bicep API versions / migrate to AVM (L/med).

### 4.4 video-generations — DEAD / ARCHIVE
Prototype predecessor of video-understanding (6-stage vs 7-stage). **Not an independent git repo** — untracked subdirectory inside HOME-as-repo. Older insecure az-CLI KV fetch (and az CLI not in Dockerfile → cold-start crash at stage 2), no `--lang`, **zero tests**, orphaned CI (triggers on Master but has no ADO remote), reuses a compliance-exam secret name.

| Dimension | State |
|---|---|
| Stack | Python 3.12, pip-only, ACA |
| Testing | **0** |
| CI | ADO (Build/Preview/Deploy) but orphaned (no remote) |
| IaC | Bicep copied from video-understanding **without renaming** (appName mismatch → resource collision risk) |
| Docker | multi-stage, non-root UID 10001 |
| Observability | `print()` only |

**Verdict & recommendation:** Strongly recommend **archive or delete** this directory; all future work goes to `video-understanding`. If kept short-term, the only must-fix is the runtime crash (backport SDK-based KV fetch — one-function diff already done in video-understanding). Do not invest in tests/CI/IaC here.

### 4.5 seekapa-training-platform
Voice sales-training (15 ElevenLabs agents) + 10-dim scoring + Postgres on VNET + JWT RBAC. Python 3.11 Functions (container) + React SWA. **Uses ADO WIF already.**

| Dimension | State |
|---|---|
| Stack | Python 3.11 + TS; **pip** backend (bun frontend); Functions v2 container on shared plan; SWA |
| Testing | pytest + hypothesis(soft import) + playwright; ~124 backend + 24 frontend specs; hypothesis missing from CI install |
| CI | ADO (WIF, OIDC ✓) + stale GitHub Actions (npm, dead branch, continue-on-error) |
| IaC | **Imperative shell** (provision.sh) — not declarative |
| Docker | single-stage, **root**, pip |
| Observability | App Insights host.json only; stdlib logging |

**Top risks (P0 security):** (1) committed seekapaadmin DB password; (2) `set_manager_role` endpoint **unauthenticated** and returns a hardcoded password in the response body — unauth privilege escalation; (3) test credential in shared module; (4) no integration test tier in CI; (5) pip no-lockfile + `pip-audit` `continueOnError:true`; (6) single-stage root image; (7) localhost CORS origin in prod host.json. *(All reported as `HARDCODED=security-risk`; no values reproduced.)*

**Ranked upgrades:** 1) Remove 3 hardcoded credentials + add admin role guard (S/low). 2) Drop localhost from prod CORS (S/low). 3) Wire KV SDK for runtime secrets / MI for Postgres (M/low). 4) Make pip-audit a hard gate + add hypothesis to CI (S/low). 5) Trivy scan in DeployBackend (S/low). 6) Delete stale GitHub Actions; e2e via bun in ADO; npx→bunx (S/low). 7) Integration tier w/ Postgres service container (M/low). 8) Non-root + two-stage Dockerfile + `.dockerignore` (M/med). 9) azure-monitor-opentelemetry + structlog (M/low). 10) pip→uv + orjson hot paths (M/low). 11) provision.sh → Bicep+AVM + what-if; Deployment Stacks (L/med). 12) instructor for typed scoring extraction + Pandera + Hypothesis (M/low).

### 4.6 social-intelligence-unit
Meta/TikTok ad competitive intel (Apify→quality gate→Foundry classify→Next.js dashboard). FastAPI + React. uv + bun. Phase-1 local POC, ACA migration in progress.

| Dimension | State |
|---|---|
| Stack | Python 3.12 + TS; uv (uv.lock); local Docker, ACA pending |
| Testing | pytest + hypothesis + atheris + locust + playwright + vitest + mutmut; ~3536 test fns; many integration tests are `.skip` |
| CI | ADO (Tier1-3 + placeholder Deploy) + 4 GitHub Actions; **no Azure service connection / OIDC wired** — Deploy is an echo |
| IaC | **None** — all target resources documented but not provisioned |
| Docker | single-stage, **root**, pip (not uv), gcc/g++/git in final image |
| Observability | OTel present but no Azure sink; Prometheus metrics defined but no scrape; custom SIULogger |

**Top risks:** (1) no IaC; (2) Deploy stage is a placeholder echo — CD deploys nothing; (3) hardcoded JWT fallback secret committed (`HARDCODED=security-risk`); (4) root single-stage image w/ build tools; (5) integration layer largely `.skip` — coverage overstates confidence.

**Ranked upgrades:** 1) Remove JWT fallback → crash on unset; wire kv-siu-prod (S/low). 2) Real Deploy stage via ADO WIF + environment approval (M/med). 3) Bootstrap Bicep+AVM infra + what-if (L/low). 4) Dockerfile uv multi-stage + non-root + drop build tools (M/low). 5) pydantic-evals eval harness as nightly gate (M/low). 6) azure-monitor-opentelemetry + distributed trace propagation (S/low). 7) SIULogger → structlog + orjson (M/low). 8) Un-skip integration tests w/ docker-compose Postgres+Redis (M/med). 9) Activate orjson in API routes (already in extras) (S/low). 10) Remove unused pandas + scikit-learn (~80MB) (S/low). 11) Trivy CI gate + ACR quarantine (S/low). 12) Fix broken mutmut CI step (running pytest, not `mutmut run`) (S/low). 13) Pandera on Apify normalization boundary (S/low). 14) Fix Tier2 coverage condition + wire Locust nightly (S/low).

### 4.7 ORM-AGENT
Online reputation management: Python listener (Foundry classify) + .NET 10 ACA backend (HITL review, Gate 1 deterministic + Gate 2 Foundry judge, publish to Discourse/Dev.to). uv + Bicep (azd) + dotnet.

| Dimension | State |
|---|---|
| Stack | Python 3.13 listener (uv) + C# .NET 10; ACA |
| Testing | pytest (listener: 2 integration-only, skip w/o creds) + MSTest (86 C# methods) |
| CI | **NONE** — manual azd deploy, no pipeline |
| IaC | **Bicep (azd-managed)** — full module set; no Key Vault; AI Foundry RBAC done in postprovision.ps1 outside IaC |
| Docker | multi-stage, non-root (.NET); **no Dockerfile for the Python listener**; frontend uses npm ci despite bun.lock |
| Observability | App Insights + OTel in C#; listener uses `print()` only, no logging on error paths |

**Top risks:** (1) IaC-without-CD — Bicep exists, no pipeline triggers it; (2) Gate 2 not enforced before `/publish` (compliance enforcement gap for a regulated CFD broker); (3) listener has no offline test coverage; (4) Discourse/DevTo keys flat in IConfiguration, no KV; (5) `credentials for MVP.txt` plaintext on disk (gitignored, not committed; `HARDCODED=security-risk` — accidental-inclusion risk).

**Ranked upgrades:** 1) Wire third-party keys into Key Vault + Bicep (M/low). 2) Add ADO pipeline (test→build+Trivy→what-if→azd deploy) via WIF (L/med). 3) KV resource in Bicep + move Foundry RBAC into Bicep role-assignment module (M/low). 4) Offline listener unit + Hypothesis schema-invariant tests + structlog error logging (M/low). 5) `print()`→structlog + configure_azure_monitor at ACA startup (S/low). 6) Dockerfile for listener (uv multi-stage) + add to azure.yaml as containerapp (M/low). 7) Enforce Gate 2 pass before publish (422 otherwise) + test (S/low). 8) frontend npm ci → bun + move Entra IDs to runtime env (S/low). 9) Playwright e2e for ACA web app (L/low). 10) Add structlog/Hypothesis/azure-monitor-opentelemetry to listener deps (S/low). 11) Deployment Stack with denyWriteAndDelete on prod (M/med). 12) pydantic-evals harness for classification (L/low). **Quick win:** delete the on-disk credentials file.

### 4.8 qc / qc-telephony-api
Azure Functions v2 multi-language transcript translation + RAG Q&A + ElevenLabs Scribe v2 STT. pip+venv, Python 3.11 CI / 3.12 local.

| Dimension | State |
|---|---|
| Stack | Python; **pip+venv** (no lockfile); Functions v2 (no container) |
| Testing | pytest + pytest-cov; ~234 test fns (unit + e2e quality); **unittest.mock heavily** (violates no-mocks rule) |
| CI | ADO (Build/E2E/Deploy/Verify); KV task for Foundry key; auth type undeclared in YAML; E2E only on main |
| IaC | **None** |
| Docker | **No Dockerfile** (zipDeploy) |
| Observability | App Insights opt-in (silent drop if env unset); azure-monitor-opentelemetry present; stdlib logging, no bound context |

**Top risks:** (1) no IaC; (2) Storage uses connection-string (shared-key) auth, not MI — silent rotation break; (3) unittest.mock fidelity drift vs no-mocks rule; (4) E2E quality gate only post-merge on main; (5) wildcard CORS on function-key endpoints; (6) `CALLBACK_HMAC_SECRET` defaults to empty string (HMAC passes for any payload); (7) no lockfile → unpinned transitive upgrades.

**Ranked upgrades:** 1) Storage → DefaultAzureCredential/MI (S/low). 2) Hard-fail empty `CALLBACK_HMAC_SECRET` + forged-HMAC smoke test (S/low). 3) Restrict CORS to allowlist (S/low). 4) ruff+mypy stage (S/low). 5) PR-time smoke quality gate from golden traces (M/low). 6) Convert service connection to WIF + move subscription ID to variable group (S/low). 7) Replace mocks with VCR cassettes (M/med). 8) pip→uv + `uv export` for Oryx (M/low). 9) structlog bound per-request context into OTel pipeline (M/low). 10) Distributed tracing for ElevenLabs + Table Storage + trace sampling env vars (S/low). 11) Hypothesis for chunking + HMAC invariants (M/low). 12) pytest-asyncio coverage for async endpoints (M/low). 13) Bicep+AVM baseline + what-if (L/med). 14) stdlib json→orjson (6 modules) (S/low). 15) Schemathesis contract/fuzz (M/low).

### 4.9 compliance-exam-docker-deploy
Regulatory compliance exam (ElevenLabs voice exams → GPT-4.1 18-Q scoring → WeasyPrint PDF → ACS email). Functions v2 Docker on ACA. pip-only, Python 3.11.

| Dimension | State |
|---|---|
| Stack | Python 3.11; **pip only**; Functions v2 Docker on ACA |
| Testing | **0 tests** — no pytest, no config |
| CI | ADO (BuildImage + ACR cleanup + Telegram); **no deploy stage**, no test stage, no scan; classic service connections |
| IaC | **None** |
| Docker | single-stage, **root**, pip; **no `.dockerignore`** (SYSADMIN-INFO.txt + .env.template enter build context) |
| Observability | App Insights host.json only; `structlog` declared but **never wired**; stdlib logging |

**Top risks:** (1) zero tests on compliance pass/fail scoring logic; (2) no deploy stage — manual ACA rollout, no rollback; (3) no IaC; (4) root container; (5) key-based auth for OpenAI/Storage/ACS instead of MI; (6) structlog declared but unused — incident investigation is free-text only.

**Ranked upgrades:** 1) MI/DefaultAzureCredential for OpenAI/Storage/ACS (M/med). 2) pytest suite for `calculate_final_result_v4`/`save_exam_scores` + Hypothesis + Pandera on evaluator dict (M/low). 3) Deploy stage via `az containerapp update` + rollback + WIF (M/med). 4) `.dockerignore` + non-root USER (S/low). 5) Bicep+AVM (ACA, KV first) + what-if (L/med). 6) Activate structlog (already in deps) (S/low). 7) Trivy scan stage + Defender for Containers (S/low). 8) Dockerfile uv multi-stage (M/low). 9) json→orjson (S/low). 10) BOT_TOKEN/CHAT_ID → KV-linked variable group (S/low). 11) Distributed tracing through queue chain (M/low). 12) LLM evaluator golden-trace eval harness (M/low). 13) PR validation pipeline (S/low). 14) Audit/remove redundant aiohttp (S/low).

### 4.10 daily-marketing-overview
Two components: automation-fabric (Functions + ACA Job + Next.js dashboard, 24 marketing slots via Grok/Sora/Veo) + market-daily-reports (Durable Functions market reports, EN+AR PDFs via SendGrid). pip-only, Bicep present.

| Dimension | State |
|---|---|
| Stack | Python 3.11/3.12 + TS; **pip**; Durable Functions + ACA Job + SWA |
| Testing | pytest + vitest + playwright; ~24 Python (container-app) + ~89 TS + ~31 e2e; **market-daily-reports has 0 tests on disk** (CI runs pytest with `continueOnError:true`) |
| CI | ADO (2 pipelines); **Kudu basic-auth** deploys (no OIDC); `KUDU_PASSWORD` bare variable (no group); tests non-blocking |
| IaC | **Bicep** (main.bicep + container-app-job.bicep); not applied from CI; SWA + market-daily-reports Function App absent |
| Docker | both single-stage, **root**, pip; dev deps bundled into prod image |
| Observability | App Insights wired in Bicep but ACA Python process emits no telemetry; market-daily-reports stdlib logging; container-app uses structlog ✓ |

**Top risks:** (1) market-daily-reports has no tests but CI silently passes; (2) Kudu basic-auth + bare `KUDU_PASSWORD` (no group); (3) ACA job API keys as Bicep `@secure()` params (literal values would persist in ARM deployment history); (4) `AzureWebJobsStorage` via `listKeys` account key, not MI; (5) Service Bus root key exposed in Bicep output; (6) Python version mismatch (Dockerfile 3.11 vs Bicep Functions 3.12).

**Ranked upgrades:** 1) `listKeys` storage key → MI `__blobServiceUri` + `allowSharedKeyAccess:false` (M/med). 2) Service Bus root key output → scoped RBAC + MI (M/med). 3) Wrap KUDU_PASSWORD in secret variable group; longer-term WIF (M/low). 4) Trivy scan gate on both images + SBOM (S/low). 5) Add market-daily-reports tests; remove `|| true` / continueOnError (L/low). 6) Make tests blocking + add Bicep what-if PR gate (S/low). 7) Both Dockerfiles → uv multi-stage + non-root (M/low). 8) Apply Bicep from CI + add SWA + market-daily-reports Function App + KV secret refs for DB password (L/med). 9) azure-monitor-opentelemetry in ACA + structlog in market-daily-reports (M/low). 10) pip→uv both subprojects + remove unused pandas (~35MB) (M/low). 11) stdlib json→orjson (7 files) (S/low). 12) Hypothesis property tests on parsing/config (M/low). 13) Align Python version 3.11/3.12 (S/low).

---

## 5. Light-Sweep Note (Secondary Repos)

11 secondary repos under `/home/shovalbe/projects`. None has IaC; observability instrumentation is absent across all 11. Status snapshot:

- **figma-4-all** — ACTIVE: Figma plugin (Bun/JS) + bun REST adapter, ADO CI with Codex audit + VABB QA gates, meaningful test suite. Gap: `sync-keyvault-env.sh` writes fetched secrets to a local `.env` on disk (cleartext-at-rest outside KV; `HARDCODED=security-risk` pattern — values not read).
- **big-brother** — ACTIVE (personal): MediaPipe/OpenCV webcam detector, local-only. Gap: no tests, no CI, no uv.lock.
- **openai-usage-audit** — STALE/BLOCKED: uv tooling, no live admin/compliance keys (cannot run). Gap: stub, no tests; `data/raw` would receive compliance-log PII if wired — no confirmed `.gitignore` guard.
- **shovaldesk** — ACTIVE (personal): Python tmux-style cockpit (uv), no cloud surface. Gap: no tests/CI.
- **_inherited/market-daily-reports** — STALE: Functions email/report generator; bare pip in CI; `continueOnError:true` masks test failures. Service stopped 2026-05-06, replaced by v2.
- **_inherited/automation-fabric** — STALE: Playwright audit scripts + pipeline; variable-group is the correct pattern but the YAML comment **names the secret keys inline** (info-disclosure).
- **_corp-powerbi-probe** — STALE/PROBE: Laravel 11 + Vite; pipeline hardcodes `dockerRegistryServiceConnection` UUID in YAML; different ACR than sentimarkregistry.
- **HR-agent** — DOCS/DATA only: candidate LinkedIn JSON + Excel **committed** with no `.gitignore`/DLP (PII-in-git risk).
- **meta-ads-cli** — PLACEHOLDER: one PNG, no code (scoped for campaign-analysis Meta-MCP, not a local install).
- **article-generation** — EMPTY.
- **azure-devops-agent** / **copilot-agent** — STALE templates (Copilot Studio YAML + Foundry snapshot); affiliate/contact spreadsheets committed alongside config (PII boundary unclear).

**Cross-cutting secondary risks:** PII committed to repos (HR-agent, copilot-agent, azure-devops-agent) with no `.gitignore` guards; secrets written to local `.env` (figma-4-all); secret key names disclosed in pipeline YAML comments (_inherited/automation-fabric); bare pip + `continueOnError:true` masking regressions; stale/stopped services with no deprecation markers (re-activation risk). Recommend: add `.gitignore`/DLP guards before any of these gain a remote; mark stale repos deprecated; migrate inherited pipelines off bare pip and off non-blocking tests.

---

## 6. Hive Self-Improvement Plan

### 6.1 New Skills

| Skill | Purpose | Effort | Why high-leverage |
|---|---|---|---|
| bicep-linter | Lint (`bicep build --lint`) + review Bicep vs AVM (module pins, system MI, RBAC, `allowSharedKeyAccess:false`, TLS1_2, KV-reference drift, Flex Consumption anti-patterns) | M | Only IaC-review gap in both inventories; Flex Consumption deadline time-boxes it |
| ado-pipeline-monitor | Poll ADO run status, failed stages, log tails — read-only | L | 100% ADO CI; closes the tightest daily friction loop |
| kv-health | KV secret expiry, app-setting references to deleted/rotated versions, missing MI RBAC — read-only, never reads values | M | Stale KV reference = silent P0 auth break across all function apps |
| aca-revision-manager | Inspect ACA revisions/traffic/ingress; trigger/rollback with explicit per-action OK | M | ACA is a primary target (newsletter migration, video PRs) with no skill |
| otel-wiring | Wire azure-monitor-opentelemetry + structlog into a Functions/ACA project; flags ACA-no-metrics limitation | M | Cross-cutting observability gap; prerequisite for trajectory eval + layer7 fidelity |
| polars-uv-migrator | Migrate pandas→Polars (lazy) + pip→uv (+ `uv export` for Oryx) | M | campaign-analysis + eval pipeline; 4GB Flex ceiling makes streaming load-bearing |
| secretless-pipeline | Migrate/scaffold ADO ARM connections to WIF; scaffold OIDC + what-if + Flex remote-build YAML | M | SP secrets expire at 2y; Flex can't use publish profiles — blocking prerequisite |
| bead-reaper | Scan beads.db for stale open beads, propose auto-close, top-10 triage; explicit OK to mutate | L | 67/70 beads open — drains the broken backlog |
| trivy-scan | Trivy image/IaC scan, HIGH/CRITICAL filter, CycloneDX SBOM, pass/fail verdict — read-only | L | Container-security CI gap (sentimarkregistry has no scan gate) |
| ado-workitem | Create/update ADO work items from session (draft-before-write) | L-M | i-sdd is 100% ADO; replaces jira-task-draft manual-paste for the SPEC axis |

### 6.2 New Subagents
- **azure-explorer** — read-only **Haiku** subagent for cheap Azure resource fan-out (enumerate Function Apps/ACA/storage/KV, grep Log Analytics, read revision lists), tools limited to Read/Glob/Grep/Bash read-only `az`, explicit mutation refusal. Prerequisite for kv-health/ado-pipeline-monitor at scale.
- **bicep-reviewer** — isolated Bicep reviewer (AVM pins, Deployment Stack deny-assignments, Flex identity-storage, KV-ref syntax); tools Read/Glob/Bash(`az bicep build --lint` only); never edits.
- **bead-claimer** — hive bead worker; `isolation: worktree` so it branches from the target rig's default branch (never touches HOME-as-repo HEAD); drains the 67-bead backlog.

### 6.3 Hooks / Automation
- **CRITICAL — wire `UserPromptSubmit`** (voice-explainer-trigger.sh + visual-explainer-trigger.sh): currently empty; CLAUDE.md's "already wired" claim is **false** for Claude Code.
- **CRITICAL — wire `PostToolUse`** (meme-post-bash.sh matcher Bash + meme-post-skill.sh matcher Skill): currently empty; meme feedback never fires.
- **Stop hook → `type:agent`** running per-rig smoke_checks → blocks completion without test evidence (enforces GREEN axis).
- **PreToolUse secrets guard** (matcher `Bash|Edit|Write`): deny on `az keyvault secret show` (value), `*_KEY`/`*_SECRET`/`*CONNECTION_STRING` echo, `cat .env`, `printenv` piped — unbypassable even in bypassPermissions.
- **SessionStart compact-reinject upgrade**: re-inject branch+commit, active bead titles for current rig, last Forge-Loop axis status.
- **Nightly bead-reaper CronJob** (~22:00 Asia/Jerusalem): triage report to `.hive/logs/`, auto-expire beads with no evidence_url older than 14 days.
- **ConfigChange hook** (matcher user_settings|project_settings|skills): append to `~/.claude/observability/config-audit.jsonl` (governance P1 axis).

### 6.4 Config Changes (settings.json)
- Add `UserPromptSubmit` array entry pointing at the two trigger scripts.
- Add `PostToolUse` entries for the two meme scripts (matchers Bash / Skill).
- Change Stop `stop-checklist.sh` to `type:agent` (or add a `type:prompt` Haiku Forge-Loop-axis check) for project sessions.
- Add `Bash(az keyvault secret show --query value*)` and `printenv`/`export` patterns to the deny-list (belt-and-suspenders for the secrets guard).
- Add heygen-skills to `enabledPlugins` OR move the bundle out of `.claude/skills/` (currently present-but-unreachable = worst case).
- Create `.claude/agents/azure-explorer.md` (model:haiku, read-only tools, mutation refusal).
- Merge `rigs.draft.yaml` ADO-wired `test_cmds` into canonical `rigs.yaml` so the agent Stop hook can read per-rig test commands.

### 6.5 Retire / Consolidate
- **RETIRE** `openai-agents` skill (no platform.openai.com key, can never run) → archive to `~/.claude-resource-archive/`.
- **RETIRE** loose `heidegger-reflection.md` in `.codex/skills/` (not a directory skill; duplicates the directory skills).
- **CONSOLIDATE** `commit-push-pr` (3 locations + Codex): canonical `.agents/skills/`, thin delegating wrappers elsewhere.
- **CONSOLIDATE** `code-simplifier` (3 locations) → one canonical + wrappers.
- **CONSOLIDATE** `azure-devops` (.codex + .agents) → `.codex` canonical; new ado-* skills depend on it, not duplicate it.
- **CONSOLIDATE** `azure-keyvault-secrets` (.codex + .agents) → `.codex` canonical (kv-health is distinct).
- **CONSOLIDATE** `red-team-review` (.codex + .claude) → `.claude` canonical (Codex copy is a wrapper of a wrapper).
- **REMOVE dead registrations** `siu-loop`, `siu-observability`, `siu-performance`, `siu-watchdog`, `insights` (no backing SKILL.md — silently fail if invoked).
- **DECIDE on heygen-skills** (wire via mcp-activation or archive).

### 6.6 Ranked Top 10 (Hive)
1. Wire `UserPromptSubmit` hooks (CRITICAL config one-liner).
2. Wire `PostToolUse` meme hooks (CRITICAL config).
3. Build `bicep-linter` skill (time-boxed by Flex Consumption deadline).
4. Build `kv-health` skill (silent P0 failure class).
5. Create `azure-explorer` Haiku subagent (cheap fan-out; prerequisite).
6. Build `ado-pipeline-monitor` skill (daily friction loop).
7. Implement `bead-reaper` + nightly cron (drain 67-bead backlog).
8. Build `secretless-pipeline` skill (blocking prerequisite for Flex migration).
9. Retire `openai-agents` + consolidate commit-push-pr/code-simplifier/red-team-review.
10. Build `otel-wiring` skill (cross-cutting observability + ACA-metrics pitfall).

---

## 7. Consolidated Prioritized Backlog

| # | Project / Hive | Area | Change | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Hive | hooks | Wire `UserPromptSubmit` (voice + visual triggers) | S | low |
| 2 | Hive | hooks | Wire `PostToolUse` (meme bash + skill) | S | low |
| 3 | seekapa-training-platform | security | Remove 3 hardcoded creds + add admin role guard | S | low |
| 4 | cs-agent-main | security | Hard-fail HMAC on missing webhook secret | S | low |
| 5 | social-intelligence-unit | security | Remove JWT fallback secret → crash on unset; wire KV | S | low |
| 6 | qc | security | Storage connection-string → Managed Identity | S | low |
| 7 | qc | security | Hard-fail empty `CALLBACK_HMAC_SECRET` | S | low |
| 8 | daily-marketing-overview | security | `listKeys` storage key → MI `__blobServiceUri` | M | med |
| 9 | compliance-exam-docker-deploy | security | OpenAI/Storage/ACS key auth → Managed Identity | M | med |
| 10 | cs-agent-main | security | Remove hardcoded CRM IP default | S | low |
| 11 | ORM-AGENT | security | Discourse/DevTo keys → Key Vault + Bicep; delete on-disk creds file | M | low |
| 12 | campaign-analysis | ci-cd | Wire `evals/run_eval.py` as stage gate | S | low |
| 13 | cs-agent-main | ci-cd | Wire YashaEvalGate w/ pinned judge + dataset | M | med |
| 14 | All ADO repos | ci-cd | Migrate service connections to WIF/OIDC | S–M | low |
| 15 | video-understanding | ci-cd | Add build/push/deploy stage (WIF + Trivy) | M | med |
| 16 | video-understanding | ci-cd | Remove `continueOnError:true` on Cloudflare lock | S | low |
| 17 | social-intelligence-unit | ci-cd | Real Deploy stage (WIF + approval) | M | med |
| 18 | compliance-exam-docker-deploy | ci-cd | Add deploy stage + rollback | M | med |
| 19 | daily-marketing-overview | testing | Add market-daily-reports tests; make tests blocking | L | low |
| 20 | compliance-exam-docker-deploy | testing | pytest for scoring logic + Hypothesis + Pandera | M | low |
| 21 | Hive | skill | Build `bicep-linter` | M | low |
| 22 | Hive | skill | Build `kv-health` | M | low |
| 23 | Hive | subagent | Create `azure-explorer` (Haiku, read-only) | L | low |
| 24 | Hive | skill | Build `ado-pipeline-monitor` | L | low |
| 25 | Hive | automation | `bead-reaper` + nightly cron | L | low |
| 26 | campaign-analysis | security | GHCR PAT → WIF; ACR admin creds → MSI AcrPull | M | low |
| 27 | All projects | observability | azure-monitor-opentelemetry + structlog bound context | M | low |
| 28 | cs-agent-main / campaign-analysis / others | iac | Bicep+AVM baseline + what-if PR gate (where missing) | L | med |
| 29 | All Docker repos | docker | uv multi-stage + non-root + Trivy gate | M | low |
| 30 | seekapa-training-platform | testing | Integration tier w/ Postgres service container | M | low |
| 31 | video-generations | cleanup | Archive dead predecessor (after crash-fix if kept) | S | low |
| 32 | All repos | libraries | json→orjson hot paths; Polars where >100MB; uv where pip-only | S–M | low |
| 33 | Hive | skill | Build `secretless-pipeline` | M | low |
| 34 | Hive | retire | Retire openai-agents + consolidate duplicated skills | S | low |
| 35 | Hive | skill | Build `otel-wiring`, `aca-revision-manager`, `trivy-scan`, `ado-workitem`, `polars-uv-migrator` | M | low |
| 36 | secondary repos | security | `.gitignore`/DLP guards for committed PII; mark stale repos deprecated | S | low |

---

## 8. References (deduplicated)

### Data / serialization / libraries
- Polars in Aggregate (Dec 2025) — https://pola.rs/posts/polars-in-aggregate-dec25/
- Announcing Polars 1.0 — https://pola.rs/posts/announcing-polars-1/
- Polars streaming user guide — https://docs.pola.rs/user-guide/concepts/streaming/
- Why Polars uses less memory than pandas — https://pythonspeed.com/articles/polars-memory-pandas/
- Polars vs pandas 2026 benchmarks — https://www.danilchenko.dev/posts/polars-vs-pandas/
- Polars vs pandas (Databricks) — https://www.databricks.com/blog/polars-vs-pandas
- Polars landing — https://pola.rs/
- polars PyPI — https://pypi.org/project/polars/
- delta-rs releases — https://github.com/delta-io/delta-rs/releases
- Delta Lake without Spark — https://delta.io/blog/delta-lake-without-spark/
- Delta Lake on ADLS — https://delta.io/blog/delta-lake-azure-data-lake-storage/
- delta-rs Python docs — https://delta-io.github.io/delta-rs/python/
- Reading Delta into Polars — https://delta.io/blog/2022-12-22-reading-delta-lake-tables-polars-dataframe/
- orjson README — https://github.com/ijl/orjson
- msgspec README/GitHub — https://github.com/jcrist/msgspec , https://github.com/msgspec/msgspec
- msgspec PyPI — https://pypi.org/project/msgspec/
- msgspec performance — https://deepwiki.com/jcrist/msgspec/7.2-performance-results
- Numba 0.61.0 notes — https://numba.readthedocs.io/en/stable/release/0.61.0-notes.html
- numba PyPI — https://pypi.org/project/numba/
- Pydantic AI v1 — https://pydantic.dev/articles/pydantic-ai-v1
- instructor GitHub — https://github.com/567-labs/instructor
- instructor PyPI — https://pypi.org/project/instructor/
- instructor docs — https://python.useinstructor.com/
- pydantic-ai GitHub — https://github.com/pydantic/pydantic-ai
- pydantic-ai overview — https://pydantic.dev/docs/ai/overview/
- PydanticAI vs Instructor — https://medium.com/@mahadevan.varadhan/pydanticai-vs-instructor-structured-llm-ai-outputs-with-python-tools-c7b7b202eb23
- Python AI agent library comparison 2026 — https://jangwook.net/en/blog/en/python-ai-agent-library-comparison-2026/
- Optuna TPESampler — https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html
- Optuna efficient algorithms — https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/003_efficient_optimization_algorithms.html
- Optuna GitHub — https://github.com/optuna/optuna
- Why Optuna beats GridSearchCV — https://www.synogize.io/hyperparameter-tuning-for-smart-people-why-optuna-beats-gridsearchcv-and-randomizedsearchcv
- Optuna guide (datagy) — https://datagy.io/python-optuna/
- Optuna SOTA (TDS) — https://towardsdatascience.com/state-of-the-art-machine-learning-hyperparameter-optimization-with-optuna-a315d8564de1/
- Pandera Polars docs — https://pandera.readthedocs.io/en/latest/polars.html
- pandera PyPI — https://pypi.org/project/pandera/
- pandera 0.19 Polars (Union.ai) — https://www.union.ai/blog-post/pandera-0-19-0-polars-dataframe-validation
- Hypothesis docs — https://hypothesis.readthedocs.io/en/latest/
- Hypothesis stateful — https://hypothesis.readthedocs.io/en/latest/stateful.html
- hypothesis PyPI — https://pypi.org/project/hypothesis/
- astral-sh/uv — https://github.com/astral-sh/uv
- uv docs — https://docs.astral.sh/uv/
- uv Docker integration — https://docs.astral.sh/uv/guides/integration/docker/
- uv locking/syncing — https://docs.astral.sh/uv/concepts/projects/sync/
- uv-docker-example — https://github.com/astral-sh/uv-docker-example
- Choosing a Python logging library 2026 (Dash0) — https://www.dash0.com/guides/python-logging-libraries
- structlog standard-library integration — https://www.structlog.org/en/stable/standard-library.html
- structlog logging best practices — https://www.structlog.org/en/stable/logging-best-practices.html
- structlog bound loggers — https://www.structlog.org/en/stable/bound-loggers.html

### IaC / Functions / ACA / azd
- Azure Verified Modules — https://azure.github.io/Azure-Verified-Modules/
- Functions infrastructure as code — https://learn.microsoft.com/en-us/azure/azure-functions/functions-infrastructure-as-code
- AVM for Platform Landing Zone — https://techcommunity.microsoft.com/blog/azuretoolsblog/release-of-bicep-azure-verified-modules-for-platform-landing-zone/4487932
- AVM container-app module — https://github.com/Azure/bicep-registry-modules/tree/main/avm/res/app/container-app
- AVM container-app main.bicep — https://github.com/Azure/bicep-registry-modules/blob/main/avm/res/app/container-app/main.bicep
- Comparing Terraform and Bicep — https://learn.microsoft.com/en-us/azure/developer/terraform/comparing-terraform-and-bicep
- Bicep vs Terraform 2026 — https://technspire.com/en/blog/bicep-vs-terraform-azure-2026-honest-update
- Flex Consumption plan — https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan
- Flex Consumption how-to — https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to
- azd March 2026 — https://devblogs.microsoft.com/azure-sdk/azure-developer-cli-azd-march-2026/
- First function with azd — https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-azure-developer-cli
- Flex Consumption azd samples — https://github.com/Azure-Samples/azure-functions-flex-consumption-samples
- Deployment Stacks — https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deployment-stacks
- Bicep modules — https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/modules
- .bicepparam files — https://mattoffprem.com/blog/2026-01-21-bicepparam-files-for-azure-deployments/
- AVM Bicep composition — https://azure.github.io/Azure-Verified-Modules/contributing/bicep/composition/
- Microsoft.App/containerApps reference — https://learn.microsoft.com/en-us/azure/templates/microsoft.app/containerapps
- ACA managed identity — https://learn.microsoft.com/en-us/azure/container-apps/managed-identity
- Python on App Service (pyproject/uv) — https://techcommunity.microsoft.com/blog/appsonazureblog/what%E2%80%99s-new-for-python-on-app-service-for-linux-pyproject-toml-uv-and-more/4468903

### CI/CD / secretless
- GitHub OIDC to Azure — https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect
- Configuring OIDC in Azure (GitHub Docs) — https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure
- ADO WIF service connection — https://learn.microsoft.com/en-us/azure/devops/pipelines/release/configure-workload-identity?view=azure-devops
- ADO WIF GA blog — https://devblogs.microsoft.com/devops/workload-identity-federation-for-azure-deployments-is-now-generally-available/
- ADO ARM service connection (conversion) — https://learn.microsoft.com/en-us/azure/devops/pipelines/library/connect-to-azure?view=azure-devops
- Azure/functions-action — https://github.com/Azure/functions-action
- Functions GitHub Actions — https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-github-actions
- Deploy Bicep via GitHub Actions — https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-github-actions
- Azure/bicep-deploy — https://github.com/Azure/bicep-deploy
- Functions core-tools uv issue #4705 — https://github.com/Azure/azure-functions-core-tools/issues/4705
- Python developer reference for Functions — https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python

### Container security
- uv multi-stage Docker (DEV) — https://dev.to/kummerer94/multi-stage-docker-builds-for-pyton-projects-using-uv-223g
- uv read-only containers — https://slhck.info/software/2025/09/19/running-uv-docker-containers-read-only.html
- Distroless vs Chainguard vs Wolfi — https://safeguard.sh/resources/blog/distroless-vs-chainguard-vs-wolfi-base-images
- Docker Hardened Images 2026 guide — https://mrcloudbook.com/docker-hardened-images-the-2026-architects-guide-to-supply-chain-compliance/
- Functions custom container — https://learn.microsoft.com/en-us/azure/azure-functions/functions-how-to-custom-container
- Docker security best practices — https://oneuptime.com/blog/post/2026-02-02-docker-security-best-practices/view
- Docker capabilities/escalation — https://pythonspeed.com/articles/root-capabilities-docker-security/
- Read-only Docker containers — https://oneuptime.com/blog/post/2026-01-16-docker-read-only-containers/view
- Trivy vs Grype 2026 — https://lucaberton.com/blog/trivy-vs-grype-2026/
- Container vuln scanning 2026 — https://vucense.com/dev-corner/container-vulnerability-scanning-2026/
- Trivy on Azure DevOps — https://trivy.dev/docs/latest/tutorials/integrations/azure-devops/
- Defender for Containers intro — https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-containers-introduction
- Container image mapping (Defender) — https://learn.microsoft.com/en-us/azure/defender-for-cloud/container-image-mapping
- Notation + Azure Key Vault signing — https://learn.microsoft.com/en-us/azure/container-registry/container-registry-tutorial-sign-build-push
- Cosign/Notation signing — https://blog.glen-thomas.com/software%20engineering/security/2026/01/20/signing-container-images-with-cosign.html
- Ratify on Azure — https://ratify.dev/docs/quickstarts/ratify-on-azure/

### Observability / OTel
- Enable OpenTelemetry in App Insights — https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable
- Configuring OpenTelemetry in App Insights — https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration
- OpenTelemetry with Azure Functions — https://learn.microsoft.com/en-us/azure/azure-functions/opentelemetry-howto
- ACA OpenTelemetry agents — https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents
- azure-monitor-opentelemetry PyPI — https://pypi.org/project/azure-monitor-opentelemetry/
- Visualize Azure Monitor with Grafana — https://learn.microsoft.com/en-us/azure/azure-monitor/visualize/visualize-grafana-overview
- Azure Managed Grafana pricing — https://azure.microsoft.com/en-us/pricing/details/managed-grafana/
- What is Azure Managed Grafana — https://learn.microsoft.com/en-us/azure/managed-grafana/overview
- Azure Monitor Prometheus overview — https://learn.microsoft.com/en-us/azure/azure-monitor/metrics/prometheus-metrics-overview
- Azure Monitor pricing — https://azure.microsoft.com/en-us/pricing/details/monitor/

### Agent testing / eval
- Foundry agent evaluators — https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/evaluation-evaluators/agent-evaluators
- Promptfoo assertions/metrics — https://www.promptfoo.dev/docs/configuration/expected-outputs/
- Promptfoo CI/CD — https://www.promptfoo.dev/docs/integrations/ci-cd/
- Promptfoo GitHub — https://github.com/promptfoo/promptfoo
- Hypothesis PBT guide (MarkTechPost) — https://www.marktechpost.com/2026/04/18/a-coding-guide-for-property-based-testing-using-hypothesis-with-stateful-differential-and-metamorphic-test-design/
- Schemathesis — https://schemathesis.io/
- Schemathesis stateful — https://schemathesis.readthedocs.io/en/stable/guides/stateful-testing/
- Cosmic Ray — https://github.com/sixty-north/cosmic-ray
- Mutation testing tools comparison (NSF) — https://par.nsf.gov/servlets/purl/10573281
- tau-bench (pass^k) — https://arxiv.org/abs/2406.12045
- PBT with Claude (Anthropic) — https://red.anthropic.com/2026/property-based-testing/
- PBT-Bench — https://arxiv.org/html/2605.15229v2

### Claude / hive extensibility
- Skill authoring best practices — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Agent Skills (Anthropic) — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Hooks guide — https://code.claude.com/docs/en/hooks-guide
- Subagents — https://code.claude.com/docs/en/sub-agents
- Multi-agent coordination patterns — https://claude.com/blog/multi-agent-coordination-patterns
- Claude Code plugins — https://claude.com/blog/claude-code-plugins
- Plugins reference — https://code.claude.com/docs/en/plugins-reference
- Output styles — https://code.claude.com/docs/en/output-styles
