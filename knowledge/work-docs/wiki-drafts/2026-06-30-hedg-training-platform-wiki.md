# HEDG Training Platform

A voice-based training platform for call-center agents at the HEDG Jordan operation, in production today. An agent picks a level, talks through a realistic scenario with an ElevenLabs voice agent for a few minutes, and within minutes gets a scored, narrative report by email and on a dashboard. Azure OpenAI grades each call against a fixed rubric (10 dimensions for Retention, 15 for Sales), and the same numbers feed the agent's own dashboard, a manager's team view, and a director's branch view. Agents self-register; managers, directors, and admins are promoted from there.

The product was built as "Seekapa Training Platform" and is being rebranded to a single brand, HEDG, for the Jordan call center, in English and Arabic. The rebrand is partially shipped: the running content today is English Sales and Arabic Retention. Arabic Sales and English Retention are not real content yet, and the visual rebrand still has Seekapa residue. Both are tracked below under What changed since the old wiki.

No customer is ever called by this platform. The voice agent is a synthetic trainer; the only people who talk to it are agents in training.

- **Frontend (live):** https://training.corp-domain.com (Azure Static Web App, Cloudflare-fronted)
- **Backend API:** Azure Functions `comp-seekapaaitrainingapi-prod` (CORS locked to the SWA origin)
- **Repo:** `Corp-AI/seekapa-training-platform` (internal name retained) | **Pipeline:** Azure DevOps `azure-pipelines.yml`
- **Resource group:** `AZAI_group`
- **Owner:** Shoval Benjer (engineering)

---

## Contents

