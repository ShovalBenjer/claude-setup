# SOTA Testing Criteria 2026 (Gastown canonical rubric)

Status: canonical reference. Authored 2026-06-29. Synthesized from nine SOTA source docs
(classic test taxonomy, agentic-MCP testing pyramid, SOTA video pyramid, SOTA voice
pipeline, Production AI June-2026, Principal Engineer curriculum, Excellent SQL June-2026,
GD Coverage Metric 2030, Next-Gen UI/UX 2026). This rubric is project-type aware: a project
is graded only against the packs that match its type-tags, plus the universal spine and the
cross-cutting overlays that apply.

Output rules for any doc generated from this rubric: no em-dash or en-dash (use comma,
colon, period, or parentheses), no emojis, no AI-slop register. State evidence as
`file:symbol`. Mark every criterion have / partial / gap.

---

## 0. How to use this rubric

1. Read the project's type-tags. Select the matching type packs in section 3.
2. Always apply the universal spine (section 1) and the cross-cutting overlays (section 4)
   that match the project's risk surface (money, CRM, PII, telephony, prod-deployed, media).
3. For any project tagged llm-agent / foundry-agent / rag / mcp-server, also apply the AI
   planes (section 2). This is the highest-value layer for this operator's portfolio.
4. Grade each applicable criterion have / partial / gap with `file:symbol` evidence.
5. Score with section 6. Emit the per-project doc using the template in section 7.

A criterion that does not apply to the project is marked n/a, not gap. Do not penalize a
CLI tool for lacking load tests, or a content repo for lacking RLS. Gap means the criterion
applies and is absent from the test/gate path.

---

## 1. Universal spine: the layered test taxonomy

Every software project is graded against these layers. Confidence comes from coverage
across layers, not from a single coverage percentage. Tests are a specification of system
behavior: invariants, determinism, regression protection, failure modeling.

| # | Layer | Purpose | Primary metric | CI cadence | SOTA tools (Python / JS) |
|---|---|---|---|---|---|
| L0 | Static and formal | Prevent bugs before runtime | zero critical findings | commit | ruff, pyright/ty (strict), mypy; Biome v2 / oxlint, tsc/tsgo; Semgrep, CodeQL, Bandit, Gitleaks |
| L1 | Unit | Verify pure logic in isolation (no IO/net/fs/DB) | branch coverage, mutation score | commit | pytest; vitest, node:test |
| L2 | Property | Prove invariants (roundtrip, idempotency, order, bounds) | invariant-violation count | commit/PR | Hypothesis; fast-check |
| L3 | Fuzz | Crash-free on malformed/hostile structured input | crash-free rate, safe-reject rate | nightly | Atheris, Schemathesis; jazzer.js |
| L4 | Mutation | Test the tests: flip conditions, remove branches | mutation kill rate | nightly | mutmut, Cosmic Ray; Stryker |
| L5 | Component | One subsystem with real (recorded) deps, no infra | deterministic pass / replay stability | PR | pytest + recorded fixtures; Testing Library + Storybook |
| L6 | Contract | API/schema/protocol compatibility, no breaking change unversioned | zero unversioned breaking changes | PR/pre-release | Schemathesis, Pact, OpenAPI lint; Pact-JS |
| L7 | Integration | Several real components, sandboxed externals | outcome + trace correctness | PR/nightly | Testcontainers + real engine; Playwright |
| L8 | E2E / system | Full user workflow, real persistence | task success, latency | nightly/pre-release | pytest e2e; Playwright |
| L9 | Golden master / regression | Snapshot vs blessed baseline; every prod bug becomes a permanent test | no regression vs baseline | nightly/pre-release | syrupy/snapshot; Playwright toHaveScreenshot |
| L10 | Non-functional | Perf, scale, concurrency, security, chaos, resilience | p95/p99, success-under-load, resilience score | nightly/pre-release | k6, Locust; Chaos Mesh, LitmusChaos |

