# Repo Enterprise Maturity TODO - 2026-07-09

Scope: `agent-call-tracker`, `axia-seekapa-cs-agents`, `ORM-AGENT`, `qc-telephony-api`, `seekapa-training-platform`, `video-understanding`, `sales-agents`, and the local agent harness (`intent-control-plane` plus the `.claude`/`.codex` hooks, added 2026-07-09).

Standards read:
- `docs/testing_practices.txt`
- `docs/cs-agent-pipeline.txt`
- `docs/cloudflare_pipeline.txt`
- `docs/Code Maturity Ladder  POC to Production (2026).md`
- `docs/API Design and Contracts SOTA - July 2026.md` equivalent file on disk uses an em dash in the filename
- `docs/System Architecture & Design Patterns SOTA - July 2026.md` equivalent file on disk uses an em dash in the filename
- `docs/Code Reuse, Deduplication, and the DRY AHA WET Balance (2026).md`
- `docs/Data & Persistence Layer SOTA - Polyglot 2026.md` equivalent file on disk uses an em dash in the filename
- `docs/Production AI & Software Engineering  The June 2026 State of the Art.md`
- `Documents/CICD_SOTA_Pipeline_Audit_20260706/CICD-SOTA-Pipeline-Audit-2026-07-06.md`

## House Rubric

Enterprise-grade means:
- Clean root tree: source, tests, docs, infra, scripts, configs, generated outputs, and local agent/tool state are separated.
- Boundary contracts: typed DTOs at ingress/egress, fail-closed validation, typed errors, OpenAPI/schema artifacts where there is an API, and contract tests.
- Architecture: modular monolith by default, with clear feature/application/domain/infra boundaries where complexity justifies it.
- Testing: static/type/lint, unit/property, contract, integration, e2e/smoke, regression, non-functional, and semantic evals for agent behavior.
- Pipeline: Yasha deploy rules, PR gates, secretless auth, no `az acr build`, Cloudflare origin lock where applicable, health gates, notifications, staging/prod separation, Codex review, and Foundry semantic eval gates where applicable.
- Docs: README plus setup, architecture, API contract, deployment, rollback, observability, known gaps, and ADRs for decisions.
- Docstrings: use PEP 257 / Google style for public modules, public classes, public functions, CLI entrypoints, API handlers with non-obvious contracts, and complex side effects. Do not docstring every private helper. Prefer type hints plus focused docstrings over narration.

## Global TODOs

- [ ] Add `.gitignore` hardening across all repos for `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.playwright-mcp/`, `.claude/`, `.codex/`, `node_modules/`, `dist/`, generated media, `*:Zone.Identifier`, local screenshots, and workdirs.
- [ ] Remove or archive local tool state and generated artifacts from active working trees after confirming no user work is lost.
- [ ] Standardize repo root layout: `src/` or product package, `tests/`, `docs/`, `infra/`, `scripts/`, `bin/`, `schemas/` or `api-specs/`, `evals/` for AI repos, `qa_reports/` only if committed intentionally.
- [ ] Add `docs/adr/` to every production repo and write ADR-0001 for architecture shape and deployment ownership.
- [ ] Add contract-first checklist to every API repo: DTOs, schema/OpenAPI artifact, boundary validation, typed errors, five-case contract tests.
- [ ] Add architecture fitness checks where boundaries exist: `import-linter` for Python, dependency-cruiser for TS.
- [ ] Add duplication reporting with `jscpd-rs` or equivalent in report-only mode first; gate only on new-code regression after exclusions.
- [ ] Normalize pipeline quality gates to the cs-agent standard: blocking ruff, mypy/pyright, pytest, coverage, pip-audit, bandit, semgrep, secret scan, test result publishing.
- [ ] Add RFC 9457-style `application/problem+json` or equivalent typed error DTOs on external HTTP APIs.
- [ ] Add generated API/DTO docs from schemas where possible, not hand-maintained payload prose.

## agent-call-tracker

