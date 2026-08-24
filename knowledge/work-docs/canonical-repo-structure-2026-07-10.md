# Canonical Repo Structure + Standard - 2026-07-10

The single reference for the general root directory structure every repo follows, the six
compliance dimensions, the LangGraph/agentic mapping, and the elite deltas beyond the
floor. Consolidates the Google-grade + OpenSSF + platform research (2026-07-09/10) and the
empirical GitHub fetches (jax, ruff, uv, pydantic, fastapi). Scored by
`intent_control_plane.standards`. Per-repo docs follow `~/.claude/rules/docs-control-plane.md`.

The LangGraph and Mojuco sim2real websearches are folded in (2026-07-10, sections 3 and 6),
both grounded in fetched official docs and real repos.

## 1. Repo classes (pick by what the repo IS)

- **product-service** - a deployable (Azure Function, web API, SPA backend). Most of the estate.
- **harness/tooling** - the control plane and dev tooling (intent-control-plane). Tested
  package + thin bash adapters. See `harness-structure-standard-2026-07-09.md`.
- **agentic-langgraph** - a genuine multi-agent LLM app (only when it declares
  langgraph/langchain). None in the estate today; the layout is reserved, not skipped.

## 2. Canonical root directory structure

### product-service (the default)

```
<service>/
├── src/<package>/            # importable core (or Azure Function folders w/ function_app.py)
│   ├── contracts/            # typed request/response/error DTOs (boundary-contracts rule)
│   ├── routes/ or handlers/  # thin entrypoints; one bounded surface per module
│   ├── services/             # application logic
│   ├── shared/               # clients, db, cross-cutting
│   └── http.py               # typed problem+json error helpers
├── tests/  { unit/  integration/  e2e/ }   # no-mocks; recorded fixtures
├── docs/
│   ├── prd/                  # living PRD spine (docs-control-plane)
│   ├── specs/                # dated impl specs w/ PRD:/Ticket:/Status: header
│   ├── adr/                  # one ADR per costly-to-reverse decision
│   ├── analysis/             # point-in-time scans (never at root)
│   ├── API_CONTRACT.md  RUNBOOK.md  REPO-MAP.md  INDEX.md
├── docs_src/                 # (elite) doc examples that are CI-tested files, not prose
├── schemas/ or api-specs/    # OpenAPI / generated contract artifacts
├── infra/                    # Bicep modules + per-env .bicepparam (dev/stage/prod)
├── scripts/  evals/          # evals/ only for AI/eval repos
├── azure-pipelines.yml       # path-triggered; gates + Codex review + comment-resolution
├── pyproject.toml  uv.lock   # uv + ruff + mypy + pytest, all configured
├── TODO.md  README.md  CHANGELOG.md  SECURITY.md  .gitignore
```

Rules: one `.git` (no repo-in-repo), runtime state and generated artifacts never tracked,
one TODO + one INDEX, root stays clean.

### harness/tooling

Tested package (`src/<pkg>/` with router/state/self_improve/repo_health/commands/util),
thin `hooks/` adapters, `skills/ rules/` prompt layer, `corpus/`, `tui/`, runtime state
outside the tree. Full spec: `harness-structure-standard-2026-07-09.md`.

## 3. LangGraph / agentic mapping (if the repo IS agentic) - verified 2026-07-10

The real canonical LangGraph layout (official docs + the `new-langgraph-project` starter) is
LEANER than a generic agentic tree; do not over-build it:

```
my-app/
├── src/agent/
│   ├── graph.py     # StateGraph construction + .compile(checkpointer=...)
│   ├── state.py     # state schema (TypedDict / dataclass)
│   ├── nodes.py     # node functions
│   └── tools.py     # tool defs
├── tests/  static/
├── langgraph.json   # graphs + deps + env; each graph = one servable assistant
└── pyproject.toml
```

- Memory/checkpointer is NOT a folder: pass it into `.compile(checkpointer=...)` (InMemory
  locally, Postgres on Platform). Add `prompts/ chains/ graphs/` under `src/` only once there
  are multiple graphs (community pattern, not official).
- `langgraph.json`: `{"dependencies": ["."], "graphs": {"agent": "./src/agent/graph.py:graph"},
  "env": ".env", "image_distro": "wolfi"}`. The LangGraph CLI/Platform reads it to build the
  deploy image; each graph is servable and inspectable in LangGraph Studio.
- Multi-agent: supervisor + workers as `create_react_agent` graphs added as nodes, OR the now
  PREFERRED agents-as-tools via `create_handoff_tool` (the prebuilt `langgraph-supervisor`
  package is legacy; use the supervisor pattern directly through tools).

Decision rule (official, langchain.com/blog/how-to-think-about-agent-frameworks): adopt
LangGraph ONLY if you need its infra: short/long-term memory, human-in-the-loop, streaming,
fault tolerance, durable/resumable state, loops/retries/branching on intermediate results, or
coordinated specialist agents. A straight-line prompt -> tool -> format flow is a plain tool
loop, NOT LangGraph. Cited overkill case: a 12-node LangGraph + Redis, 6 weeks, replaceable by
~180 lines of direct FastAPI. "If langgraph is the way, so be it" means adopt it where the app
is truly a graph, never by default.