Replayability is mandatory wherever an external dependency exists: freeze it with recorded
cassettes (VCR.py, WireMock, PollyJS) so PR and nightly runs are deterministic. No mocks for
business logic, external services, DB, or filesystem: use recorded fixtures and real
components (Testcontainers). This is an operator hard rule, and it is the 2026 consensus.

Minimum-viable bar for any serious service: L0 + L1 + L2 + L7 (Testcontainers) + L9
(regression suite). Add L3/L4/L6 when it handles external input or is distributed. Add L10
when prod-deployed.

### 1.1 Mocking policy: mock the seam, never the subject

The no-mocks rule bans faking the subject under test, not the use of monkeypatch or a Mock
object at a legitimate seam. Three seams, three tools:
- Environment non-determinism (clock/now, uuid, random/seed, env vars, sleep, cwd): monkeypatch
  (pytest monkeypatch.setattr, auto-undo). This is control, not faking. Encouraged.
- An architectural port in a UNIT test (LLM client, tool executor, CRM client, mailer): a small
  hand-written fake, or Mock/MagicMock when you must assert the interaction (tool choice, tool
  args, was-the-write-attempted). Prefer a hand fake over MagicMock when behavior matters
  (MagicMock returns truthy magic for everything and hides bugs).
- The real external dependency in an INTEGRATION test: never hand-mock. Use Testcontainers (DB)
  or a recorded cassette (VCR.py, or httpx.MockTransport with a recorded response). Replay, not
  invention.
Forbidden: monkeypatch or Mock applied to the function under test or to business logic (for
example stubbing a scoring or verdict function, or asserting a chart against a mock fixture
instead of recorded data). That is the defect the rule targets. Hexagonal ports-and-adapters is
what makes this clean: the LLM client, vector store, and tool executors are adapters, faked at
the port in unit tests, real or recorded in integration.

Compiler-runtime note for the L3 fuzz layer: Atheris (Python) and jazzer.js (TS) are the
libFuzzer/LLVM coverage-guided fuzzers. That is the only place LLVM compiler-runtime tooling
applies to a pure Python/TS stack. Sanitizers (ASan/UBSan/TSan) and gcov/llvm-cov apply only to
native code you build and ship; native dependencies (pydantic-core, orjson, numpy, ffmpeg) are
sanitized upstream, not your concern. Coverage uses coverage.py (Python) or c8/istanbul (TS).

---

## 2. AI / agent planes (apply to llm-agent, foundry-agent, rag, mcp-server, llm-judge)

The target of evaluation is the full harness plus model plus tools plus environment state,
not a text generator. Test the agent as a decision system. Catastrophic failures appear low
in the stack (over-permissive tool, schema drift, hidden prompt injection in imported data,
unsafe autonomous write), so the AI pyramid is broader than the classic one.

### 2.1 Eval control plane (compose, do not pick one framework)
- One trace substrate (OpenTelemetry GenAI conventions + OpenInference; Langfuse / Phoenix).
- One offline golden-dataset gate (runs on every prompt, model, or retrieval change).
- One online eval surface (LLM-as-judge on 10-20% of prod traffic, score written as a span
  attribute, queryable next to latency/cost).
- One human-review/calibration surface (annotation queue; failures become offline tests).
- One adversarial surface (red-team / prompt-injection, scheduled).
Missing any one of these five = not SOTA for a high-risk agent workload.

### 2.2 What the load-bearing tests grade
- Tool choice (did it pick the right tool), tool arguments (schema-conform, correct values).
- Policy compliance (defer-to-human when required, refuse out-of-scope, no unsafe write).
- Outcome correctness in the external system (CRM/ads/warehouse final state), not just the
  text shown. Verify downstream state.
- Cross-system data lineage (where did this datum come from, what touched it, which model
  saw it), replayability, and consistency over repeated trials.

