# Project maturity audit, 2026-07-01

Source scope:
- Knowledge context: `docs/SOTA-TESTING-CRITERIA-2026.md`, `docs/SHOVAL-CV-PROJECT-INVENTORY-2026-05-28.md`, `docs/KNOWLEDGE-BASE.md`, `docs/eval-findings-2026-05-11.md`, `docs/2026-06-10-IMPLEMENTATION-PLAN.md`, `docs/REPO-AUDIT.md`.
- Active repo roots checked under `~/projects`: `video-understanding`, `qc-telephony-api`, `lp-creation/ebook-task`, `agent-call-tracker`, `seekapa-training-platform`, `campaign-analysis`, `call-analyzer-frontend`, `ORM-AGENT/social-media-agent`.
- Utility repo checked separately: `video-understanding/ui-ux-pro-max-skill`.
- Excluded from maturity scoring: `~/projects` root repo anomaly, `.archive/*`, and nested empty/alias repos with zero tracked files.

Verification commands used:
- `rtk proxy find /home/shovalbe/projects -maxdepth 3 -type d -name .git -printf '%h\n'`
- `rtk proxy bash -lc '<tracked LOC and test classification script using git ls-files -z>'`
- `rtk rg -n 'pytest|ruff|mypy|playwright|coverage|mutation|openapi|gitleaks|deploy|smoke' .../azure-pipelines.yml`
- `rtk proxy bash -lc '<du and artifact/dependency scan>'`
- targeted `rtk nl -ba` reads for CI, DTO, frontend contract, and Vlad-style raw pass-through findings.

## Bottom line

The strongest projects are not the largest ones. `agent-call-tracker`, `qc-telephony-api`, and `campaign-analysis` have the most defensible engineering maturity because they combine tests, contracts or schema thinking, CI gates, and deploy/runtime evidence. `call-analyzer-frontend` is the weakest active production-adjacent repo because it has typed domain shapes but no tracked test suite and no `test` or `typecheck` script. `video-understanding`, `campaign-analysis`, and `ORM-AGENT/social-media-agent` need Ponytail cleanup before more features: their working directories are dominated by generated artifacts, dependency folders, or output history.

Vlad's DTO point is a real cross-project rule: known API boundaries must be typed and validated. The current QC Python backend is already good here (`src/api/shared/insights_models.py:InsightsView`). The Go drop-in sketch is not: it ignores `json.Marshal`, ignores `io.ReadAll`, and passes raw QC JSON through unchanged.

## Score table

Scoring follows `docs/SOTA-TESTING-CRITERIA-2026.md`: have = 1, partial = 0.5, gap = 0, n/a excluded. Scores below are audit scores, not test coverage percentages.

| Project | Stack and risk | Dirty | Source LOC | Test LOC | Test files | Size | Maturity | Score | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| `agent-call-tracker` | FastAPI/Python, CRM-read, prod | 0 | 5,664 | 4,538 | 29 | 177M | L3 defined | 82 | Best current balance of small code, serious CI, Testcontainers, security gates. |
| `qc-telephony-api` | Azure Functions Python, telephony, PII, prod | 6 | 6,137 | 8,474 | 49 | 291M | L3 defined | 78 | Strong contract/test posture, but CI still uses pip and a Go integration sketch violates Vlad's DTO rule. |
| `campaign-analysis` | Python/FastAPI/MCP/Next, analytics, PII, prod | 355 | 29,729 | 11,077 | 64 | 4.2G | L3 defined | 76 | Strong gates and security tests, but dirty state and artifact bulk reduce operational maturity. |
| `seekapa-training-platform` | React/Vite + Azure Functions, training, PII, prod | 36 | 53,643 | 16,407 | 80 | 415M | L2 managed | 70 | Broad tests and deploy smoke, but CI has non-blocking audit and an `npx` deploy step against house rules. |
| `ORM-AGENT/social-media-agent` | Python + Vite admin, social/creative, PII/content, prod-ish | 16 | 29,097 | 13,203 | 181 | 3.2G | L2 managed | 68 | Huge test corpus, weak top-level gate shape, heavy artifacts. Needs consolidation more than features. |
| `video-understanding` | Python media pipeline, video/audio QA | 189 | 9,449 | 1,137 | 13 | 9.0G | L2 managed | 58 | Useful recorded-fixture tests, but CI only covers a narrow subset and repo size is out of control. |
| `video-understanding/ui-ux-pro-max-skill` | Skill/tooling utility | 0 | 10,307 | 602 | 2 | not measured | L1 ad hoc | 42 | Clean git state, but low test depth for the amount of code. |
| `lp-creation/ebook-task` | PDF/ebook generation | 12 | 3,945 | 1,018 | 8 | 2.7G | L1/L2 | 38 | Verification scripts exist, but little CI/package structure was visible. |
| `call-analyzer-frontend` | Next/React frontend, QC scorecard UI | 0 | 22,296 | 0 | 0 | 1.1G | L1 ad hoc | 22 | Typed contract exists, but zero tracked tests and no `test` or `typecheck` script. |