## 4. The six compliance dimensions (scored)

1-5 as built: repo_org, code_health, docs, testing, cicd (see `repo-standards-2026-07-09.md`).

**6. supply-chain / security (NEW, Azure-translated).** The Google-grade/OpenSSF research
showed our scorer was missing this whole dimension. Translated to our private Azure DevOps
services (not public GitHub OSS):

- **Floor (OpenSSF Scorecard, do first):** hash-pinned deps (`uv.lock`), least-privilege
  service connection, SAST in CI (bandit + semgrep, as cs-agent already does), branch
  protection + required checks, secret scan (detect-secrets vs baseline, as cs-agent does).
- **Elite delta (empirical, ranked):** (a) CI-as-product - fuzz/benchmark/test-against-real
  where feasible, not just unit tests; (b) verifiable releases - the Azure analog of
  Sigstore provenance / immutable artifacts; (c) docs-as-tested-code (`docs_src`); (d) the
  CI config itself security-linted (the Azure Pipelines analog of `zizmor`/`actionlint`).
- **Skip (OSS-only or multi-human):** PyPI Trusted Publishing, OSS-Fuzz, CODEOWNERS,
  community bots. Elite repos routinely lack CODEOWNERS/SECURITY.md, so do not over-score
  ceremony.

## 5. Elite deltas beyond the floor (what separates elite from merely-good)

Ranked for solo leverage (from fetched jax/ruff/uv/pydantic/fastapi):
1. **CI as a shipped product** (fuzz daily, benchmark every PR, test against downstream).
2. **Supply-chain-verifiable releases** (Trusted Publishing + Sigstore + immutable releases).
3. **Docs as tested code** (fastapi `docs_src/` fails CI on example drift).
4. **CI config is itself security-linted** (`zizmor` + `actionlint` on the workflows).

## 6. Mojuco sim2real: simulate more (deterministic-first pyramid)

Grounded in 2026 research (cited), ranked by solo-adoptability. The principle: a simulation
runs before any real cost, and its pass-rate is a SCREEN, not ground truth (the sim2real gap
is real, so calibrate against real outcomes).

1. **Deterministic-first eval pyramid (adopt now, zero infra).** Three tiers, each runs only
   on what the cheaper tier could not resolve: (1) schema/regex/JSON-shape/function-call-shape
   checks (sub-ms, free, catches 30-60% of failures), (2) a small classifier (toxicity/PII/
   injection), (3) an LLM judge on the residual only. Insert tiers 1-2 BEFORE the grok/DeepSeek
   Foundry judges in the existing 4-phase eval pipeline. Source: futureagi.com deterministic-
   metrics + eval-vs-testing writeups.
2. **Simulate the Codex reviewer.** Cheap deterministic pre-check (lint/type/test on the diff)
   plus a Haiku sim-reviewer; escalate to the real Codex/Foundry reviewer only on flagged risk.
   Directly cuts the 262 calls and their 30% failure/rate-limit waste.
3. **tau-bench simulated user for the CS agent (Yasha/AxiaCS).** An LLM plays a persona with a
   goal + policy doc; the agent runs tool APIs against a mock DB; score the end-state, not the
   text. github.com/sierra-research/tau-bench (and tau2-bench). CAVEAT, "Lost in Simulation"
   (arXiv 2601.17087): up to 9pp pass-rate swing across simulator models, worse calibration on
   hard tasks, and dialect-linked fairness gaps (AAVE vs SAE). Treat the number as a screen.
4. **Deterministic replay of recorded traces.** We already log every a2a call and intent event
   as JSON; replay them verbatim against a candidate model/prompt and diff the divergence.
   Virtualize the clock if prompts embed timestamps. Source: tianpan.co replay-debugging.
5. **Shadow -> canary -> percentage -> full gate.** Fork prod requests to the candidate with no
   user exposure, then route 1-5% with rollback. Adopt only after 1-4 exist.

Tooling: `mini-swe-agent` (MIT, ~100-line agent + sandboxed shell, 74% SWE-bench) for a
coding-agent sandbox. Watch-don't-adopt: world-model simulators (Qwen-AgentWorld, needs GPU
clusters). Full local spec: `specs/2026-06-28-work-general-mojuco-artifixer-foundry-plan.md`.

## 7. Sources

Google-grade + OpenSSF research (2026-07-09), empirical GitHub fetches (jax-ml/jax,
astral-sh/ruff, astral-sh/uv, pydantic, fastapi), the July-2026 SOTA cluster (AI-native repo
structure, code-maturity-ladder, architecture-patterns, data-persistence), cs-agent pipeline
reference. LangGraph + Mojuco sim2real websearches pending (2026-07-10).