### 2.3 Consistency: pass@1 and pass^k
- pass@k = at least one of k trials succeeds. pass^k = all k trials succeed.
- High-consequence workflows (money, CRM writes, external comms) gate on pass^k, not pass@1.
  Behavior is non-deterministic: run multiple trials, report both.

### 2.4 Prompt-as-code regression
- Version prompts like code. Diff them. A prompt change is a code change in user impact and
  invisible to CI without an explicit prompt eval. Gate: did it improve the target metric AND
  not regress any other metric? You cannot debug a regression you cannot reproduce.

### 2.5 RAG evaluation (if rag-tagged)
- Retrieval is the failure point 73% of the time: test the retriever first.
- Metrics: faithfulness, answer relevance, context precision/recall (RAGAS); retrieval recall
  per request monitored in prod. Citation/grounding tracking. Freshness management.
- Tune k per route (recall past k=8 often degrades; over-fetching is an anti-pattern).
- RAGAS evaluation runs in CI.

### 2.6 Guardrails, safety, red-team (mandatory if it ingests external/untrusted data)
- Threat classes to test: over-privileged tools, prompt injection from external data (CRM
  notes, ad text, transcripts, web), memory poisoning, schema drift, replay failure, secret
  leakage, unsafe autonomous writes, tool poisoning, jailbreak, PII exfiltration.
- Tools: Promptfoo (agent red-team, MCP security), AgentDojo (attack/defense env), Inspect
  (sandboxed untrusted code), Garak. Pass: no privilege escalation, no tool-poisoning-induced
  unsafe action, no data-exfil path.
- Context-engineering failure modes to architect against: context poisoning (a hallucinated
  fact compounds across turns), distraction (history drowns the instruction), confusion
  (irrelevant retrieval degrades tool choice), clash (contradictory turns).

### 2.7 LLM-as-judge discipline
- Judges are prompts: version, test, calibrate. Calibrate against 30-50 human-labeled
  examples before trusting a judge; target 75-90% agreement with humans.
- One criterion per dimension (no bundling), explicit pass/fail per dimension, 2-3 few-shot
  excellent/poor examples, chain-of-thought before the score.
- Bias modes to mitigate: positional (prefers first option), length (longer scores higher),
  self-preference (a model prefers its own family). Mitigate with multi-family judges (this
  operator: grok primary + DeepSeek audit) and calibration drift tracking.
- Multi-judge ensemble (3-5, majority vote) for high-stakes gates (brand sign-off, version
  gating): cuts position/verbosity bias 30-40%, costs 3-5x. Reserve for critical decisions.

### 2.8 AI observability and online evals
- OTel GenAI span attributes: gen_ai.system, gen_ai.request.model, usage.input_tokens,
  usage.output_tokens, response.finish_reason. Root span at request start. Never log raw
  completion content as a span attribute (use span events, sanitized).
- Per-request metrics: TTFT, tokens/s, token counts, cost, cache hit rate, retrieval recall,
  tool-call success rate. Sampling: 100% dev/staging, 10-30% head + tail-on-error in prod.
- Alert thresholds: TTFT p95 > 2s, cost/request 30-day trend > +20%, cache hit < 60%,
  tool-call error rate > 5%, quality-judge below threshold, cost anomaly (injection/retry
  loop can spike token spend 1000x in minutes).

### 2.9 GD Coverage Metric (the coverage philosophy beyond accuracy)
- A fixed golden set's accuracy says nothing about prod traffic it never sampled. Measure how
  well the golden set semantically covers prod traffic, weighted by uncertainty decay.
- Signals: Semantic Coverage Index (traffic-weighted fraction of prod clusters the golden set
  covers), JSD/Wasserstein coverage gap (>0.5 severe mismatch; cross-agent JSD >0.3 = scores
  not poolable), confidence-decay curve (reliability falls with embedding distance from the
  golden manifold), conformal prediction band (report an interval, not a point), topological
  hole detection (persistent homology finds zero-coverage regions).
