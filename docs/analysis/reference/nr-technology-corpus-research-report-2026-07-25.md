# Technology Source Corpus Research Report

Research date: 2026-07-24  
Candidate calibration: junior / early-mid  
Primary consumers: Seekapa learning platform and the local resume engine

## Outcome

The result is a provenance-first corpus package, not a loose bookmark list.
Cloudflare is the anchor research family, but it is deliberately paired with
the candidate's real Azure/Python/PostgreSQL/React/MCP work and with portable
standards.

The package separates four things that must never be collapsed:

1. what official documentation says;
2. what was actually read;
3. what local artifacts prove; and
4. what wording may be proposed for human-reviewed resume use.

Documentation can create a learning item or market term. It cannot create work
experience. Technology progression is:

```text
discovered -> read -> lab_verified -> project_verified -> production_verified
```

The generated learning export is read-only and feature-flagged. The generated
resume export contains market terms plus evidence-gated candidate wording; it
cannot edit the canonical resume generator or rendered files.

## Research method

The complete research prompt was written before browsing. It sets the source
taxonomy, scoring model, evidence states, licensing rules, Cloudflare questions,
learning projection, resume projection, and completion gates.

Each source is scored from 0 to 5 using:

- 25% existing-work alignment;
- 20% target-role alignment;
- 20% learning transfer;
- 15% machine readability;
- 15% operational depth; and
- 5% rights clarity.

Scores prioritize research effort. They do not claim candidate skill or
job-market frequency.

Each source card stores a canonical URL, publisher, tier, current lifecycle,
actually inspected pages, acquisition adapter, rights mode, refresh cadence,
volatile fields, market terms, and target resume lanes.

## Cloudflare findings

### Where Pipelines fits