## Test layer classification

| Project | Tests | Unit | Property | Contract/schema | Integration/e2e/live | Security/auth/PII | Visual/media | Fixtures/golden |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `video-understanding` | 20 | 12 | 0 | 1 | 1 | 0 | 8 | 7 |
| `qc-telephony-api` | 66 | 35 | 0 | 5 | 36 | 0 | 2 | 16 |
| `lp-creation/ebook-task` | 8 | 1 | 0 | 0 | 0 | 0 | 2 | 0 |
| `agent-call-tracker` | 30 | 29 | 2 | 1 | 4 | 2 | 1 | 2 |
| `seekapa-training-platform` | 91 | 62 | 1 | 8 | 24 | 4 | 19 | 2 |
| `campaign-analysis` | 64 | 61 | 2 | 1 | 1 | 7 | 1 | 1 |
| `call-analyzer-frontend` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ORM-AGENT/social-media-agent` | 198 | 178 | 1 | 3 | 9 | 1 | 29 | 25 |

Interpretation:
- `qc-telephony-api` has the best test-to-source ratio and the clearest fixture/ground-truth habit.
- `agent-call-tracker` has the best SOTA shape per LOC: unit, property, integration, Testcontainers, SAST, secret scanning, and mutation all appear in CI.
- `ORM-AGENT/social-media-agent` has many tests, but quantity is not the same as maturity. The audit risk is gate wiring and artifact sprawl.
- `call-analyzer-frontend` is currently unprotected. The typed `InsightsView` helps humans, but TypeScript interfaces alone do not validate runtime JSON or prevent UI regressions.

## Project notes

### `agent-call-tracker`

Evidence:
- CI runs `uv sync`, `ruff`, `mypy`, `pytest`, Testcontainers MySQL integration, Bandit, pip-audit, and Gitleaks in `azure-pipelines.yml:93-114`.
- Nightly mutation exists in `azure-pipelines.yml:116-145`, but surviving mutants are currently warning-only.
- Test inventory includes API, auth, cache, contract, MySQL integration, PII logging, properties, read-only invariant, snapshots, and settings.

Maturity:
- L3 defined, close to L4 once mutation becomes blocking and deploy smoke is fully blocking.

Ponytail read:
- Keep this repo small. Do not add a framework for the dashboard unless a measured frontend pain appears.
- The next mature move is not more feature code. It is turning mutation from advisory into a real threshold once stable.

### `qc-telephony-api`

Evidence:
- Python DTO contract exists: `src/api/shared/insights_models.py:203` defines `InsightsView`.
- Frontend-facing schema endpoint exists in code references: `src/api/function_app.py` returns `InsightsView.model_json_schema()`.
- CI runs unit coverage and E2E quality tests in `azure-pipelines.yml:65-70` and `azure-pipelines.yml:133-145`.
- The Go drop-in sketch violates Vlad's rule: `docs/integration/qc-dashboard-dropin/qc_insights_proxy.go:64` ignores `json.Marshal`, line 84 ignores `io.ReadAll`, and line 86 sends raw upstream bytes.

Maturity:
- L3 defined for Python service logic.
- The integration documentation is below the same standard as the implementation.

P0 finding:
- Replace `qc_insights_proxy.go` raw pass-through with typed Go DTOs: `QCInsightsRequest`, `QCInsightsView`, nested response DTOs, and typed error body. Add one valid-response fixture test and one malformed-upstream `502` test.

Ponytail read:
- Do not add a generic proxy abstraction. Add one small `QCClient.GetInsights(ctx, req)` and one shared `writeAPIError` helper only if a second handler needs it.

### `campaign-analysis`

Evidence:
- CI hard-fails lint and tests: `azure-pipelines.yml:101-106`.
- Coverage gate is named at 70 percent.
- Tests include MCP, OAuth, token redaction, credential vault, OneSignal DTO shaping, Chatwoot key contracts, OpenAPI schemas, Dockerfile source policy, and scoring pipelines.
- Repo is 4.2G, with 1.2G in `outputs`, 687M in `.venv`, 682M in `funnel-ui/node_modules`, and 22M in `dist`.

Maturity:
- L3 defined for backend/MCP work.
- Dirty state and artifact volume make operational maturity weaker than code maturity.

Ponytail read:
- Delete or archive generated outputs before building new analysis surfaces.
- Keep Foundry/MCP eval additions narrow and route-specific. Broad "agent eval platform" work would be overbuild unless tied to a failing acceptance criterion.

### `seekapa-training-platform`

Evidence:
- CI runs backend `ruff`, unit/property/contract tests with coverage, and deploy smoke: `azure-pipelines.yml:116-136`.
- Frontend has Playwright, build, lint, and targeted test scripts in `frontend/package.json`.
- Pipeline uses `bun install` and `bun run build`, but deploy still uses `npx --yes @azure/static-web-apps-cli` in `azure-pipelines.yml:446-451`.
- `pip-audit` is `continueOnError: true` in `azure-pipelines.yml:121-125`.

Maturity:
- L2 managed, with parts of L3.

P0/P1 findings:
- Replace the `npx` deploy step with a Bun-compatible or preinstalled SWA CLI path, or document a project-specific exception.
- Make dependency audit blocking for high/critical findings after current exceptions are triaged.

Ponytail read:
- The platform is already large. Avoid another reporting layer until the existing report/test/deploy paths are simplified.

### `ORM-AGENT/social-media-agent`

Evidence:
- 198 test files by audit classification, including admin API tests, gate tests, render snapshots, adversarial image fixtures, Arabic localization gates, and Playwright admin specs.
- Top-level `ORM-AGENT/azure-pipelines.yml` is build/push/deploy focused and main-gated, but the visible top-level flow does not show lint/test before deploy in lines checked.
- Repo size is 3.2G: 1.4G artifacts, 724M admin `node_modules`, 471M `assets/ui-liron/node_modules`, 428M `video/hedg-weekly/node_modules`.

Maturity:
- L2 managed. Test corpus is strong, gate wiring is the weak link.

P0/P1 findings:
- Add a blocking lint/test stage before image build/deploy for the exact deployed path.
- Move generated creative artifacts to an ignored/archive surface unless they are intentional golden fixtures.

Ponytail read:
- This repo is the biggest "delete before add" candidate. Consolidate admin/frontend dependency folders before adding new creative agents.

### `video-understanding`

Evidence:
- CI intentionally lint/tests only, with no build/push/deploy stage.
- CI only runs a subset: `tests/test_bot.py`, `tests/test_pipeline_smoke.py`, `tests/test_render.py`, `tests/test_schemas.py` in `azure-pipelines.yml:81-90`.
- Repo size is 9.0G, including 1.2G `video-gen/remotion/node_modules`, 249M `ebook-task/.venv`, 105M `video-gen/dist`, and many media artifacts.

Maturity:
- L2 managed for local media QA, not production-grade yet.

P0/P1 findings:
- Decide if this is a product repo or a media lab. If product, CI must cover the real extractor/gates path. If lab, archive generated outputs aggressively and stop scoring it like a service.

Ponytail read:
- Do not build more video abstractions until the repo is split or cleaned. The current size will slow every audit and every agent.

### `call-analyzer-frontend`

Evidence:
- `package.json` has only `dev`, `build`, `start`, and `lint`; no `test` or `typecheck`.
- No tracked tests were found.
- It has a strong typed mirror of the QC contract in `lib/qc/types.ts:96-104`, but runtime API parsing still relies on the generic client returning `InsightsView`.

Maturity:
- L1 ad hoc.

P0 finding:
- Add a minimal test harness: `bun run typecheck`, one contract fixture test that validates an `InsightsView` payload with Zod or generated schema, and one rendering smoke test for the scorecard page.

Ponytail read:
- Do not add a big frontend testing platform. Use one existing dependency if present, otherwise `node:test` plus a tiny schema parser is enough for the first contract guard.

### `lp-creation/ebook-task`

Evidence:
- Verification scripts exist for PDFs, truncation, brand assets, uniqueness, locale terms, and reviewer edits.
- No strong project-level CI/package markers were visible in the active scan.
- Repo size is 2.7G, with a 218M `.venv`; remaining size likely generated PDF/media output.

Maturity:
- L1/L2. Better as a content-production tool than as a software service.

Ponytail read:
- Treat most tests as acceptance verifiers. Do not inflate this into a service unless another system calls it.

### `video-understanding/ui-ux-pro-max-skill`

Evidence:
- Clean git state.
- 326 tracked files, 10,307 source LOC, 602 test LOC, 2 test files.
- GitHub workflows exist.

Maturity:
- L1 ad hoc for the amount of code.

Ponytail read:
- Either increase tests around the CLI behavior that matters, or reduce the surface. A large skill repo with two tests is hard to trust.

## Vlad contract rule generalized

Use this as the audit gate for every API boundary:
- Request DTO exists.
- Response DTO exists.
- Error DTO exists where errors are stable/domain-owned.
- Known upstream JSON is decoded into a typed contract before successful return.
- Unknown/flexible sections use `json.RawMessage`, `dict[str, Any]`, or equivalent only in explicitly named extension fields.
- Serialization/deserialization errors are handled and tested.
- Successful domain responses do not use anonymous maps.
- Repeated HTTP client flow is centralized behind a small client/helper.
- At least one success fixture and one malformed upstream fixture exist for every new endpoint.

This rule is most urgent for `qc-telephony-api` integration docs and `call-analyzer-frontend` runtime parsing.

## Highest-leverage fixes

1. `qc-telephony-api`: fix `docs/integration/qc-dashboard-dropin/qc_insights_proxy.go` to typed Go DTOs and explicit serialization errors.
2. `call-analyzer-frontend`: add `typecheck`, a test script, one `InsightsView` fixture contract test, and one scorecard render smoke.
3. `ORM-AGENT/social-media-agent`: add a blocking test/lint stage before top-level deploy.
4. `seekapa-training-platform`: remove or formally justify `npx` in the SWA deploy path; make high/critical dependency audit blocking.
5. `video-understanding`: clean or relocate generated media/dependency bulk before more feature work.
6. `campaign-analysis`: archive or ignore historical `outputs` and dirty generated state before the next MCP/reporting slice.
7. `qc-telephony-api`: complete the already tracked PII model-boundary tokenization item before expanding scoring features.
8. `agent-call-tracker`: convert mutation from warning-only to thresholded once baseline kill rate is known.
9. All prod API repos: commit/lint OpenAPI contracts and add a contract break gate where missing.
10. All AI/agent repos: refresh golden/eval sets from production failures rather than only synthetic rows.

## Cleanup candidates, do not delete without owner approval

Measured bloat:
- `video-understanding`: 9.0G total; `video-gen/remotion/node_modules` 1.2G, `ebook-task/.venv` 249M, `video-gen/dist` 105M.
- `campaign-analysis`: 4.2G total; `outputs` 1.2G, `.venv` 687M, `funnel-ui/node_modules` 682M.
- `ORM-AGENT/social-media-agent`: 3.2G total; `artifacts` 1.4G, multiple `node_modules` totaling more than 1.6G.
- `call-analyzer-frontend`: 1.1G total; `node_modules` 945M.
- `lp-creation/ebook-task`: 2.7G total; `.venv` 218M, likely generated output elsewhere.

Ponytail rule: clean generated/dependency/output bulk before adding any new audit framework, UI shell, or agent workflow.