- Practical: embed golden + 30-day prod queries (pinned embedding), UMAP to <=5 dims, HDBSCAN
  cluster, compute SCI + JSD monthly, track as a time series. Min golden size ~246/cluster for
  an 80% target at +/-5%, 95% confidence. Refresh the golden set from live traffic (coverage
  is Goodhart-gameable).
- For most projects here, the actionable bar is lighter: does the golden/eval set demonstrably
  cover the real production intent distribution, and is it refreshed from prod failures.

### 2.10 HITL and agent-oversight bars
- Human-on-the-loop is the default (agent acts, human monitors and can intervene) for
  reversible/internal actions. Human-in-the-loop (blocking) only for irreversible high-stakes
  actions (payments, external email, data deletion). Blocking HITL on reversible low-stakes
  actions is an anti-pattern.
- Reversibility-first: prefer reversible actions, flag irreversible ones, provide an undo
  path, persist an audit trail of consequential actions.

---

## 3. Project-type criteria packs

Select by type-tag. Each pack lists the must-have layers (beyond the universal spine), the
SOTA-specific add-ons, and the headline thresholds.

### 3.A Backend service (azure-functions-python, fastapi-service)
- L7 integration with Testcontainers (real Postgres/MySQL/queue, never in-memory stand-in).
- L6 contract: OpenAPI 3.1 committed + linted in CI; Schemathesis property-fuzz of the API;
  Pact if it has consumers. N-1 version maintained.
- API correctness gates: keyset (cursor) pagination on large collections (offset is an
  anti-pattern), Idempotency-Key on POST/PATCH with stored result, RFC 7807 error model,
  structured input validation (Pydantic v2 strict).
- Async correctness: no synchronous blocking lib (requests/psycopg2) in an async handler;
  CPU-bound work offloaded; event loop never blocked.
- Durable execution (Temporal or equivalent) for any workflow with real side effects
  (payments, emails, API calls, DB writes) or human-approval steps. Outbox pattern for the
  dual-write problem.
- L10: load test (k6/Locust) against staging pre-release; SLO/SLI + error-budget burn alerts
  (RED for services, USE for infra); chaos in staging before prod.
- Webhook security: HMAC signature verification tested (replay, tampered body, wrong key).

### 3.B AI agent (llm-agent, foundry-agent, rag, mcp-server)
- All of section 2 (AI planes). This is the core pack.
- Unit-test each tool function in isolation; test tool-selection logic with scripted
  scenarios; E2E with Testcontainers real deps; do not mock the LLM in integration (use a
  cheap real model with a deterministic seed, or recorded cassettes).
- Structured-output enforcement (JSON schema / constrained decoding) is a gate, not optional.
- Golden-trace regression suite: replay approved traces, compare tool usage, arguments,
  outcome state, cost envelope over time.
- If mcp-server: MCP protocol tests (tools, resources, prompts, transport, capability
  negotiation) via MCP Inspector; treat each MCP server as an enterprise API (pin schema +
  protocol revision, contract-check every tool-schema change, bind tool access to identity).

### 3.C SQL / data pipeline (sql-data-pipeline)
- L7 integration with Testcontainers (postgres:18), no mocks. The four non-negotiables:
  migration idempotency (run suite twice, schema matches), ON CONFLICT/upsert under concurrent
  inserts, isolation-level behavior (SERIALIZABLE anomalies), index usage (EXPLAIN ANALYZE
  asserts no unexpected Seq Scan).
- Query-plan regression as a CI gate: EXPLAIN (ANALYZE, FORMAT JSON), assert node type =
  Index Scan / Heap Fetches: 0; track pg_stat_statements.mean_exec_time per fingerprint across
  deploys.
- Constraint-as-test: NOT NULL, UNIQUE, FOREIGN KEY (not optional), CHECK (enum + cross-column
  invariants), GENERATED columns for derived values, RLS tested with a non-superuser
  connection.