Current read: good production shape; root contains `tracker/`, `tests/`, `docs/`, `scripts/`, `bin/`, but also local `.venv`, caches, `.playwright-mcp`, Zone.Identifier files, and `web/node_modules`. Strong DTO usage via Pydantic in `tracker/app.py`, `tracker/settings.py`, `tracker/auth.py`, `tracker/emailer.py`, `tracker/roles.py`; Protocols exist. Pipeline is closest to Yasha standard but still has hotspots.

TODO:
- [ ] Clean root: remove local `.venv`, caches, `.playwright-mcp`, `web/node_modules`, and Zone.Identifier files from the active tree; ensure ignored.
- [ ] Split `tracker/static/dashboard.js` (~1519 LOC) into API client, state/cache, chart rendering, and UI controller modules.
- [ ] Split `tracker/app.py` (~1228 LOC): move API DTOs to `tracker/contracts.py`, route registration into routers, response helpers into `tracker/http.py`.
- [ ] Add explicit `schemas/openapi.json` or generated OpenAPI artifact and make contract tests compare runtime schema to committed schema.
- [ ] Convert raw `{"detail": ...}` error responses to a typed error model / problem+json shape.
- [ ] Add public docstrings to exported DTOs, routers, cache classes, and `DBClient`/auth protocols; do not chase private helper coverage.
- [ ] Add architecture lint preventing routes/static code from importing persistence directly except through approved repository/service modules.
- [ ] Add semgrep if it remains absent from the pipeline.
- [ ] Verify pipeline no longer uses `az acr build`; the grep matched comments, but this needs a direct YAML assertion test.
- [ ] Add `docs/adr/0001-modular-fastapi-webapp.md`.

## axia-seekapa-cs-agents

Current read: strongest AI/eval maturity. Root has heavy docs/evals/tests, but also `.claude`, `.codex`, `.venv`, caches, `.playwright-mcp`, `kb-snapshot-2026-05-05`, qa reports. Azure Function shape is still folder-per-function with large handlers. DTO discipline is partial: many dict/HttpRequest boundaries, some TypedDict/dataclass/Protocol, but not consistent Pydantic request/response DTOs. Pipeline is closest to full cs-agent standard and includes Codex review and Foundry eval gates, but semantic eval gate is still advisory in places.

TODO:
- [ ] Clean root and decide which qa reports/eval outputs are canonical artifacts vs generated outputs.
- [ ] Move webhook boundary contracts into `azure-function-crm/contracts/` with Pydantic DTOs for Chatwoot webhook input, normalized turn, agent request, agent response, escalation payload, and channel-router request/response.
- [ ] Convert `chatwoot_handler/__init__.py` (~1200 LOC) into a thin function entrypoint plus application service modules.
- [ ] Convert `_pre_classifier.py` (~1246 LOC) into rule packs/data tables plus a small deterministic classifier engine.
- [ ] Add explicit error DTO/problem shape for function responses; remove free-form raw JSON error strings.
- [ ] Make Foundry live eval gate blocking only after baseline variance is stabilized; until then label clearly as advisory in README and pipeline docs.
- [ ] Add `docs/adr/0001-function-app-modular-boundaries.md`.
- [ ] Add import-linter contracts: handlers may import application services; domain classifiers cannot import Azure Functions or HTTP clients.
- [ ] Review docstrings: public classifiers, OTP verifier, channel router, CRM client, and signed-link APIs need Google-style docstrings; private rule constants do not.
- [ ] Add schema tests for eval dataset rows and Chatwoot payload variants as first-class contract tests.
- [ ] Ensure Codex PR review comments are resolvable threads and document merge policy around unresolved comments.

## ORM-AGENT

Current read: not one clean repo; it is a multi-product workspace containing `review-alert`, `social-media-agent`, `widgora`, nested `.git` under `social-media-agent`, local agent state, artifacts, PDFs, zips, logs, samples, and multiple pipelines. Some good DTO work exists in `widgora/blog_blocks.py` and admin SPA Zod schemas, but boundary discipline is inconsistent. Root structure is the main maturity blocker.

