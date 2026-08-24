# Autonomous Technology Corpus Research Protocol

**Created:** 2026-07-24  
**Research anchor:** Cloudflare Developer Platform  
**Consumers:** Shoval's learning platform and resume engine  
**Mode:** Dynamic discovery, official-primary-source first, evidence-gated

## Mission

Act as a principal technical research architect and corpus engineer. Build an
evergreen, machine-readable technology documentation corpus that:

1. teaches the modern production stack needed for AI-native, data-intensive,
   real-time applications;
2. recommends concrete labs and projects appropriate to the learner's current
   level;
3. supplies a resume engine with current market vocabulary and defensible skill
   mappings; and
4. never converts reading, documentation familiarity, or generated examples
   into false hands-on experience.

Cloudflare is the anchor platform, beginning with Cloudflare Pipelines, but the
research must discover the complementary domains and category leaders required
to design and operate complete systems. Do not use a permanently hardcoded tool
list as the research boundary.

## Grounded user and system context

- Current positioning: junior to early-mid AI / Applied AI / Full-Stack
  Solutions Engineer, not Senior, Lead, Principal, or Platform Architect.
- Existing defensible strengths include Python, TypeScript/React, Azure
  Functions and AI services, PostgreSQL, LLM-agent integration, MCP, evaluation
  work, multilingual product delivery, and cross-functional implementation.
- Existing learning-platform reference implementation:
  `projects/seekapa-training-platform` (React, TypeScript, Python, Azure
  Functions, PostgreSQL, ElevenLabs, Azure OpenAI, evaluation and progression).
- Resume source of truth:
  `resumes_2026/gen.py`, its generated variants, `loop_config.json`, and the
  local project/evidence inventory. Do not edit generated resume files directly.
- Existing corpus precedent:
  `.claude/corpus/build_best_practices_corpus.py` and `.claude/corpus/sources.json`.
- The new corpus must support two distinct outputs:
  - **learning output:** prerequisites, concepts, labs, assessments, and mastery
    evidence;
  - **resume output:** market keywords plus only evidence-backed claims.

## Non-negotiable research rules

1. Use current official product documentation, specifications, official
   repositories, official engineering blogs, and pricing/limits pages as the
   primary evidence. Use independent sources only for clearly labelled
   comparison or operational experience that the vendor does not document.
2. Record the exact canonical URL, source owner, source type, product area,
   retrieval date, last-updated date when exposed, version, license/terms,
   ingestion permission, and refresh cadence.
3. Every volatile statement about limits, pricing, product status, regional
   availability, API shape, or model support requires a direct citation and an
   `as_of` date.
4. Distinguish documented fact, vendor claim, standards requirement, measured
   local evidence, and researcher inference.
5. Do not infer private implementation internals. If a vendor does not document
   its consensus, replication, hardware, or memory model, record `not publicly
   documented`.
6. Prefer stable documentation roots, `llms.txt`/`llms-full.txt`, sitemaps,
   OpenAPI/specification files, and official docs repositories over arbitrary
   page scraping.
7. Respect robots directives, licenses, rate limits, and terms. When full-text
   ingestion is not clearly allowed, store metadata, a short factual summary,
   and the canonical link rather than copied page content.
8. Deduplicate by canonical URL and content hash. Preserve source/page lineage
   through every chunk and every derived learning or resume record.
9. No fabricated benchmarks, metrics, production usage, cost savings, latency
   improvements, or resume bullets.
10. Research breadth is not mastery. A technology may be marked `discovered`,
    `read`, `lab_verified`, `project_verified`, or `production_verified`; never
    collapse those states.

## Phase 0 — Inspect the consumers before researching

Inspect the real local contracts for the learning platform, resume generator,
resume routing configuration, project evidence, and existing corpus builder.
Document:

- fields each consumer can use now;
- fields or adapters the new corpus must add;
- which files are canonical versus generated;
- how evidence and provenance must flow;
- what can be integrated safely without touching production systems.

If the named workspace path is stale, locate the active copy and record the
resolved path. Do not silently write to a duplicate or archived project.

## Phase 1 — Dynamic domain map

Derive the technology domains from two inputs:

