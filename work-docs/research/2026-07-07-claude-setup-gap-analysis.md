# Claude Code Operating Setup: Gap Analysis (what to implement / wire / fix / add)

Date: 2026-07-07. Method: 6 parallel subagents (3 mined ~/docs SOTA files and cross-referenced
the live setup; 3 did cited web research on trending 2026 OSS). VERIFIED = a file or primary source
was read. CLAIMED = prior knowledge or a search snippet, not independently fetched.

## The one root finding

Across testing, eval, observability, memory, and architecture, the pattern is identical: the SOTA
is **named in `CLAUDE.md` or a skill's prose, and nothing executes it.** The only automated gates that
actually run are `coverage-enforcer.sh` (a filename heuristic on `git push`, never runs a test) and the
`commit-push-pr` skill (`uv run ruff/mypy/pytest`, per-project, not global). Of the 13 test layers in
your own `SOTA-TESTING-CRITERIA-2026.md`, **12 have zero executing enforcement**. Your Python Library
Defaults block (`CLAUDE.md:269-288`, pandera/structlog/orjson/msgspec/instructor/deltalake/optuna) binds
nothing: none is a dependency in any `pyproject.toml`. The fix is never "add more prose." It is "wire the
prose to a hook."

Second root finding (memory): your `intent-control-plane` captures prompt->intent write-only and never
reads back at session start. That is exactly the anti-pattern Anthropic's own context-engineering guidance
warns against: structured note-taking only pays off when the notes are re-injected after a reset. [ctx]

## Part A: your own research, mined for named tools you never wired

Condensed to the high-impact rows (full per-agent tables in the appendix section below). Wired: Y=executes,
P=prose only, N=absent.

| Thing | Your doc | Wired | Where it plugs in |
|---|---|---|---|
| LLM-as-judge online sampling + Langfuse/Phoenix | Production-AI-SOTA | N | eval layer; the biggest observability hole (CS-agent ships prompt regressions invisibly) |
| Hybrid retrieval (BM25+dense+RRF) + cross-encoder rerank | Production-AI-SOTA | N | CS-agent KB retrieval; documented 15-48% quality lift, KB is at 64% eval pass |
| OTel GenAI conventions + azure-monitor-opentelemetry | Production-AI-SOTA | P | `CLAUDE.md:284` mandates `configure_azure_monitor()`; nothing runs it. No per-call cost/latency trace |
| pandera at every data boundary | CLAUDE.md:275 | P/N | a data-boundary validator; mandated, never installed |
| structlog / orjson / msgspec / instructor | CLAUDE.md:269-282 | P | Functions logging + hot-path + LLM extraction; prose, zero deps |
| Hypothesis property tests | Prod-AI + testing docs | P | dev-dep + `coverage-enforcer.sh`; the intent-plane PII/redaction invariants need generated inputs |
| Promptfoo + PyRIT (red-team) | deep-research-report(3) | P | called "mandatory" for your CRM+ads+PII MCP threat model; `red-team` skill spawns Claude agents instead of running them |
| Testcontainers (integration) | SQL + DR2 + DR3 | P/N | named 3x; no runnable integration gate |
| mutmut / Stryker (mutation) | testing docs | P | `mutation-runner` prints commands; no hook invokes it |
| sqlglot | Text2SQL, SQL | N | the load-bearing dep of your own SQLTok proposal; absent |
| Atlas (atlasgo) migrations | SQL | N | doc's #1 migration pick; Widgora owns schema with no migration tooling |
| react-bits / Aceternity / Magic UI | Next-Gen UI/UX | N | the report's headline UI differentiators; 0 refs in `ui-ux-pro-max` |
| ADRs in Git + import-linter fitness functions | Principal-Eng-Curriculum | N | `docs/decisions/ADR-*`; no ADR skill; no CI boundary check |
| Keyset pagination + UUIDv7 | Prod-AI + Curriculum | N | already bit you: agent-call-tracker ~23s cold-start was a bare `MAX(id)` over an unindexed view |
| SBOM (CycloneDX) + SLSA signing | Production-AI-SOTA | N | one CI step per pipeline; eVest-merger raises the compliance stakes |
| Feature flags (OpenFeature) | Prod-AI + Curriculum | N | prompt/model kill-switch; the missing safety valve for overnight autonomous /loop |