TODO:
- [ ] Decide repo boundary: split `social-media-agent` and `widgora` into separate repos or formalize this as a monorepo with a root workspace manifest and per-package ownership.
- [ ] Remove nested `.git` from `social-media-agent` only after preserving history/remote status; nested repos inside product repos are not enterprise-clean.
- [ ] Move generated artifacts/zips/images/logs into ignored `artifacts/` or external storage; commit only fixtures and golden samples.
- [ ] Add root `docs/REPO-MAP.md` explaining product boundaries, deployables, pipelines, owners, and runtime resources.
- [ ] Add root `docs/adr/0001-monorepo-or-split.md`.
- [ ] For `widgora`, centralize DTOs/contracts in `widgora/contracts/`; keep Pydantic/Zod schemas aligned and generate docs from them.
- [ ] Replace raw Flask error responses with typed error DTOs/problem+json for admin and public API routes.
- [ ] Add import-linter/dependency checks: routes cannot import DB/storage internals except through service/repository modules.
- [ ] Split `widgora/widget_store.py`, `routes_widgets.py`, and large page components over 1000 LOC.
- [ ] Add semgrep and CodexReview to pipelines where absent.
- [ ] Confirm all pipelines are using agent-side docker build and push, not `az acr build`.
- [ ] Add duplication report excluding generated/admin build outputs; investigate repeated UI pages and daily card scripts.
- [ ] Docstrings: public Flask routes with contract behavior, DTOs, storage/repo APIs, and generators need docstrings; template helpers and one-off scripts can stay light.

## qc-telephony-api

Current read: strong API contract repo. Root has `src/api`, `tests`, `docs/api-specs`, `samples`, `e2e`, but also `.claude`, `.codex`, `.venv`, caches, screenshots, Zone.Identifier files. DTO discipline is best of the set: many Pydantic models in `shared/*_models.py`, request limits, validators, schema tests. Main debt is route monolith and advisory lint/type gates.

TODO:
- [ ] Clean root local artifacts and screenshots; ensure ignored.
- [ ] Split `src/api/function_app.py` (~1412 LOC) into route modules by bounded surface: transcribe, translation, QA, insights, scoring, batch, health.
- [ ] Promote all public request/response DTOs into a clearly named `src/api/contracts/` or keep `shared/*_models.py` but document contract ownership.
- [ ] Generate and commit OpenAPI 3.1 spec from DTOs or maintain `docs/api-specs` as source of truth with diff tests.
- [ ] Add RFC 9457/problem+json error model for every API error branch.
- [ ] Make ruff and mypy blocking in pipeline; currently grep shows advisory `|| true`.
- [ ] Add import-linter contracts: route modules -> application services -> shared/domain; services cannot import Azure Functions.
- [ ] Add idempotency-key contract tests for batch/callback endpoints where mutation or external callbacks happen.
- [ ] Add docstrings to public DTOs with non-obvious domain constraints, service interfaces, and route modules; avoid docstring churn on simple validators.
- [ ] Add ADR for stateless/no-storage design and callback/HMAC boundary.
- [ ] Add contract-breaking CI gate for `docs/api-specs` changes.

## seekapa-training-platform

Current read: product-rich but structurally noisy. Root has backend function-per-folder, frontend, database, docs, reports, qa reports, node_modules at root and frontend, backend `.python_packages`, `.claude`, caches. Backend has some Pydantic in SSO/roles, but most Azure Function endpoints parse dicts directly and duplicate response/error logic. Pipeline has Codex review and Cloudflare sync, but still uses `az acr build`.