1. capabilities needed by a production-grade interactive AI learning platform;
2. recurring requirements in relevant junior/early-mid AI Engineer, Applied AI,
   Full-Stack Solutions, Forward-Deployed, Data Scientist, and Data Analyst
   roles.

Create a domain map broad enough to cover the full system lifecycle. Expected
domain shapes may include, but are not limited to:

- edge compute and delivery;
- event ingestion, streaming, queues, and CDC;
- workflow orchestration and durable state;
- transactional, analytical, vector, graph, object, and lakehouse storage;
- model inference, gateways, routing, and serving;
- agent frameworks, tool protocols, and MCP;
- multimodal voice/video and real-time transport;
- data processing, analytics, and evaluation;
- frontend, streaming UI, and application backends;
- identity, secrets, zero trust, and software supply-chain security;
- observability, LLM tracing, testing, and SRE;
- infrastructure as code, CI/CD, containers, and deployment;
- governance, privacy, safety, and cost control.

For every domain:

1. identify the open standard or foundational project where one exists;
2. identify the relevant hyperscaler services;
3. identify one or more category-leading independent platforms;
4. identify the most relevant source for the existing stack;
5. score each candidate rather than selecting it because it is popular.

Use this weighted source-value score:

```text
source_value =
  0.25 * relevance_to_existing_projects +
  0.20 * frequency_in_target_roles +
  0.15 * architectural_leverage +
  0.15 * hands_on_feasibility +
  0.10 * documentation_quality +
  0.10 * interoperability_or_portability +
  0.05 * cost_accessibility
```

Each factor is 0–5 and must include a short rationale. Popularity alone is not
an admissible score.

## Phase 2 — Cloudflare anchor map

Map the current Cloudflare developer platform from its official documentation
taxonomy. Begin with Cloudflare Pipelines and follow its actual dependencies and
adjacent products. At minimum, verify whether the current platform contains
relevant capabilities in:

- compute and state;
- ingestion, queues, streaming, pipelines, and workflows;
- relational, key-value, object, vector, analytics, and lakehouse storage;
- AI inference, AI gateways, agents, browser/automation, and model protocols;
- media and real-time communications;
- application security, identity, zero trust, networking, and delivery;
- observability, developer tooling, IaC, limits, pricing, and platform status.

Do not assume names or availability from prior conversations. Discover the
current taxonomy and lifecycle status from Cloudflare's official sources.

For each Cloudflare product or capability, record:

- what problem it solves and when not to use it;
- data/control flow and documented runtime model;
- bindings, APIs, CLI/IaC entry points, and local-development path;
- supported integrations and open formats;
- consistency/state model when documented;
- exact limits, pricing dimensions, lifecycle status, and failure modes;
- identity, network, tenant-isolation, and secrets model;
- observability and testability;
- one learning objective and one small evidence-producing lab;
- relevant resume vocabulary, with no claim of experience until the lab or
  project evidence exists.

## Phase 3 — Complementary source discovery

Use gaps in the Cloudflare map to discover the other source families. Compare
platforms by architectural role rather than producing a brand list. The final
catalog must include a balanced mix of:

- open standards and portable foundations;
- the existing Azure stack;
- AWS and Google Cloud equivalents where they materially improve job-market or
  architecture coverage;
- category leaders in data, durable execution, vector retrieval, voice/video,
  model serving, observability/evaluation, application delivery, security, and
  developer infrastructure;
- only sources with a clear learning or system-design reason.

Index all useful source families at catalog depth. Apply detailed extraction to
the highest-value families and place lower-value discoveries in a ranked
backlog. Do not pretend an unlimited research task is complete.

Recommended depth tiers:

- **Tier A — deep:** Cloudflare anchor plus the highest-value cross-domain
  sources needed by the learning-platform architecture and current resume lanes.
- **Tier B — working:** important alternatives and interoperability sources.
- **Tier C — watch:** emerging, duplicative, expensive, niche, or currently
  premature sources.

## Phase 4 — Per-source extraction contract

For every cataloged source family, produce a source card with:

```yaml
identity:
  id:
  owner:
  product:
  domain:
  canonical_url:
  documentation_roots: []
  source_type:
  official: true
  lifecycle:
  version:
  retrieved_at:
  last_updated_at:
rights:
  license_or_terms:
  robots_or_crawl_notes:
  ingestion_mode: full_text | metadata_summary_links | api_spec
  attribution_required:
relevance:
  source_value_score:
  rationale:
  depth_tier:
  prerequisites: []
  target_roles: []
technical:
  problems_solved: []
  architecture_summary:
  interfaces: []
  limits: []
  failure_modes: []
  security: []
  observability: []
  cost_dimensions: []
  portability: []
learning:
  objectives: []
  labs: []
  assessment_evidence: []
resume:
  market_terms: []
  potential_claims: []
  minimum_evidence_required: []
provenance:
  citations: []
  fact_inference_notes: []
refresh:
  volatility: low | medium | high
  cadence:
  change_signals: []
```

Detailed technical notes should cover six dimensions where the official source
actually provides evidence:

1. architecture and execution/data model;
2. limits, reliability, and failure handling;
3. configuration, SDK, CLI, API, and IaC;
4. a minimal lab pattern in Python or TypeScript;
5. pricing dimensions and cost traps;
6. security, identity, governance, and isolation.

Do not generate a giant production-ready code sample for every indexed tool.
Code belongs in a lab only when it will be run and verified.

## Phase 5 — Learning-platform projection

Transform the catalog into a progressive curriculum:

- prerequisite graph;
- domain → concept → lab → assessment sequence;
- estimated effort and cost;
- local/cloud requirements;
- evidence artifact created by each lab;
- rubric with observable pass criteria;
- spaced refresh/reassessment interval;
- recommended next lesson derived from skill gaps and target-role demand.

Every lab must produce durable evidence such as a repository commit, test
result, architecture decision record, benchmark with methodology, deployment
record, screenshot, or queryable event trace. Reading completion alone is not
proof of implementation ability.

The adapter should be compatible with the existing training concepts where
reasonable, but must not write to the live Seekapa production database or deploy
the proprietary platform.

## Phase 6 — Resume-engine projection

Create a resume skill/evidence graph, not a marketing-text generator.

Allowed state transitions:

```text
discovered -> read -> lab_verified -> project_verified -> production_verified
```

Resume policy:

- `discovered` and `read`: may inform learning priorities and ATS vocabulary
  analysis only; never appear as hands-on skills.
- `lab_verified`: may appear under projects/labs with explicit scope.
- `project_verified`: may support a project bullet when linked to concrete
  artifacts and explainable decisions.
- `production_verified`: may support experience bullets when employer/project
  evidence and metrics are present.
- Quantified claims require a metric, baseline, method, time window, and evidence
  locator.
- Generated examples are labelled `candidate wording`, never merged
  automatically into `resumes_2026/gen.py`.
- Calibrate titles and wording to junior/early-mid roles unless the evidence
  later justifies a different level.

Each possible claim must contain:

```yaml
claim_id:
skill_id:
claim_text:
claim_state:
resume_lanes: []
evidence_ids: []
metric:
  value:
  unit:
  baseline:
  method:
  window:
confidence:
review_required: true
```

## Phase 7 — Corpus packaging

Produce:

1. the frozen research prompt;
2. a human-readable research report;
3. a machine-readable source catalog;
4. a corpus schema and validator;
5. learning objectives/labs projection;
6. resume skills/claims projection;
7. source coverage and gap report;
8. refresh policy and changelog format;
9. example queries for both consumers;
10. a small verified seed corpus.

The seed corpus should be practical and testable. Do not mirror the entire web
or claim comprehensive page-level coverage when only documentation roots were
verified.

## Quality gates

The work is complete only when:

- all catalog records validate against the schema;
- every fact in the human report can be traced to an official URL;
- all current/volatile facts have retrieval dates;
- Cloudflare Pipelines is researched at Tier A depth;
- complementary sources cover the complete learning-platform lifecycle;
- the catalog distinguishes catalog-depth from deep-researched coverage;
- learning recommendations cite prerequisites and produce evidence;
- resume projections contain no unearned hands-on claims;
- examples clearly separate documented capability from locally verified work;
- dead links, duplicates, licensing ambiguity, and missing refresh policies are
  reported rather than hidden.

## Final reporting style

Lead with the architecture and priority decisions. Be concise at catalog level
and detailed only for high-value sources. State what was verified, what was
inferred, what remains unresearched, and what the learner should build next.
Use direct links to the official sources and include an `as_of` date.
