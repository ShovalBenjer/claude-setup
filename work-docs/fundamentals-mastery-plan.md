# Fundamentals Mastery Plan — "SOTA counter, don't rely"

Goal: independent mastery of core fundamentals so I evaluate/critique the AI rather than depend on it.
Companion to `ai-103-study-tracker.md`. Principle: use the AI to *accelerate* the generation effort, never to skip it.

## The discipline (apply to all work, not just study)
1. **Predict-then-peek** — write my expected answer/approach BEFORE asking; the gap is the lesson.
2. **Build-first, diff-second** — on a fundamental, never start from AI code; build, then diff.
3. **Review the AI like a PR** — find the bug, demand the citation, verify independently.
4. **Feynman** — explain it with no notes; let the AI grade and find the hole.
5. **Spaced retrieval** — re-derive from memory days later.
6. **Never accept "trust me"** — make the AI show sources; check them.

## The 4 pillars (grounded in real projects)

### 1. API types
Fundamental: choose the right contract + handle its failure modes.
Scope: REST vs gRPC vs GraphQL vs WebSocket vs webhook/event-driven vs **MCP**; idempotency; pagination; rate limits & backpressure; auth (API key / OAuth2-OIDC / managed identity); versioning; OpenAPI/AsyncAPI contracts.
Live case studies: Yasha CRM REST, Jira REST, MS Graph, PandaTS webhooks, MCP servers, the session rate-cap.
Counter-practice: sketch the contract (endpoints/auth/pagination/idempotency/error model) before any integration; predict rate-limit behavior before testing.

### 2. Production data
Fundamental: data is a contract with a blast radius — validate at the boundary, preserve lineage, never leak.
Scope: schema contracts (pandera/pydantic); validation-at-boundary; idempotent/replayable pipelines; batch vs stream; partitioning; schema evolution / SCD2; **data leakage**; PII/DLP/masking; freshness SLAs + drift; medallion/lakehouse; parquet/Delta.
Live case studies: CJA `scores_v2` leakage, PII in `agents.csv`, 146-xlsx churn, provenance for bosses, the DuckDB/Polars catalog idea.
Counter-practice: for every data bug, ask "what test/contract would have caught this?"; design the catalog schema yourself, then have the AI review.

### 3. Types / typing
Fundamental: make illegal states unrepresentable — types are the cheapest tests.
Scope: static (mypy/pyright) vs runtime (pydantic/pandera/msgspec); type-driven / parse-don't-validate; Decimal-not-float for money; tz-aware datetimes; enum/categorical over str; NULL semantics.
Live case studies: instructor/pydantic structured outputs, Polars/DuckDB schemas, eval-row schemas.
Counter-practice: write the signature + domain model before the impl; predict what the type checker will catch.

### 4. SOTA tests
Fundamental: each layer catches a different failure; an unwritten test is a shipped bug.
Scope: the 8-layer pyramid (static → unit → property → component → contract → integration → e2e → non-functional) + agent trajectory/adversarial; property-based (hypothesis); contract (schemathesis); mutation testing; fixtures-not-mocks; eval-as-CI-gate; TDD RED→GREEN.
Live case studies: `testing-pyramid` skill, the eval pipeline, today's adversarial-verifier agents.
Counter-practice: write the failing test first; for anything the AI generates, write the test that breaks it; mutation-test the AI's code.

## Weekly rhythm (alongside the AI-103 hour)
- Mon/Wed/Fri: AI-103 module + lab.
- Tue/Thu: one pillar (rotate weekly), using a real project artifact as the case study.
- Every AI session: run habits #1 (predict-then-peek) + #3 (review-like-a-PR).
- Sat: retrieval — re-derive the week's hardest concept with no notes; `/grill-me` to check.

## Retrieval log (re-derive these from memory)
- 