VERIFIED: all wired-status rows were checked against `~/.claude/CLAUDE.md`, `~/.claude/skills/*/SKILL.md`,
`~/.claude/hooks/`, `~/.claude/settings.json`, and `~/pyproject.toml`. Only DuckDB, Polars, Hypothesis,
uv, Ruff, pytest, Pydantic, shadcn/Tailwind/Three.js (via `ui-ux-pro-max` data) reach an executable path.

## Part B: external 2026 SOTA you lack or reinvent worse

VERIFIED repos (fetched 2026-07-07):

- Spec-driven dev: **GitHub Spec-Kit** (github.com/github/spec-kit, 119k stars) and **OpenSpec**
  (github.com/Fission-AI/OpenSpec, 59k) implement a propose->apply->archive spec state machine with
  diffable delta specs. **BMAD-METHOD** (50k) is spec + persona orchestration in one. Your "PRD as prose
  control plane" + gastown registry has no spec-version diff or drift gate. [spec1][spec2][spec3]
- Orchestration: **Dynamic Workflows / ultracode** is the official Anthropic primitive (now on in your
  settings). **Bernstein** (github.com/sipyourdrink-ltd/bernstein) is the reference for deterministic,
  zero-LLM-token, replayable orchestration with an HMAC-chained audit log and a Janitor verify-before-merge.
  Your homegrown "hive" routes turn-by-turn via the model: non-deterministic, no tamper-evident replay. [orch]
- Eval: **OpenAI Evals is being shut down 2026-11-30 and OpenAI itself points users to promptfoo.** The
  2026 trio is **promptfoo** (CI + 500+ red-team vectors), **DeepEval** (pytest-native regression, G-Eval +
  deterministic DAG judges), **Inspect AI** (UK AISI; drives Claude Code / Codex as the eval SUT via
  `inspect_swe`). Your Foundry-only eval-runner (grok/DeepSeek judges) has no red-team suite, no agent-
  trajectory harness, and no block-on-regression CI contract. [eval1][eval2][eval3]
- Verifiers: 2026 consensus flipped to "verification is the harder problem." Ground verifiers in executed
  tests, not source inspection: TDD-style rewards cut reward-hacked SWE-bench resolutions from 28.6% to
  0.56%. Static LLM-judge critics get length-exploited. [ver]
- Memory: **Mem0** (60k), **Graphiti/Zep** (28k, bi-temporal graph, ships an MCP server), **Letta** (24k),
  **Cognee** (27k, graph+vector on a single Postgres, ships MCP server). You already run
  `aiprojects-company-postsql` (PG18), so Cognee-on-Postgres or Graphiti-MCP is a low-friction upgrade over
  the hand-rolled bag-of-words `term_vector`/cosine in intent-control-plane's SQLite. [mem]
- Context engineering: Anthropic's 4 canonical primitives are compaction, structured note-taking,
  tool-result clearing, just-in-time retrieval. You implement the write half of note-taking and skip the
  read-back. [ctx]
- MCP: the **official MCP Registry** (Linux Foundation), **Docker MCP Gateway** (container isolation +
  secrets, MIT), **IBM ContextForge** (REST/gRPC->MCP translation, Apache-2.0) are the wiring surfaces for
  your centralized-marketing-MCP plan. [mcp]

GOTCHA (VERIFIED): Claude Code's native cross-session Session Memory is first-party Anthropic-API only and
does NOT run on Bedrock/Vertex/Foundry. Your brn-azai runtime cannot rely on it, so your own memory layer
is the correct call: it just needs the read-back. [mem]

## Prioritized backlog (implement / wire / fix / add)

Effort S/M/L. "Replaces" = supersedes something bespoke you half-built.

TIER 0 (do first; unlocks four complaints at once)
- [WIRE] SessionStart recall hook: query `intent list intents/events` (+ embedding rank later), inject a
  <=400-token digest (last task, open goal, proof_required) + candidate skills from gastown registry.
  Effort M. New `~/.claude/hooks/session-recall.sh` + settings SessionStart. Replaces: the dark read-path of
  intent-control-plane. Closes continuity + skill-loading + goal + spec at once. [ctx][mem]

TIER 1 (wire what you already researched; cheap, high value)
- [FIX] UserPromptSubmit skill-router: map prompt -> candidate skills (gastown registry) and inject.
  Effort M. New hook. Replaces gastown-as-prose. Makes skill activation deterministic, not discretionary.