[Cloudflare Pipelines](https://developers.cloudflare.com/pipelines/) is an
open-beta, Workers Paid product for append-oriented streaming analytics. Its
documented path is:

```text
HTTP / Worker binding / Logpush
        -> durable stream
        -> stateless SQL validation and transformation
        -> R2 JSON or Parquet files
        -> or R2 Data Catalog Iceberg table
        -> R2 SQL / DuckDB / Spark and other engines
```

This is highly relevant as a learning project because it joins event contracts,
stream processing, columnar storage, an open table format, analytics, schema
errors, cost reasoning, and infrastructure management in one bounded system.
It is not yet evidence that the candidate has built or operated Cloudflare
infrastructure.

### Semantics and constraints

- Streams accept JSON and can enforce a structured schema. Pipeline metrics
  expose dropped-record families including `missing_field`, `type_mismatch`,
  `parse_failure`, and `null_value`.
  [Streams](https://developers.cloudflare.com/pipelines/streams/) and
  [metrics](https://developers.cloudflare.com/pipelines/observability/metrics/)
  are therefore both required for a valid lab.
- Current SQL is stateless: selection, filtering, expressions, CTEs, scalar
  functions, `UNNEST`, and multiple `INSERT` statements for fan-out are
  documented. Stateful joins, aggregations, and windows should not be designed
  into the first version.
  [SELECT reference](https://developers.cloudflare.com/pipelines/sql-reference/select-statements/)
- Pipeline SQL is immutable after creation; changing it requires delete and
  recreate.
  [Manage pipelines](https://developers.cloudflare.com/pipelines/pipelines/manage-pipelines/)
- R2 sinks write newline-delimited JSON or Parquet; Parquet defaults to Zstandard.
  The default roll interval is 300 seconds and the documented minimum is 10
  seconds.
  [R2 sink](https://developers.cloudflare.com/pipelines/sinks/available-sinks/r2/)
- The overview describes exactly-once delivery to R2. This is retained as a
  scoped vendor claim, not rewritten as a proven end-to-end guarantee for a
  candidate project.
- Open-beta limits are 20 streams, 20 sinks, and 20 pipelines per account, a
  5 MB maximum ingestion request, and 5 MB/s per stream.
  [Limits](https://developers.cloudflare.com/pipelines/platform/limits/)

### Pricing conflict

The official pages are not fully synchronized:

- the Pipelines overview says usage is not billed beyond standard R2 charges;
- the newer pricing page publishes 50 GB/month included for SQL transforms and
  sinks, then $0.04/GB for transforms, $0.03/GB for JSON sinks, and $0.06/GB
  for Parquet/Iceberg sinks; and
- the changelog says the pricing model was announced while billing was not yet
  enabled and promises notice before charging.

The corpus therefore records both the pricing model and a volatility warning.
It must re-check billing state immediately before any paid lab rather than
choosing a convenient page.
[Pricing](https://developers.cloudflare.com/pipelines/platform/pricing/) and
[Pipelines changelog](https://developers.cloudflare.com/changelog/product/pipelines/)

### Recommended Cloudflare product boundaries

Use:

- Pipelines for event-to-lakehouse analytics;
- Queues for application work distribution and delivery retries;
- Workflows for durable multi-step orchestration and human approval;
- Durable Objects for coordination/state that needs a single logical owner;
- PostgreSQL as authoritative relational state, with Hyperdrive when a
  Cloudflare Worker needs database connectivity;
- R2/Data Catalog/Iceberg for analytical history;
- AI Gateway for model traffic policy/observability; and
- Workers AI/Agents/AI Search only when a measured use case justifies them.

The relevant official roots are
[Workers](https://developers.cloudflare.com/workers/),
[Queues delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/),
[Workflows](https://developers.cloudflare.com/workflows/),
[Durable Objects](https://developers.cloudflare.com/durable-objects/),
[R2 Data Catalog](https://developers.cloudflare.com/r2/data-catalog/),
[Hyperdrive](https://developers.cloudflare.com/hyperdrive/),
[AI Gateway](https://developers.cloudflare.com/ai-gateway/), and
[Agents](https://developers.cloudflare.com/agents/).

### Acquisition strategy

Cloudflare is unusually corpus-friendly operationally: it publishes site and
per-product `llms.txt`/`llms-full.txt`, page-level Markdown, Markdown content
negotiation, OpenAPI schemas, source repositories, and MCP surfaces.
[Cloudflare's agent guide](https://developers.cloudflare.com/docs-for-agents/)
documents these mechanisms.

Those are acquisition mechanisms, not a blanket license. The catalog separately
records documentation, example-code, API-schema, terms, and trademark handling.

## What to include besides Cloudflare

Cloudflare is a strong edge/data/agent source, but it should not become the
corpus backbone by itself.

### Tier A: ingest and refresh first

| Family | Why it belongs |
|---|---|
| PostgreSQL + pgvector | Existing project alignment, durable data semantics, SQL, retrieval, indexing, and broad job transfer |
| Python + FastAPI + Pydantic | Directly evidenced application stack and typed API contracts |
| React + TypeScript + MDN | Current learning-platform frontend and AI-product/full-stack roles |
| Microsoft Learn: Foundry, Functions, Entra, Monitor, PostgreSQL | The candidate's actual work environment; Microsoft also publishes a documentation MCP reference |
| Model Context Protocol | Existing FastMCP/OAuth project evidence and high-value agent-platform vocabulary; pin the versioned specification |
| OpenAI evals + Agents SDK | Evaluation, graders, tracing, lifecycle/deprecation tracking; use only official OpenAI sources |
| OpenTelemetry + OpenInference + MLflow | Portable traces and evaluation evidence instead of vendor-only observability |
| pytest + Playwright + GitHub Actions/Azure Pipelines + Docker | Converts reading and labs into reproducible evidence |
| OWASP + OpenAPI + JSON Schema | Security, authorization, and contract correctness |
| ElevenLabs | Existing voice/STT work; keep websocket, latency, retry, and privacy guidance current |

Official starting points include
[PostgreSQL](https://www.postgresql.org/docs/current/),
[pgvector](https://github.com/pgvector/pgvector),
[Python](https://docs.python.org/3/),
[FastAPI](https://fastapi.tiangolo.com/),
[React](https://react.dev/reference/react),
[TypeScript](https://www.typescriptlang.org/docs/),
[MCP](https://modelcontextprotocol.io/specification/2025-11-25/index),
[OpenAI eval guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices),
[OpenTelemetry](https://opentelemetry.io/docs/),
[OpenAPI](https://spec.openapis.org/oas/latest.html), and
[ElevenLabs](https://elevenlabs.io/docs/api-reference).

### Tier B: use for portability and comparison

- Apache Iceberg, Arrow, Parquet, and DuckDB;
- Temporal, Kafka, Debezium, and CloudEvents;
- NIST AI Risk Management Framework and GenAI Profile;
- LiveKit/WebRTC;
- AWS and Google Cloud documentation connectors;
- Vercel/Next AI when a specific project or role needs it; and
- Hugging Face/vLLM for model-serving or fine-tuning work.

Tier B is not lower quality. It is lower current priority relative to the
candidate's real work and junior/early-mid target lanes.

### Private source families

Two private families remain local-only:

- project evidence: code, tests, CI, reports, bundles, and sanitized locators;
- job demand: current job descriptions after requirements-first review and
  deduplication.

The current job digest is not accepted as clean demand data because it contains
clear routing false positives. Job descriptions must be reduced to requirements,
seniority, location, and recurring terms before affecting a resume.

## Learning-platform integration

The existing Seekapa application is a voice-practice, scoring, and reporting
platform, not a general LMS or document corpus.

Reusable concepts exist in the frontend:

- `name`;
- `description`;
- `prerequisites`;
- `objectives`; and
- `difficulty`.

The database and runtime contracts are not safe corpus targets. The checked-in
schema contains legacy `practice_sessions`/`session_reports`, while runtime
handlers and tests use combinations of `training_sessions`,
`llm_evaluations`, `call_recordings`, and `analysis_reports`. Curriculum data is
also fragmented between database rows, frontend registries, static content, and
remote ElevenLabs prompts.

The integration decision is therefore:

```text
technology corpus
  -> reviewed read-only sidecar bundle
  -> standalone technology-learning catalog behind feature flag
  -> optional manually approved bridge to existing practice levels
  -> evidence export
  -> resume candidate claims
```

No existing level IDs are attached automatically. No production table, score,
session, user, role, agent, or prompt is changed.

Before a future write-enabled import, the platform needs:

1. a canonical content schema;
2. hash-idempotent dry-run and commit endpoints;
3. admin/service authorization;
4. user-owned completion records;
5. a review/retirement lifecycle;
6. privacy separation between public corpus content and user evidence; and
7. remediation of the schema/auth/secret-handling findings in the coverage
   audit.

Suggested additive API surface, only after those gates:

- `POST /api/v1/corpus/import?dry_run=true`;
- `POST /api/v1/corpus/import` after explicit review;
- `GET /api/v1/learning/catalog`;
- `GET /api/v1/learning/units/{unit_id}`;
- `POST /api/v1/learning/completions` with JWT ownership checks; and
- `GET /api/v1/resume-evidence/export` with JWT ownership checks.

## Resume-engine integration and corrected evidence

The canonical resume source is `resumes_2026/gen.py`; the seven active routing
lanes come from `loop_config.json`. The corpus reads both and writes only to
`dist/resume`.

The resume graph contains:

- market terms for gap analysis and ATS review;
- evidence state;
- local evidence IDs;
- target lanes;
- minimum evidence for promotion;
- candidate wording; and
- a hard automatic-write prohibition.

Important corrections discovered during the local audit:

- The `24% to 64%` support-agent improvement is contradicted by a later project
  reflection: the evaluation used the wrong endpoint and the related deployment
  claim was false. It is now a rejected negative evidence record.
- The approximately `$359k` recovery is directional opportunity sizing, not
  achieved revenue.
- Spoken languages are Hebrew and English. Arabic, Spanish, and Portuguese are
  supported delivery languages/markets.
- Corp-home SSO has implementation/tests, but its inspected handoff still had
  one real-browser exchange pending.
- Three social-content formats were enabled; six more were specified but
  disabled.
- Intent-control reliability/eval components are tested but deliberately
  unwired.
- Current hiring tools are interactive/tested components, not a fully autonomous
  hiring daemon.
- The recommendation letter confirms an employment end caused by organizational
  changes/reduced activity and uses `Junior AI Technologist`, while routed
  resumes currently say `Present` and use `AI Engineer`. That chronology/title
  conflict is blocked for review; the letter remains private and
  interview/reference-stage only.

The initial signal file contains both blocked documentation-only technologies
and project-verified candidate wording. All exported claims remain
`review_required=true`; no production-verified signal is asserted.

## Learning sequence

Ten labs were generated. The highest-value order is:

1. provenance-aware corpus build and query;
2. schemas, idempotency, and event contracts;
3. Cloudflare Pipelines to Parquet/Iceberg with a deliberate invalid record;
4. query the lakehouse with R2 SQL or DuckDB;
5. durable workflow with retries and human approval;
6. PostgreSQL/pgvector retrieval with recall/latency evidence;
7. MCP contracts and authorization;
8. evals and portable tracing;
9. realtime voice reliability; and
10. a secure capstone that promotes only retained evidence.

The Cloudflare lab is the clearest near-term opportunity. Its completion can
create a truthful lab/project entry such as “built a schema-validated
event-to-Iceberg prototype” only after the repository, test output, invalid-event
metric, query result, versions, cost, and failure case are retained. It must not
be phrased as production experience.

## Refresh and rights policy

- Daily: model/API lifecycle and explicit deprecations.
- Weekly: beta status, pricing, limits, MCP/SDK compatibility, and agent/eval
  docs.
- Monthly: stable specifications, language/framework concepts, and security
  frameworks.
- Immediate: security advisories and retirement notices.

Full text is stored only where the reviewed rights mode permits it. Otherwise
the corpus stores metadata, canonical links, short original summaries, hashes,
and live connector references. Private project code and job descriptions never
enter the portable corpus.

## Self-review

The research changed course in five material ways:

1. The supplied Gemini transcript treated documentation, learning, and resume
   claims too loosely. The final design makes those separate state transitions.
2. An early package shape was converging before the actual resumes and project
   evidence had been fully audited. The run was reopened and the coverage audit
   added.
3. The local job digest initially looked like usable market data; inspection
   showed false routing, so it was demoted to quarantined input.
4. Narrative manifests looked like corroboration until their identical hashes
   showed they were duplicates.
5. Official Cloudflare pages conflict on billing state. The corpus preserves
   the disagreement and refresh requirement instead of silently choosing one.
6. The first bounded build found that two AI Gateway pages had moved from
   `/platform/` to `/reference/`. The catalog was corrected and URL handling
   was regression-tested before the final build.

The stopping condition is therefore not “all docs read.” It is: all selected
source families and consumer contracts are represented; high-risk claims and
integration surfaces are inspected; failures and gaps are explicit; bounded
builds validate; and no unverified reading, metric, deployment, or language
claim can silently enter a resume.