TODO:
- [ ] Remove root `node_modules`, `frontend/node_modules`, `.playwright-mcp`, backend caches, `.python_packages`, and local report render outputs from active tree unless deliberately committed.
- [ ] Replace `az acr build` in `azure-pipelines.yml` with agent-side `docker build` + `docker push`.
- [ ] Add missing security gates: bandit, semgrep, detect-secrets/gitleaks; make them blocking.
- [ ] Add mypy or pyright for backend; start with shared/auth/reporting modules, then expand.
- [ ] Create `backend/contracts/` with Pydantic DTOs for every public endpoint: session start, guest session, progress, team performance, report delivery, ElevenLabs webhook, admin actions.
- [ ] Generate TypeScript frontend types from backend DTO/OpenAPI instead of manually duplicated interfaces in `frontend/src/api/*`.
- [ ] Standardize response/error helper to typed DTOs/problem+json; stop each function hand-rolling `func.HttpResponse`.
- [ ] Split `backend/shared/email_service.py`, `retention_report_html.py`, and deploy scripts over 900 LOC.
- [ ] Archive or delete `scripts/deploy_retention_agents_v2_backup.py` if obsolete.
- [ ] Create `docs/adr/0001-training-platform-boundaries.md` and `docs/adr/0002-elevenlabs-webhook-contract.md`.
- [ ] Add contract tests from `docs/API_CONTRACT.md` to actual endpoint DTOs.
- [ ] Add import-linter: function entrypoints cannot import DB directly; they call application services.
- [ ] Add rollback/runbook doc for backend deploy and frontend static app deploy.
- [ ] Docstrings: public endpoint handlers, shared auth/role/email/reporting services, webhook validators, and DTOs need docstrings. Do not docstring every Azure Function folder's trivial `main` once wrappers are thin.

## video-understanding

Current read: currently a lab/workbench repo, not production-clean. Root contains app code, generators, video-gen, ebook-task, UI skill nested repo, `.agents`, `.claude`, `.codex`, workdirs, generated videos/audio/html, node_modules, many untracked artifacts. Contracts exist as JSON schemas and one Pydantic gate request, but most pipeline data structures are ad hoc. Pipeline has Cloudflare lock and lint/tests but not full security/type/contract posture.

TODO:
- [ ] First priority: clean root. Move generated media/workdir outputs to ignored `workdir/` or external artifact storage; remove nested `ui-ux-pro-max-skill` or vendor it explicitly.
- [ ] Decide product boundary: either split `video-gen`, `ebook-task`, and extractor into separate packages or formalize a monorepo workspace with clear package READMEs.
- [ ] Add `docs/REPO-MAP.md`: extractor, generator, video-gen, ebook-task, schemas, infra, tests, production app.
- [ ] Add `schemas/` as the source of truth and define Pydantic models mirroring JSON schemas for design evaluator input/output, ship gate, video plan, brand QA, voice QA, and creative gates.
- [ ] Add contract tests that validate real generated outputs against these schemas.
- [ ] Add mypy/pyright and make type checks blocking for extractor/generator modules.
- [ ] Add bandit, semgrep, secret scan, dependency audit to pipeline.
- [ ] Add health/smoke gate back to pipeline if absent in current grep.
- [ ] Split large creative components: `HowToOpenPosition*.tsx`, `ebook-task/src/content.py`, duplicated `design_system.py`.
- [ ] Add duplication report excluding generated Remotion outputs and media artifacts; investigate duplicated design system copies.
- [ ] Add architecture lint: generator cannot import Streamlit UI; extractor pipeline cannot import video-gen UI code.
- [ ] Add `docs/adr/0001-creative-understanding-monorepo.md`.
- [ ] Docstrings: public pipeline stages, gate evaluators, schema models, and CLI scripts need docstrings. One-off generation scripts can have module docstrings only.

## sales-agents

Current read: prototype/research shape, not production repo shape. Root has `src`, `functions`, `tests`, prompts, personas, research, outputs, test-results, data-inputs. Many dataclasses exist but no Pydantic boundary DTOs found. Azure Functions `function_app.py` is large and directly handles webhooks/leads/status. Pipeline is voice-test oriented, not production CI/CD.