1. [What the platform does](#what-the-platform-does)
2. [The content matrix (what is actually live)](#the-content-matrix-what-is-actually-live)
3. [The session pipeline](#the-session-pipeline)
4. [How a call is scored](#how-a-call-is-scored)
5. [Reports and email](#reports-and-email)
6. [Roles and access](#roles-and-access)
7. [Architecture](#architecture)
8. [Database](#database)
9. [API reference](#api-reference)
10. [Security and data protection](#security-and-data-protection)
11. [Operations](#operations)
12. [Development](#development)
13. [What changed since the old wiki](#what-changed-since-the-old-wiki)

---

## What the platform does

An agent in the HEDG Jordan call center opens the web app, picks a track (Sales or Retention), a language (English or Arabic), and a level, and starts a session. The frontend opens a live voice connection to an ElevenLabs agent whose persona is fixed by the chosen level, and the agent role-plays a realistic customer for roughly three to ten minutes, longer at higher levels. When the call ends, the platform fetches the transcript, sends it to Azure OpenAI for scoring against the track's rubric, stores the scores and a narrative report, and emails the report to the agent. The agent sees their scores and trend on a personal dashboard; managers see a team roll-up; directors see a branch view.

The same calculation feeds every surface, so an agent's email, their dashboard, and their manager's team view tell the same story rather than three drifting ones. A guest can also take a session without an account through a public guest flow, and gets a one-off report URL instead of a dashboard.

| Surface | Who it is for | What it shows |
|---|---|---|
| Personal dashboard | The agent | Their own scores per session and trend over time |
| Team dashboard | Manager | Aggregated performance across the manager's team |
| Branch dashboard | Director | Branch-level roll-up across teams |
| Drip email report | The agent (and on demand, managers) | The per-session narrative report and scores |
| Guest report | A guest with no account | A single session's report at a one-off URL |

---

## The content matrix (what is actually live)

The product is designed as two tracks (Sales, Retention) across two languages (English, Arabic), but not all four cells have real content. This is the single most important thing to understand before demoing or planning, because the old wiki implies all cells exist and they do not.

| | English | Arabic |
|---|---|---|
| **Sales** | Live. 5 levels, escalating difficulty. | Not real content. The "Arabic sales" rows were mislabeled duplicates of English/Spanish levels and were soft-disabled by migration 018 (2026-06-03). Genuine Arabic sales scenarios are a content task, not built. |
| **Retention** | Not real content. The English retention registry falls back to the Arabic retention scenarios ("English retention TBD" in `levelDefinitions.ts`). | Live. Arabic retention scenarios, scored on the 10-dimension Retention rubric. |

So the two genuinely live cells today are **English Sales** and **Arabic Retention**. Each track exposes 5 levels. Level 1 is a roughly three-minute basics scenario; Level 5 is a roughly ten-minute scenario with multi-layered objections. Per-level expectations are leniency-graded: low levels forgive advanced technique, high levels expect it. Recommended durations are enforced in `prompts.py` (`LEVEL_RECOMMENDED_DURATIONS`).

A note on Spanish: the codebase still carries Spanish-LATAM level definitions and a set of Spanish agent scripts. That content is legacy and out of scope for the HEDG Jordan rollout. It is not part of the current product and should not be presented as such. See What changed since the old wiki.

---

## The session pipeline

What runs from the moment an agent clicks start until the report email lands.

::: mermaid
sequenceDiagram
    autonumber
    participant U as Agent (trainee)
    participant F as Frontend (SWA)
    participant API as Function App
    participant DB as PostgreSQL
    participant E as ElevenLabs
    participant LLM as Azure OpenAI
    participant ACS as ACS Email
    U->>F: Pick track + language + level, start
    F->>API: POST /start_session (or /start_guest_session)
    API->>DB: INSERT training_sessions
    API->>API: Issue ElevenLabs WebSocket token
    API-->>F: session_id + ws token
    F->>E: WebSocket open (agent_id from level)
    U->>E: Voice conversation (3 to 10 min)
    alt Webhook completion (preferred)
        E->>API: POST /webhook_elevenlabs (HMAC signed)
    else Timer fallback
        API->>E: Pull completed conversations (every 5 min)
    end
    API->>E: GET full transcript (re-fetched at report time)
    API->>LLM: Evaluate (15-dim Sales OR 10-dim Retention)
    LLM-->>API: Scores + narrative JSON
    API->>DB: INSERT session_scores, llm_evaluations, analysis_reports
    API->>DB: ENQUEUE report_email_queue
    API->>ACS: Send drip email (timer drains the queue)
    ACS-->>U: Personalised report
    F->>API: Poll /get_session_detail
    API-->>F: Scores + narrative
    F-->>U: Dashboard updates
:::

Step by step:

1. **Session start.** `start_session` (authenticated) or `start_guest_session` (public) inserts a row into `training_sessions` and returns the level's `elevenlabs_agent_id` plus a fresh, short-lived WebSocket token from `get_elevenlabs_token`.
2. **Voice conversation.** The frontend opens an ElevenLabs WebSocket. The agent persona is fixed by `training_levels.elevenlabs_agent_id`. Duration scales with level.
3. **Completion detection.** Two paths. The preferred one is the ElevenLabs webhook to `webhook_elevenlabs`, whose HMAC signature is validated against the webhook secret. The fallback is the `sync_sessions` timer (every five minutes), which pulls completed conversations in case a webhook is missed.
4. **Transcript fetch.** The full transcript is re-fetched from ElevenLabs at report time. This is a deliberate fix: an earlier version could ship a mid-conversation (partial) transcript into the report, because the stored `call_recordings` copy was sticky-partial. The report now pulls the final transcript from ElevenLabs rather than trusting a possibly-partial stored copy.
5. **LLM evaluation.** `llm_evaluator` selects the Sales or Retention prompt from the level metadata, calls Azure OpenAI with retry and exponential backoff, and gets back strict JSON: a per-dimension score, cited evidence, feedback, and a summary.
6. **Persist and enqueue.** Scores go to `session_scores`, the structured evaluation to `llm_evaluations`, the narrative to `analysis_reports`, and a queued report to `report_email_queue` (idempotent per session).
7. **Drip email.** A timer drains `report_email_queue` through Azure Communication Services, one report per session. Arabic sessions get a sanitised report variant. Stale in-flight rows are recovered after about ten minutes so a crash mid-send does not strand a report.

---

## How a call is scored

Scoring is the heart of the product. Azure OpenAI is given the transcript and a track-specific rubric, and must return a score (1 to 10) for each dimension with cited evidence from the transcript, plus a weighted overall score, a pass flag, and a strengths/weaknesses/improvements summary. The prompts live in `backend/shared/prompts.py` (Sales) and `prompts_retention.py` (Retention).

**Sales rubric: 15 weighted dimensions.** Greeting and rapport, active listening, empathy and tone, pain-point discovery, product knowledge, objection handling, compliance, DISC adaptation, explanation quality, closing technique, trust building, talk/listen ratio, lead qualification, conversation flow, and overall effectiveness. Objection handling, product knowledge, and closing carry the heaviest weights.

**Retention rubric: 10 dimensions,** tuned for retention conversations, weighting empathy and objection handling higher than the Sales rubric does.

Two honesty rules keep short or incomplete calls from reading as good:

- A call under roughly 180 seconds is treated as incomplete and cannot reach a high score, regardless of how polished the part that did happen was.
- A dimension that was never demonstrated (no objections raised, no close attempted) is scored low with an explicit "NOT DEMONSTRATED" note rather than a charitable guess.

The pass threshold is a weighted overall at or above 7.0. The model and endpoint are configured server-side and are not reproduced here; see the repo for the exact model id, fallback chain, API version, retry policy, and transcript size bounds.

---

## Reports and email

After scoring, the narrative report is rendered and queued for delivery. Transport is Azure Communication Services email, reusing the existing `axia-seekapa-comm` resource (no new infrastructure). The connection string is a secret and lives only in app settings (Key Vault tier); it never appears in the repository, in logs, or in any response. (Note: as of this writing some ops scripts still embed this secret in plaintext, tracked under Security and What changed since the old wiki.)

The email queue is idempotent per session, so a retry never double-sends. Arabic sessions get a sanitised report (short-call cap applied, no spurious composite criteria). A failed send is logged and retried from the queue rather than crashing the sender. Reports can also be force-generated for a single session through an admin endpoint when a report needs to be rebuilt.

---

## Roles and access

There are four roles, each inheriting the one below it. Agents self-register as `rep`; the higher roles are granted by an admin.

| Role | Inherits | Can do |
|---|---|---|
| `rep` | none | Run practice sessions, view own dashboard, generate own reports |
| `manager` | rep | Plus: view the team dashboard, export team reports (XLSX) |
| `director` | manager | Plus: view the branch-level dashboard |
| `admin` | director | Plus: admin functions, role assignment, agent-id updates |

Roles are enforced in two places: a database CHECK constraint on `users.role` (one of `rep`, `manager`, `director`, `admin`), and the `@require_role` decorator in `backend/shared/decorators.py` on each protected endpoint. Authentication is a JWT (HS256) signed with a server-side secret, default 24-hour expiry; the token is stored in the browser as `auth_token` in `localStorage`. Passwords are hashed with bcrypt.

---

## Architecture

Every component is an Azure-managed service in resource group `AZAI_group`. The status column reflects current reality, including one known misconfiguration.

| Component | Service | Resource | Status |
|---|---|---|---|
| Backend | Azure Functions v4 (Linux, Python 3.11) | `comp-seekapaaitrainingapi-prod` | Operational |
| Frontend | Azure Static Web Apps | sales-training frontend (SWA) | Operational |
| Database | Azure PostgreSQL Flexible Server (VNET-only) | `aiprojects-company-postsql` | Operational |
| LLM inference | Azure OpenAI | Foundry project `brn-azai` | Operational |
| Voice AI | ElevenLabs Conversational AI | Voice agents per active level | Operational |
| Email | Azure Communication Services | `axia-seekapa-comm` | Operational |
| Report/audio storage | Azure Blob | `stseekapatrainingprod` | Operational |
| Function host storage | Azure Storage (host metadata, leases) | `stsentimarkv2` | Wrong account, see note |
| Container registry | Azure Container Registry | `seekapatrainingacr` | Operational |
| Observability | Application Insights | `sales-training-platform-insights` | Operational |
| Secrets | Azure Key Vault (shared) | `kv-seekapa-apps` | Operational |

**Storage account note.** The Function App's `AzureWebJobsStorage` points at `stsentimarkv2`, which belongs to a different project. A correctly-named account, `stseekapatrainingprod`, exists in the same resource group and should be used instead. This is not a quick swap: the host's singleton leases and timer state would have to be re-established. Tracked as a planned migration.

---

## Database

| Property | Value |
|---|---|
| Server | `aiprojects-company-postsql.postgres.database.azure.com` |
| Database | `seekapa_training` |
| Runtime user | `training_app_user` (cannot read other project databases) |
| DDL user | admin server role (DDL only, never used from app code) |
| Network | VNET-only, no public access from dev machines |
| Connection secret | held in Key Vault `kv-seekapa-apps` (secret name not reproduced here) |

The runtime user is grant-scoped to `seekapa_training` only. Even if a connection string were wrong, it could not read other tenants' databases on the same server. Schema changes (DDL) require the admin role, which application code must never use.

**Core tables:**

| Table | Purpose |
|---|---|
| `users` | Accounts; foreign key to `teams` |
| `teams` | Grouping under a `branches` row |
| `branches`, `organizations` | Tenancy and hierarchy |
| `training_levels` | The levels per track and language; holds `elevenlabs_agent_id` and an `is_active` flag |
| `training_sessions` | Every session, started or completed |
| `session_scores` | The numeric scores per session |
| `analysis_reports` | The full narrative report (markdown) |
| `llm_evaluations` | The structured LLM output in typed columns |
| `report_email_queue` | The drip-email outbox (idempotent) |

**Migrations.** Numbered SQL files live in `database/migrations/` (repo-level) and `backend/migrations/` (function-app-relative). The database is VNET-only, so migrations are applied through the Azure Portal Query Editor, which has VNET access. Helper scripts exist (`scripts/run-migration.sh` for a single migration with a confirmation prompt, `scripts/apply-database-schema.sh` for the full schema). A schema-affecting change must be applied to the database before its PR merges to the deploy branch, or the next deploy starts failing with column-not-found errors. The most recent migration, 018 (2026-06-03), soft-disabled the mislabeled Arabic-branch sales levels (see the content matrix).

---

## API reference

Base URL: the `comp-seekapaaitrainingapi-prod` Function App, `/api`. CORS is locked to the SWA origin. Auth is a JWT bearer token (`Authorization: Bearer <token>`) issued by `/login`. Role gates are the `@require_role` decorator.

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health_check` | GET | public | Liveness probe (used by smoke tests) |
| `/list_levels` | GET | public | List levels (filter by `?language=`) |
| `/login` | POST | public | Issue a JWT |
| `/register` | POST | public | Create a user (self-register as `rep`) |
| `/start_session` | POST | rep+ | Begin an authenticated session |
| `/start_guest_session` | POST | public | Begin a guest session |
| `/get_session_detail` | GET | rep+ | Session transcript and scores |
| `/get_guest_session` | GET | public | Guest report by session id |
| `/get_elevenlabs_token` | GET | public | Issue an ElevenLabs WebSocket token |
| `/personal_stats` | GET | rep+ | Personal scoring trend |
| `/get_user_progress` | GET | rep+ | Per-user level progression |
| `/team_stats` | GET | manager+ | Team performance |
| `/get_team_performance` | GET | manager+ | Detailed team breakdown |
| `/export_team_report` | GET | manager+ | XLSX export |
| `/ai_reports` | GET/POST | rep+ | Generate an AI performance report |
| `/retention_report` | GET | manager+ | Retention practice analytics |
| `/generate_report` | POST | rep+ | Force-generate a report for one session |
| `/llm_evaluate` | POST | admin | Re-run the evaluator on a session |
| `/retry_evaluations` | POST | admin | Retry failed evaluations |
| `/admin_setup` | POST | admin | Initial admin bootstrap |
| `/admin_unlock_level` | POST | admin | Unlock a level for a user |
| `/set_manager_role` | POST | admin | Promote a user to manager/director |
| `/update_agent_ids` | POST | admin | Refresh ElevenLabs agent ids in the database |
| `/backfill_arabic_emails` | POST | admin | Replay Arabic-session emails |
| `/webhook_elevenlabs` | POST | HMAC | ElevenLabs completion webhook |
| `/monitor_webhook` | GET | admin | Diagnostic on webhook health |

All endpoints return JSON. Errors use an HTTP status code plus a JSON body of the shape `{ "error": "human-readable message", "code": "OPTIONAL_MACHINE_CODE" }`.

---

## Security and data protection

| Property | How it is enforced |
|---|---|
| Database isolation | The runtime user `training_app_user` is grant-scoped to `seekapa_training` only; other databases on the server are blocked at the role level |
| No DDL from app code | Schema changes require the admin server role, never used by the application |
| Network boundary | PostgreSQL is VNET-only (reached via VNET integration); the Function App allows public ingress but CORS is locked to the SWA origin; the SWA is public; Key Vault is reached via Managed Identity |
| Secrets at rest | Production secrets live in Key Vault `kv-seekapa-apps`, resolved by Key Vault references in app settings; local dev uses a gitignored settings file; a populated env file is never committed |
| Webhook authenticity | `webhook_elevenlabs` validates the ElevenLabs HMAC signature against the webhook secret (validator in `backend/shared/webhook_validator.py`, covered by unit tests) |
| Audit logging | Sensitive actions (team-dashboard access, level unlock, role change) are written to a dedicated audit table via `backend/shared/audit_logger.py` |
| Transport | HTTPS-only ingress with HTTP-to-HTTPS redirect; PostgreSQL connections use `sslmode=require` |
| Password storage | bcrypt, cost factor 12 |

**Open security item: secrets in scripts.** Several operations scripts under `scripts/` still contain hardcoded production secrets (an ElevenLabs API key, an ACS connection string) in plaintext, and these values are also in repo history. They need to be sanitised and the keys rotated. A cleanup pass already deleted four archive scripts that tripped Azure DevOps push protection, but the active scripts remain. This is a P0 follow-up. No secret value is reproduced in this page.

**Data retention.** Transcripts are retained indefinitely in `analysis_reports`. Audio is stored in Blob (`stseekapatrainingprod`); a formal retention policy is still to be set. Application Insights uses default retention (roughly 30 days for exceptions and requests), so historical operational queries past about a day often come back empty. Email-queue rows are retained after send to support idempotent retry. JWT signing-key rotation is currently manual through Key Vault, not automated.

---

## Operations

### Health checks

| Check | How | Expected |
|---|---|---|
| Function host alive | `curl https://comp-seekapaaitrainingapi-prod.azurewebsites.net/` | HTTP 200, default Azure landing |
| App reachable | `curl /api/health_check` | HTTP 200, JSON `{ "ok": true, ... }` |
| Levels load | `curl "/api/list_levels?language=english"` | HTTP 200, JSON array of levels |

If `/api/health_check` returns 404, the worker process failed to import, most often a missing dependency. Check Application Insights `exceptions` for `ModuleNotFoundError`. This is the exact failure mode of the April 2026 outage (see What changed since the old wiki).

### Tail backend logs

```bash
az webapp log tail --resource-group AZAI_group --name comp-seekapaaitrainingapi-prod
```

### Application Insights

Component `sales-training-platform-insights`. Use the component AppId (held in the repo/portal, not reproduced here) with `az monitor app-insights query`, for example top exceptions in the last day, or per-function failure rate. Retention is short, so queries past about a day often return empty.

### Background timers

| Timer | Cadence | What it does |
|---|---|---|
| `sync_sessions` | every 5 min | Pulls completed ElevenLabs sessions for transcripts |
| `poll_conversations` | every 5 min | Polls active conversations for state changes |
| `email_drip_sender` | every 5 min | Drains `report_email_queue` and sends via ACS |

If a timer fails, check first for the `ModuleNotFoundError` failure mode (a missing `psycopg2` or `azure.communication.email`).

### Common tasks

| Task | Command |
|---|---|
| Restart the Function App | `az functionapp restart --resource-group AZAI_group --name comp-seekapaaitrainingapi-prod` |
| Force a redeploy | Trigger the pipeline manually from Azure DevOps |
| Run a migration | `./scripts/run-migration.sh` (prompts for confirmation) |
| Verify infrastructure | `./scripts/verify-infrastructure.sh` |
| Smoke all endpoints | `./scripts/test_all_endpoints.sh` |

### Deploy and rollback

Backend deploys go through the Azure DevOps pipeline. Never run `func azure functionapp publish` by hand: the Function App has `SCM_DO_BUILD_DURING_DEPLOYMENT=false`, so Oryx does not run `pip install` on deploy. The pipeline bundles dependencies into `backend/.python_packages/lib/site-packages/` before the zip step. A manual publish ships source-only and every function dies with `ModuleNotFoundError` on cold start. That is precisely the April 2026 outage.

The pipeline runs in tiers: lint and unit tests and a Docker build on every build; an AI code review that posts back to the PR; and a deploy-plus-smoke stage on the deploy branch. The branch model is mid-migration: the pipeline currently triggers on `master` (the historical deploy branch) with `main` and `stage` also wired and a `master`-to-`main` migration noted as still to be finalised in `azure-pipelines.yml`. Confirm the active deploy branch before shipping.

Rollback is `git revert <bad-commit>` followed by a push to the deploy branch, which re-runs the pipeline. Caveat: if the deploy step succeeds but the smoke step fails, the broken artifact stays deployed; the smoke test only marks the build failed. Automatic rollback to the last good deploy is a P1 follow-up.

---

## Development

### Run locally

```bash
git clone git@ssh.dev.azure.com:v3/Corp-domain/Corp-AI/seekapa-training-platform
cd seekapa-training-platform

# Backend (port 7071)
cd backend
cp local.settings.json.example local.settings.json   # fill in secrets locally; never commit
pip install -r requirements.txt
func start

# Frontend (port 5173), separate terminal
cd frontend
npm install
npm run dev
```

Required backend settings (in the gitignored local settings file): the PostgreSQL connection values, the ElevenLabs API key, the Azure OpenAI key and endpoint, the JWT secret, and the ACS connection string. Production resolves all of these via Key Vault references. The database is VNET-only, so local development needs either a VNET tunnel (bastion or jump host) or a local PostgreSQL seeded from `database/schema.sql` plus `database/seed_test_data.sql`. The connection pool in `backend/shared/database.py` is a singleton holding 1 to 10 connections.

### Tests

```bash
cd backend && python -m pytest tests/     # backend unit tests
cd frontend && npm run test               # Playwright end-to-end
cd frontend && npm run test:personal      # personal dashboard suite
cd frontend && npm run test:team          # team dashboard suite
```

### Smoke against production

```bash
curl -fsS https://comp-seekapaaitrainingapi-prod.azurewebsites.net/api/health_check
curl -fsS "https://comp-seekapaaitrainingapi-prod.azurewebsites.net/api/list_levels?language=english"
./scripts/test_all_endpoints.sh
```

---

## What changed since the old wiki

This page consolidates six older pages (Training-Platform, Handover-Notes, Compliance, Operations, API-Reference, Database) that were written for "Seekapa Training Platform" before the HEDG Jordan rebrand. The following items in those pages are now outdated or need a flag:

- **Brand.** The product is being rebranded from Seekapa to a single brand, HEDG (navy, amber, teal), for the Jordan call center. The rebrand is iteration 1 and partial: the dashboard, logo, and gradient are repointed to HEDG, but indigo Seekapa primary buttons, Tailwind `seekapa-*` utility colors, and roughly two dozen frontend files still carrying "Seekapa" text strings (footer, login testimonials) all still ship. The internal code slug `seekapa` was kept and repurposed for HEDG to avoid refactoring the dual-brand conditionals, so a code search for "seekapa" will mislead. Treat the brand as in-transition.

- **Languages.** The old wiki describes three languages (English, Gulf Arabic, Spanish-LATAM) and "15 levels." The HEDG Jordan product is English and Arabic only. Spanish-LATAM level definitions and Spanish agent scripts still exist in the repo but are legacy and out of scope; do not present Spanish as a current language.

- **The content matrix is not full.** The old pages imply all tracks and languages have content. In reality only English Sales and Arabic Retention are live. Arabic Sales was mislabeled duplicate content and was soft-disabled by migration 018 (2026-06-03); English Retention falls back to the Arabic retention content and is marked TBD in code. See the content matrix section.

- **Deploy and live state.** The HEDG rebrand work is committed but sits on a non-deploy feature branch and has not been deployed or live-smoked as HEDG. Per the merged-plus-deployed-plus-smoked definition, the HEDG rebrand is not yet "in production"; the platform that is in production is still the pre-rebrand Seekapa build with HEDG changes not yet shipped. Confirm the deployed commit before claiming HEDG is live.

- **Deploy branch.** The old wiki shows `feature/* -> master`. The pipeline is mid-migration to a `stage`/`main` model and currently triggers on `master`, `main`, and `stage`, with the `master`-to-`main` cutover noted as still to be finalised. Confirm the active deploy branch in `azure-pipelines.yml` before shipping.

- **Transcript fix.** Reports could previously ship a partial, mid-conversation transcript because the stored `call_recordings` copy was sticky-partial. The report now re-fetches the final transcript from ElevenLabs at report time and only heals from a final transcript. This is current behavior and was not in the old pages.

- **Still-true carryovers (kept, not changed).** The April 2026 outage (a missing `psycopg2` on cold start, fixed by bundling dependencies into `.python_packages/` before the zip step) is still the canonical deploy hazard. The `AzureWebJobsStorage`-points-at-`stsentimarkv2` misconfiguration is still open. The hardcoded secrets in `scripts/` are still open and still need rotation. The roles, the database isolation model, the VNET-only database, and the API surface are unchanged.

Open follow-ups carried from the handover notes, by priority: P0 sanitise and rotate the hardcoded secrets in `scripts/`; P0 migrate `AzureWebJobsStorage` off `stsentimarkv2`; P1 add smoke-test rollback so a failed smoke does not leave a broken artifact deployed; P1 pin dependencies to a lockfile for deterministic deploys; P2 split the backend and frontend monolith files; P2 add a type-check gate (mypy) in CI.

---

*This page is the consolidated overview for the HEDG Training Platform (formerly Seekapa Training Platform). It replaces the six older Training-Platform wiki pages. Implementation detail lives in the repo README and `docs/`. The HEDG rebrand and the empty content cells are the active work; verify deploy state against the live app before claiming HEDG is in production. Maintained by engineering.*