- [WIRE] Real eval gate: promptfoo (red-team + judge) + DeepEval (pytest regression) invoked from a Stop or
  pre-`git push` hook; block on regression-vs-baseline (guard `stop_hook_active`). Effort M. Extends
  `coverage-enforcer.sh` from filename-check to real gate. Complements the Foundry eval-runner. [eval1][eval2]
- [WIRE] Hypothesis as a dev-dep + into the coverage gate, starting with intent-plane redaction/PII and
  ledger invariants. Effort S. `pyproject.toml` + `coverage-enforcer.sh`.
- [WIRE] The CLAUDE.md Python defaults that bind nothing: pandera (data boundary), structlog +
  azure-monitor-opentelemetry (Functions logging/trace), orjson/msgspec (hot paths), instructor (LLM
  extraction). Effort S each, in the Functions repos, not globally.
- [FIX] ponytail-audit + spec/PRD + goal reminders in `stop-checklist.sh` + the router (the parked
  setup work). Effort S.

TIER 2 (adopt external SOTA; stop reinventing)
- [ADD] Inspect AI to drive Claude Code / Codex as the eval SUT (agent-trajectory eval your Foundry judge
  cannot do). Effort M. [eval3]
- [ADD] A spec harness (OpenSpec or Spec-Kit): propose->apply->archive with diffable delta specs. Effort M.
  Replaces PRD-as-prose control plane. [spec1][spec2]
- [ADD] Agent memory: Cognee-on-Postgres or Graphiti-MCP for relational recall. Effort M/L. Replaces the
  hand-rolled SQLite term_vector in intent-control-plane. [mem]
- [ADD] CS-agent KB retrieval upgrade: hybrid BM25+dense+RRF + cross-encoder rerank. Effort M/L. Biggest
  lever on the 64% eval pass rate. [Prod-AI]
- [ADD] Docker MCP Gateway for the centralized-marketing-MCP plan (container isolation + secrets). Effort M. [mcp]

TIER 3 (cheap CI / DB hardening)
- [ADD] SBOM (CycloneDX) + SLSA signing steps in Azure DevOps pipelines. Effort S.
- [ADD] Keyset pagination + UUIDv7 as review defaults (the cold-start class). Effort S.
- [ADD] Feature flags (OpenFeature) for prompt/model kill-switch (overnight /loop safety). Effort M.
- [FIX] ADRs in Git + import-linter fitness function in CI. Effort S.

Plus the parked DevOps hygiene: prune 36 merged remote branches, retire qc-telephony-api's diverged
`master` trunk, standardize pipelines to the agent-call-tracker reference, fix the red SMA pipeline
(missing `COMP-SMA-PROD`). Branch deletion needs explicit per-action OK.

## Highest-leverage single move

Tier 0. One SessionStart recall hook that reads intent.db and injects a digest + candidate skills. It is
the read-back half of Anthropic's own memory loop, it is the fix the reflection identified independently,
and it converts continuity, skill-loading, goal-tracking, and spec-anchoring from prose the model may
ignore into context injected every session. Build it before adopting any external framework.

## Citations (external, VERIFIED unless noted)

- [spec1] https://github.com/github/spec-kit  [spec2] https://github.com/Fission-AI/OpenSpec
  [spec3] https://github.com/bmad-code-org/BMAD-METHOD
- [orch] https://github.com/sipyourdrink-ltd/bernstein ; https://code.claude.com/docs/en/workflows
- [eval1] https://github.com/promptfoo/promptfoo ; deprecation: https://community.openai.com/t/deprecation-notice-evals-will-be-shut-down-on-november-30th-2026/1385537
  [eval2] https://github.com/confident-ai/deepeval  [eval3] https://github.com/UKGovernmentBEIS/inspect_ai
- [ver] https://arxiv.org/pdf/2606.26300 (CLAIMED, figures not independently re-fetched)
- [mem] https://github.com/mem0ai/mem0 ; https://github.com/getzep/graphiti ; https://github.com/topoteretes/cognee ;
  https://github.com/letta-ai/letta
- [ctx] https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- [mcp] https://github.com/modelcontextprotocol/registry ; https://github.com/docker/mcp-gateway ; https://github.com/IBM/mcp-context-forge