- Schema golden test: pg_dump --schema-only checked into VCS; Atlas drift detection +
  lint-before-apply (unsafe-DDL: missing CONCURRENTLY, lock risk).
- Pipeline correctness: idempotency/exactly-once (ON CONFLICT; offset+rows in one txn),
  incremental unique_key uniqueness validated before use, watermark freshness with a buffer
  window, CDC slot-lag monitoring, lineage (dbt DAG / Data Vault), reconciliation of rollups.
- Data quality frameworks: Great Expectations (pipeline-stage validation) + Soda (continuous
  monitoring); dbt tests (not-null/unique/accepted-values/relationships); pandera at every
  DataFrame boundary.
- Anti-pattern lint over SQL: no SELECT *, no non-sargable predicate, no NOT IN with nullable
  subquery, parameterized queries only (no string interpolation), no N+1.
- Migration safety: expand-contract phases independently deployable, lock_timeout=3s, bounded
  backfill batches, staging at >=10% of prod size.

### 3.D Frontend (frontend-react, frontend-next, static-site with interactive UI)
- L5 component: Testing Library + Vitest; Storybook interaction (play) tests per variant.
  shadcn/ui copy-own-the-code means you own the bug and the test.
- L9 visual regression: Playwright toHaveScreenshot or Chromatic, gated on PR. Mandatory for
  glassmorphism/3D/animation work (renders differ per browser/GPU). 3D/WebGL: tolerance
  threshold + fixed camera/seed, or assert canvas mounts + disposes (no GPU leak).
- Accessibility (hard gate): axe-core via jest-axe/vitest-axe (component) and
  @axe-core/playwright (page); Pa11y-CI; Lighthouse a11y >= 95. WCAG 2.2 AA floor (4.5:1
  normal / 3:1 large), APCA (WCAG 3.0) forward. Keyboard operability, focus management,
  ARIA roles on state-machine primitives, screen-reader semantics.
- prefers-reduced-motion is a hard gate for any animation (Aceternity UI / Magic UI do not
  ship it, so the test is mandatory there). Test prefers-color-scheme and forced-colors.
- Performance budgets: LCP < 2.5s (fail > 4.0), INP < 200ms (fail > 500), CLS < 0.1 (fail >
  0.25). Lighthouse CI category budgets. Bundle-size budgets (size-limit/bundlesize); lazy-load
  the 3D chunk; cap Lottie JSON payloads.
- Cross-browser matrix: Chromium + Firefox + WebKit (backdrop-filter, View Transitions,
  Scroll-Driven Animations, WebGPU differ per engine). Responsive snapshots per breakpoint.
- E2E (Playwright): core user flows; for generative UI, test the streamed-component path and
  graceful degradation on partial/malformed LLM output (use recorded provider fixtures, not a
  live LLM).
- Design-token correctness: W3C DTCG source, Style Dictionary transform, snapshot/diff
  generated outputs; lint against raw hex/px when a token exists; contrast valid in light and
  dark.

### 3.E Voice (voice-tts-stt, telephony with audio)
- Five-layer voice stack: (1) objective audio signal, (2) simulation at scale, (3) production
  observability, (4) regression/CI, (5) governance/compliance.
- L1 signal metrics (no LLM): PESQ (wb), ViSQOL v3, UTMOSv2 (no-reference MOS), NISQA, STOI,
  MCD. For TTS naturalness use UTMOS; for device/tone use ViSQOL-Audio 48kHz + FFT.
- AI-as-judge (gpt-audio-1.5): naturalness, tone-match, pacing, emotion-appropriateness,
  non-verbal cues (laugh/sigh/cough). Sandwich prompt (instructions, audio, format). Rubric
  75-90% human agreement. Multi-judge ensemble for brand-voice/version gating.
