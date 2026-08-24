# Repo Maintenance File Plan - 2026-07-09

This is the lower-level companion to `repo-enterprise-maturity-todo-2026-07-09.md`.

Purpose: turn the repo-level audit into file-by-file work without mixing cleanup, refactor, contract changes, and pipeline changes in one unsafe blob.

## Rules

- Do not delete generated/local artifacts until `.gitignore` and an artifact-retention decision exist.
- Do not mix file moves with logic changes.
- Do not split large files until current tests pass or the failure baseline is recorded.
- Do not add docstrings mechanically. Add PEP 257 / Google-style docstrings only to public contracts, exported service APIs, CLI entrypoints, non-obvious domain classes, and side-effect-heavy functions.
- Ponytail audit means: delete or reuse before adding, split only when it reduces real complexity, and avoid new abstractions until the rule-of-three or a contract boundary justifies it.

## Change Types

- `HYG`: hygiene only: ignore rules, generated artifact relocation, cache cleanup.
- `TREE`: directory restructuring, file moves, repo boundary cleanup.
- `DOC`: README, REPO-MAP, ADR, RUNBOOK, API_CONTRACT, docstrings.
- `DTO`: request/response/error contracts, schemas, OpenAPI, generated frontend types.
- `PIPE`: CI/CD, security gates, Cloudflare/Yasha deploy alignment.
- `PONY`: large-file split, dedup, dead-code removal.
- `TEST`: unit/contract/integration/eval tests and verification logging.

## Acceptance Template

Each file-level task must include:

```text
Repo:
Type:
Files:
Change:
Why:
Risk:
Verification:
Rollback:
```

## Global Directory Management Plan

Target root shape for production repos:

```text
README.md
AGENTS.md
pyproject.toml / package.json / uv.lock / bun.lock
azure-pipelines.yml
src/ or product_package/
tests/
docs/
  REPO-MAP.md
  RUNBOOK.md
  API_CONTRACT.md
  adr/
infra/
scripts/
schemas/ or docs/api-specs/
evals/                 # only AI/eval repos
qa_reports/            # only committed canonical reports
artifacts/             # ignored unless fixtures/golden samples
```

Root items that should not remain active tracked/visible unless explicitly justified:

- `.venv/`
- `node_modules/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `.playwright-mcp/`
- `.claude/`
- `.codex/`
- `.agents/`
- `*:Zone.Identifier`
- local screenshots
- generated audio/video
- ad hoc `workdir/`
- nested `.git/` directories inside child products
- `*.bak`, backup scripts, duplicated generated lock/artifact folders

## File-by-File Seeds

These are the first file targets. Before implementation, expand each into the acceptance template above and verify current tests/status.

## agent-call-tracker

### HYG / TREE

- `.gitignore`: add missing ignores for caches, local tool state, Zone.Identifier, generated screenshots, `web/node_modules`.
- root local artifact files: move/delete only after confirming untracked and non-canonical.
- `web/`: decide whether this is production source or local experiment; if production, add README and build/test commands; if experiment, move under `experiments/` or archive.

### DTO / DOC

- `tracker/app.py`: move exported API models (`DayAggregate`, `FtdDay`, `AgentEntry`, `AgentsResponse`, settings/email request DTOs) into `tracker/contracts.py`.
- `tracker/routers/role_sync.py`: replace manual dict validation with Pydantic DTOs for role sync events.
- `tracker/routers/auth.py`: add response DTOs for `/api/auth/me` and logout.
- `tracker/http.py` (new): typed error/problem response helpers.
- `schemas/openapi.json` (new): committed contract artifact or generated snapshot.
- `docs/adr/0001-modular-fastapi-webapp.md` (new).

### PONY

- `tracker/static/dashboard.js`: split into `api.js`, `state.js`, `charts.js`, `ui.js`.
- `tracker/app.py`: after DTO move, split route registration into modules.
- `tracker/emailer.py`: inspect for split between config validation, rendering, and sending.

## axia-seekapa-cs-agents

### HYG / TREE

- `.gitignore`: ignore `.claude/`, `.codex/`, `.venv/`, `.playwright-mcp/`, caches, generated eval run outputs.
- `qa_reports/`: classify canonical reports vs generated run outputs.
- `kb-snapshot-2026-05-05/`: classify as fixture, canonical snapshot, or archive.

### DTO / DOC

- `azure-function-crm/contracts/` (new):
  - `chatwoot.py`: Chatwoot webhook DTO, normalized inbound message DTO.
  - `agent.py`: agent request/response DTOs.
  - `escalation.py`: escalation/ticket/forwarding DTOs.
  - `channel.py`: channel router request/response DTOs.
  - `errors.py`: typed function error response.
- `azure-function-crm/chatwoot_handler/__init__.py`: turn into thin entrypoint after contracts exist.
- `azure-function-crm/channel_router/__init__.py`: replace body parsing/formatting with DTO validation.
- `docs/adr/0001-function-app-modular-boundaries.md` (new).
- `docs/API_CONTRACT.md`: update from real DTOs.

### PONY

- `azure-function-crm/chatwoot_handler/_pre_classifier.py`: split rules/data from classifier engine.
- `azure-function-crm/chatwoot_handler/__init__.py`: split orchestration, Chatwoot I/O, agent call, post-processing.
- `azure-function-crm/shared/crm_mysql_client.py`: inspect whether query allowlist and transport are separable.

## ORM-AGENT

### HYG / TREE

- Root `.gitignore`: ignore generated media, zips, logs, local agent/tool state, node_modules, venvs, Zone.Identifier.
- `social-media-agent/.git`: decide split vs subtree vs delete nested metadata; no blind deletion.
- `social-media-agent/artifacts/`, `social-media-agent/logs/`, generated png/jpg/zip files: move to ignored artifact storage unless golden fixtures.
- `widgora/.venv`, `widgora/admin-spa/node_modules`, `.playwright-mcp`, caches: ignore and clean.

### DIR DECISION

Option A: split into separate repos:
- `ORM-AGENT/review-alert`
- `ORM-AGENT/social-media-agent`
- `ORM-AGENT/widgora`

Option B: formal monorepo:
- root workspace README
- `packages/review-alert`
- `packages/social-media-agent`
- `packages/widgora`
- shared `docs/`, `infra/`, `scripts/`

Do not implement either until an ADR exists.

### DTO / DOC

- `docs/REPO-MAP.md` (new): map deployables and owners.
- `docs/adr/0001-monorepo-or-split.md` (new).
- `widgora/contracts/` (new): admin, widget, brand, blog, role sync, error DTOs.
- `widgora/routes_admin_spa.py`, `routes_widgets.py`, `routes_sync.py`: route through DTOs.
- `widgora/admin-spa/src/ConfigGallery.tsx`: align Zod schema with backend DTO source.

### PONY

- `widgora/widget_store.py`: split storage, validation, query, serialization.
- `widgora/routes_widgets.py`: split route layer from application service.
- `social-media-agent/deployment/daily-card/daily_card.py`: split data fetch, card model, rendering, delivery.
- duplicated UI Home pages: run duplication report before extraction.

## qc-telephony-api

### HYG / TREE

- `.gitignore`: ignore `.claude/`, `.codex/`, `.venv/`, caches, screenshots, Zone.Identifier.
- root screenshots/env images: remove from active tree or move to ignored evidence folder.

### DTO / DOC

- `src/api/shared/*_models.py`: either rename/move to `src/api/contracts/` or document as contract-owned.
- `src/api/shared/errors.py` (new): problem/error DTOs.
- `docs/api-specs/`: decide source-of-truth vs generated artifact.
- `schemas/openapi.json` or updated `docs/api-specs/openapi.yaml`: add breaking-change tests.
- `docs/adr/0001-stateless-telephony-api.md` (new).
- `docs/adr/0002-callback-hmac-contract.md` (new).

### PONY

- `src/api/function_app.py`: split into `routes/transcribe.py`, `routes/translation.py`, `routes/qa.py`, `routes/insights.py`, `routes/batch.py`, `routes/health.py`.
- `src/api/shared/translation_service.py`: inspect for provider/client/domain split.
- `src/api/shared/scribe_v2_service.py`: inspect transport vs mapping vs domain contract split.

### PIPE / TEST

- `azure-pipelines.yml`: remove advisory `|| true` from ruff/mypy once baseline is green or explicitly baseline failures.
- Add import-linter config.
- Add idempotency/callback contract tests.

## seekapa-training-platform

### HYG / TREE

- `.gitignore`: root `node_modules`, `frontend/node_modules`, `.playwright-mcp`, backend caches, `.python_packages`, local report render outputs.
- `reports/`, `qa_reports/`, `data/retention_*`: classify generated vs canonical fixtures.
- `scripts/deploy_retention_agents_v2_backup.py`: archive/delete if obsolete after comparison.

### DTO / DOC

- `backend/contracts/` (new):
  - `sessions.py`
  - `progress.py`
  - `reports.py`
  - `elevenlabs.py`
  - `admin.py`
  - `errors.py`
- `backend/shared/utils.py`: replace generic `error_response` with typed error responses.
- `frontend/src/api/*`: generate or align TS types from backend DTO/OpenAPI.
- `docs/API_CONTRACT.md`: make generated or schema-backed.
- `docs/adr/0001-training-platform-boundaries.md` (new).
- `docs/adr/0002-elevenlabs-webhook-contract.md` (new).
- `docs/RUNBOOK.md`: backend and frontend rollback.

### PONY

- `backend/shared/email_service.py`: split config, template/rendering, transport, queue/retry.
- `backend/shared/retention_report_html.py`: split data model from HTML rendering.
- `frontend/src/pages/GuestSessionReport.tsx`: split data query, layout, sections, export actions.
- Many `backend/*/__init__.py` function folders: thin wrappers only after services/contracts exist.

### PIPE

- `azure-pipelines.yml`: replace `az acr build` with agent `docker build` + `docker push`.
- Add bandit, semgrep, secret scan, mypy/pyright.

## video-understanding

### HYG / TREE

- `.gitignore`: generated media, workdir, nested node_modules, `.agents`, `.claude`, `.codex`, `.playwright-mcp`, ebook venv, Zone.Identifier.
- `workdir/`: ignored generated output, not repo source.
- `ui-ux-pro-max-skill/`: decide vendor, submodule/subtree, or remove from this repo.
- `video-generator (1)/`: inspect and archive/delete if duplicate generated copy.
- `video-gen/out`, `video-gen/dist`, generated media: ignore or artifact-store.

### DIR DECISION

Option A: monorepo packages:
- `packages/extractor`
- `packages/generator`
- `packages/video-gen`
- `packages/ebook-task`

Option B: split creative tools into separate repos and keep `video-understanding` as shared QA/eval brain.

Write ADR before moving.

### DTO / DOC

- `schemas/`: make source of truth for design evaluator and creative gates.
- `generator/contracts.py` (new): Pydantic mirrors for schemas.
- `extractor/contracts.py` (new): pipeline input/output DTOs.
- `docs/REPO-MAP.md` (new).
- `docs/adr/0001-creative-understanding-monorepo.md` (new).
- `docs/API_CONTRACT.md` only if exposing HTTP API; otherwise `docs/PIPELINE_CONTRACT.md`.

### PONY

- `video-gen/remotion/src/HowToOpenPosition*.tsx`: split scenes, copy, timing, assets.
- `ebook-task/src/content.py`: split content model, generation, rendering.
- duplicated `design_system.py`: pick one source, vendor or package it.
- `extractor/pipeline.py`: split stage contracts from orchestration.

## sales-agents

### HYG / TREE

- `.gitignore`: generated outputs, exports, voice samples, test-results, research PDFs if not canonical, `.claude`.
- `test-results/*`: keep only curated golden summaries; move run outputs to ignored artifacts.
- `output/`, `exports/`, `data-inputs/`: classify as fixtures vs generated/private input.

### DTO / DOC

- `docs/PRODUCTION-GAP.md` (new): explicitly state prototype vs production promotion path.
- `src/contracts/` or `functions/contracts.py` (new):
  - ElevenLabs webhook DTO
  - lead import DTO
  - lead status update DTO
  - call record DTO
  - health/list response DTO
  - typed error DTO
- `docs/API_CONTRACT.md` (new).
- `docs/adr/0001-sales-agent-production-boundary.md` (new).

### PONY

- `functions/function_app.py`: split webhook, leads, calls, health routes.
- `src/testing/human_likeness_evaluator.py`: split metrics, judge prompt, report rendering, orchestration.
- `src/database/service.py`: split connection/repository/query/domain services.
- `scripts/*voice*`: classify one-off scripts vs reusable CLI.

### PIPE / TEST

- `azure-pipelines.yml` (new): production CI/CD.
- `azure-pipelines-voice-tests.yml`: keep as semantic/eval lane, not primary software gate.
- `pyproject.toml` (new or normalized): ruff, mypy/pyright, pytest, coverage.
- Add recorded ElevenLabs webhook fixtures and endpoint contract tests.

## Implementation Order

1. Global ignore/artifact policy.
2. Per-repo `REPO-MAP.md` and ADR for boundary decisions.
3. DTO/error contract layer for the first target repo.
4. Tests for those contracts.
5. Pipeline gate normalization.
6. Ponytail split of the largest file.
7. Repeat.

Recommended first target: `qc-telephony-api`, because contract models already exist and the risk is bounded.