TODO:
- [ ] Decide stage explicitly: if production-bound, write `docs/PRODUCTION-GAP.md`; if research-only, label it and stop pretending README production-ready means enterprise-ready.
- [ ] Clean generated outputs, exports, test-results, voice samples, and research PDFs into ignored artifact/storage paths.
- [ ] Add standard `azure-pipelines.yml` for CI/CD, not only `azure-pipelines-voice-tests.yml`.
- [ ] Add `pyproject.toml` with ruff, mypy/pyright, pytest, coverage configuration.
- [ ] Add blocking pipeline gates: ruff, mypy/pyright, pytest, coverage, pip-audit, bandit, semgrep, secret scan.
- [ ] Create `functions/contracts.py` or `src/contracts/` with Pydantic DTOs for ElevenLabs webhook, call record, lead import, lead status update, pending lead response, health response.
- [ ] Split `functions/function_app.py` into route handlers plus application services.
- [ ] Add typed error/problem responses and reject unknown fields at ingress.
- [ ] Add OpenAPI or API contract markdown generated from DTOs for lead/call/webhook endpoints.
- [ ] Add integration tests for Azure Function endpoints with real DTO validation and recorded ElevenLabs fixtures.
- [ ] Add Foundry/voice semantic eval gate only after DTO/API CI exists; do not let eval sophistication hide missing software gates.
- [ ] Add `docs/adr/0001-sales-agent-production-boundary.md`.
- [ ] Add docstrings to public dataclasses only if they are contract/domain objects; many current dataclasses are internal test/eval structures and do not all need Google docstrings.
- [ ] Add database migration/runbook posture if `src/database` is production-used: migration tool, rollback, backup/restore, schema docs.

## intent-control-plane (local agent harness)

Current read (2026-07-09): the tooling that enforces maturity on every repo above was itself unmeasured, treated only as `.claude`/`.codex` clutter to ignore. It is bash hooks plus a Python CLI package (`~/projects/intent-control-plane`). A same-day pass raised the core: the `prompt-router.sh` and `self-improve.py` decision logic moved into the tested `intent_control_plane.harness` package (golden + unit tests, ruff/mypy clean, 24 passed); `cli.py` split 1736 to 1453 LOC (`schema.py` + `mappers.py`); 14 dead-stub hooks removed; duplicate hooks single-sourced; README + lint/type/pytest config added; ADR-0001 written. Plan: `docs/specs/2026-07-09-harness-maturity-plan.md`.

TODO:
- [ ] Migrate the remaining ~9 python-heredoc hooks to the thin-shim shape (`python -m intent_control_plane.harness.*`), per ADR-0001.
- [ ] Add a blocking local gate (`uv run ruff/mypy/pytest`) before harness scripts are edited, mirroring the cs-agent standard.
- [ ] Add golden-trace regression fixtures for any future router or self-improve misfire.
- [ ] Fix the promptfoo push-gate: point at the deployed prompt and a sturdier grader (Foundry judge such as `grok-4-1-fast`); the nano judge has JSON-parse variance.
- [ ] Split the remaining `cli.py` command surface (1453 LOC) into command modules if it keeps growing.

## Ranking After Reground

1. `qc-telephony-api` - best DTO/API contract discipline; needs route split and blocking lint/type.
2. `agent-call-tracker` - best pipeline/deploy maturity; needs monolith split and error-contract cleanup.
3. `axia-seekapa-cs-agents` - best AI eval maturity; needs DTO consistency and handler decomposition.
4. `seekapa-training-platform` - real product, weaker boundary/pipeline security discipline.
5. `ORM-AGENT` - valuable systems, but repo boundary and artifact hygiene are below enterprise bar.
6. `video-understanding` - strong ideas, currently lab/workbench structure.
7. `sales-agents` - research/prototype unless promoted with standard CI, DTOs, API contracts, and deploy controls.
8. `intent-control-plane` (local agent harness) - newly measured 2026-07-09; router + self-improve decision logic now tested and typed, `cli.py` split. Open: migrate remaining heredoc hooks, add a blocking local gate. Tracked apart from the product repos since it is personal tooling, not a deployable.

## First 10-Day Execution Order

Day 1:
- Clean ignore rules and artifact plan for all repos.
- Pick one target repo to fix first; recommended `qc-telephony-api` or `agent-call-tracker`.

Days 2-3:
- For target repo, split root tree/source boundaries and add ADR-0001.
- Add/normalize DTO contract folder and error DTO.

Days 4-5:
- Add contract tests and schema/OpenAPI artifact.
- Make lint/type/security gates blocking.

Days 6-7:
- Split largest monolith file.
- Add architecture lint.

Days 8-9:
- Add duplication report-only gate with generated/artifact exclusions.
- Write README/deploy/runbook delta.

Day 10:
- Repeat the pattern on the next repo.