- Dimensions: WER on clean audio; WER on proper nouns/numbers/domain terms (the brand-mispron
  failure lives here); noise robustness (WER at 45dB/70dB SNR); accent/dialect WER; speaker
  similarity (ECAPA-TDNN cosine) for cloning; TTS TTFB P50/P95/P99 (not averages).
- Conversation: task-completion rate, multi-turn context retention (5+ turns), barge-in/
  interruption recovery, CSAT/escalation rate.
- Tiered golden set 100-500 scenarios: 60% happy / 25% edge (rare accents, long silence,
  jargon, interruptions) / 15% adversarial (known failures, hostile phrasing). Studio audio
  does not predict prod: include real phone audio or noise+accent-augmented synthetic.
- CI gates: WER regression > 5% blocks, UTMOS drop > 0.2 blocks, P99 over threshold blocks,
  judge-score drop > 10% triggers human review. Feed every failure back into the golden set.
- Platform tooling: Hamming / Coval (sim + monitor), Roark (replay real failed calls), Cekura
  (PII-leak alerts), DeepEval/Promptfoo (OSS CI), Langfuse (trace-level judge).

### 3.F Video / multimodal media (video-generation)
- Three modalities must agree at every second (pixels, narration, on-screen text). The
  highest-value failures live in the seams between modalities. Use a fused output-aware
  scorecard that re-analyzes the rendered mp4, not the source.
- Visual signal (no LLM): reference metrics VMAF (libvmaf; per-rendition vmaf_avg>=85,
  vmaf_min>=65 at 720p), SSIM/MS-SSIM, PSNR, LPIPS; golden-master per-frame snapshot diff
  (the cheapest deterministic regression for a deterministic render); no-reference blur
  (variance-of-Laplacian, BRISQUE/NIQE via pyiqa), banding, palette delta-E brand fidelity;
  frame-diff/scene-cut and optical-flow motion QA.
- Audio sub-stack: EBU R128 loudness window, F0 monotone floor, per-segment energy drift, and
  non-speech disfluency detection (cough/breath/throat-clear) via PANNs CNN14 decision-level
  or a gpt-audio-1.5 non-speech judge (AudioSet classes). Enable provider audio-event tags.
- Brand pronunciation: phoneme-aware, not fuzzy string. g2p reference (g2p_en/espeak-ng),
  forced alignment (MFA/WhisperX), PanPhon feature-weighted distance + syllable-nucleus count.
- Cross-modal semantic: decompose each VO claim into a subject, classify frame screen-identity
  (ScreenSpot-class), judge agreement (FaithSCAN Visual-NLI pattern). Owns the wrong-screen
  defect a viewer notices instantly and a single-modality gate never sees.
- Self-evaluate-to-self-fix loop: failed gate name maps to a generator repair action
  (re-synthesize, splice, re-pin, swap asset, re-normalize), re-render, cap retries, require
  the failed-gate set to shrink each iteration, else escalate to human.
- Tiered golden set mirrors voice: 60% happy / 25% edge (RTL mirror, long single-take) / 15%
  adversarial (every reviewer-found defect frozen as a must-FAIL fixture). A fixture that
  starts passing means the gate regressed.

### 3.G Low-stakes CLI / dev-tooling (python-cli with no external service, no PII, no deploy)
- L0 (ruff + type check) + L1 unit + L2 property on the core logic. A small regression suite.
  Smoke test of the entrypoint. That is sufficient; do not over-test. Add more only if it
  grows a service surface, external deps, or handles sensitive data.

---

## 4. Cross-cutting overlays (apply by risk surface, not by type)

### 4.1 Security (any network-exposed or untrusted-input surface)
- Static: Semgrep + CodeQL (SAST), Bandit (Python), Gitleaks (secrets), dependency scan. Zero
  critical findings, zero leaked secrets, in CI.
- OAuth 2.1 (if it does auth): PKCE for all clients, no implicit/password grant, exact-match
  redirect URIs, bearer tokens in Authorization header only (never query string), refresh
  rotation or DPoP/mTLS. Audit gate: grep for grant_type=password, response_type=token.
- JWT: short expiry (15 min access), RS256/ES256 (never HS256 distributed), never in
  localStorage, verify iss/aud/exp on every request.
- Supply chain: SBOM (CycloneDX/SPDX) in CI; SLSA L2 (signed provenance: GitHub Actions +
  Sigstore); secrets in Key Vault, never in env/config/images; rotate <= 30 days.
- Multi-tenant: PostgreSQL RLS at the DB layer (defense-in-depth vs app-authz bugs).

### 4.2 PII / data protection (any project handling names, phones, emails, IDs, transcripts, CRM)
- Mask PII at the model boundary by reversible tokenization (stable vaulted token, map outside
  any model call), never raw PII into an LLM/MCP payload. Test the tokenizer (property test:
  detect-and-mask invariants) and the rehydration path (agent identity stays pseudonymized).
- Never mutate/strip PII from production sources (read-only). Redaction unit + property tests
  for required-redaction invariants on call/transcript data.
- PII-leakage eval: assert no PII in model-facing context and no PII in outward deliverables
  (scan staged diffs).

### 4.3 Money / CRM-write surface (spends, budget changes, lead status, ticket creation)
- Outcome-in-external-system tests (verify the CRM/ads final state, not the agent text).
- Idempotent writes (no duplicate spend events, idempotent upserts), human-approval gate before
  consequential writes, immutable audit trail, pass^k consistency bar on the write path.
- Read/write scope separation; agent identity required for every write.

### 4.4 Prod-deployed (any project with a live pipeline/endpoint)
- "Production" means merged-to-deploy-branch + deployed + live-smoked (real URL, real output),
  not "tests green on a feature branch". Verify against freshly-fetched refs.
- Online evals + drift + cost-anomaly monitoring (section 2.8). Rollback path documented.
- Preview environment per PR where feasible (highest-ROI CI/CD investment for AI apps).

---

## 5. CI cadence matrix

| Trigger | What runs | Blocks on |
|---|---|---|
| On commit | L0 static (lint, type, secret scan), L1 unit, L2 property | any hard static finding, any failing unit/property |
| On PR | L5 component, L6 contract, L7 integration (Testcontainers), offline AI golden-set eval, a11y + visual regression (frontend) | contract break unversioned, integration fail, eval below baseline, a11y violation |
| Nightly | L3 fuzz, L4 mutation, L8 E2E, L10 perf/concurrency, full AI eval (expanded), red-team/prompt-injection | mutation kill below floor, perf p95/p99 regression, red-team escalation |
| Pre-release | L9 full regression, E2E, load, chaos, pass^k on high-consequence scenarios, cross-modal/judge ensemble (media/voice) | any regression vs baseline, pass^k below bar, judge-score drop > 10% |
| Production (continuous) | online evals, drift, cost anomaly, SLO burn-rate alerts | actionable alert within minutes |

---

## 6. Scoring and maturity

For each applicable criterion: have (gated and working) = 1.0, partial (exists but advisory,
unwired, mock-bound, or generation-side only) = 0.5, gap (absent from the gate path) = 0,
n/a (does not apply) = excluded.

- Layer coverage score = sum(scores) / count(applicable). Report per layer and overall.
- Weight the AI planes, security, and PII overlays 2x for projects whose notable risk includes
  money/CRM/PII/prod, because that is where business-catastrophic failures live.

Maturity ladder (report one level per project):
- L1 ad hoc: unit tests only, no CI gate, no eval.
- L2 managed: CI runs lint + unit + some integration; an eval harness exists but is not gated.
- L3 defined: PR gates on integration + contract + offline eval; regression suite exists;
  a11y/visual for frontend; security static gates.
- L4 measured: online evals + observability in prod, mutation/property at depth, pass^k on
  write paths, golden-set refreshed from prod failures, SLO burn alerts.
- L5 optimizing: self-fix loops, coverage-metric (SCI/JSD) monitoring, multi-judge ensembles,
  chaos in prod drills, error-budget-gated releases.

---

## 7. Per-project output template

Each project gets a file `TESTING-SOTA-2026-GAPS.md` at its root. Structure:

```
# Testing SOTA 2026: gap analysis and open items

> Generated <date> against ~/docs/SOTA-TESTING-CRITERIA-2026.md.
> Status legend: have / partial / gap / n-a. Evidence is file:symbol.

## 1. Project profile
- type-tags, stack, risk surface (money/CRM/PII/telephony/prod/media), current maturity level.

## 2. Current test state (verified, not assumed)
- What exists: test dirs, frameworks, eval harness, CI, existing test docs. Cite paths.

## 3. Gap analysis (applicable criteria only)
- A table per applicable section/pack: criterion | status | evidence (file:symbol) | note.
- Mark n-a explicitly for non-applicable criteria so the reader knows it was considered.

## 4. Coverage score and maturity
- Per-layer score, overall score, maturity level, and the single highest-leverage gap.

## 5. Open items (prioritized, agent-pickup-ready)
- Each item: [PRIORITY P0/P1/P2] title
  - why it matters (the risk it addresses)
  - acceptance criteria (what "done" looks like, testable)
  - suggested tool(s) and the file/path it would live in
  - rough size (S/M/L)
- Order by risk-reduction per effort. P0 = blocks a real failure mode on a prod/money/PII path.
```

Open items must be concrete enough that a coding agent can pick one up and implement it
without re-deriving the analysis. Name the tool, the file, the threshold, the fixture.

---

## Appendix: merged tool inventory (testing / eval / quality / observability)

Static/quality: ruff, pyright, ty, mypy, Biome v2, oxlint, tsgo, Semgrep, CodeQL, Bandit,
Gitleaks, import-linter, ArchUnit, Pydantic v2, pandera.
Unit/property/fuzz/mutation: pytest, vitest, node:test, Hypothesis, fast-check, Atheris,
Schemathesis, jazzer.js, mutmut, Cosmic Ray, Stryker.
Integration/contract/replay: Testcontainers, Pact, OpenAPI lint, MCP Inspector, VCR.py,
WireMock, PollyJS, syrupy.
E2E/visual/a11y/perf (frontend): Playwright, Cypress, Testing Library, Storybook, Chromatic,
Percy, Loki, axe-core, jest-axe, vitest-axe, Pa11y, Lighthouse CI, size-limit, bundlesize,
Style Dictionary.
AI eval/observability: Langfuse, Braintrust, Arize Phoenix, RAGAS, OpenAI Evals, Promptfoo,
AgentDojo, Inspect, DeepEval, OpenLLMetry, OpenInference, OpenTelemetry GenAI, Helicone,
Datadog LLM Obs.
Voice: PESQ, ViSQOL v3, UTMOSv2, NISQA, STOI, MCD, gpt-audio-1.5, Hamming, Coval, Roark,
Cekura, Sipfront, ECAPA-TDNN.
Video: libvmaf (ffmpeg), torchmetrics (SSIM/LPIPS), pyiqa, PySceneDetect, PANNs CNN14, YAMNet,
AST, BEATs, g2p_en, espeak-ng, MFA, WhisperX, PanPhon.
SQL/data: Testcontainers (postgres:18), EXPLAIN ANALYZE in CI, Atlas, dbt tests, Great
Expectations, Soda, Debezium, pg_stat_statements, auto_explain, hypopg.
Non-functional: k6, Locust, Chaos Mesh, LitmusChaos.
Reliability/SLO: Prometheus, Grafana, OpenSLO, burn-rate alerts (RED/USE).
Coverage-metric (GDCM): UMAP, HDBSCAN, JSD, Wasserstein-1, Gaussian Process/Matern, conformal
prediction, semantic entropy / SEPs / SGD, persistent homology.
