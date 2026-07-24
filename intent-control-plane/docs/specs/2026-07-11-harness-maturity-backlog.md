---
prd: intent-control-plane
ticket: none (internal platform brain)
status: active
created: 2026-07-11
---

# Spec: harness-maturity backlog (the 2027-ready checklist, honestly scored)

Turns the Custom Harness Checklist (13 categories + 2027 features) into a prioritized, buildable
backlog against our actual code, from the evidence-based audit of 2026-07-11. What we already have
is not repeated as tasks; only the real gaps are. Verified against the code (36 modules, 326 tests):
no semantic cache, no dense embeddings, no model failover, no sandbox, and the eval gate is failing
0/20 right now.

## Framing (do not lose this)

The checklist is production HYGIENE, not the frontier. It omits our actual moat, the self-evolving
depth/company/bandit/archive layer (P13-P21, already built). Scoring 100% here makes us a solid
production harness, not automatically SOTA. We are strong where it is rare (the learning layer) and
thin where it is common (memory/cache/eval/observability plumbing). This backlog closes the plumbing.

## Prioritized tasks

- **P1 — Fix the eval gate (BROKEN NOW).** Category 11. The gate is 0 pass / 20 fail per the G1
  report while eval smoke passes; diagnose the divergence and make the gate green and trustworthy.
  Precondition for everything graded: a grading swarm on top of a broken grader is meaningless.
- **P2 — Semantic cache.** 2027 feature; the biggest untapped speed lever (we have zero cache).
  Cache LLM responses, tool results, and retrieval results by a semantic key so repeated work is not
  recomputed. Start with an exact+normalized key, add embedding-nearest later.
- **P3 — Dense + typed memory.** Category 8. Add an embedding store and typed memory kinds
  (episodic / semantic / procedural / scratchpad), demoting tf-idf to one index among several. Keep
  agentic-JIT for CODE retrieval (2026 evidence says vector-first loses there); dense is for fuzzy
  cross-session recall, not code.
- **P4 — Observability surface.** Category 10. The data is already captured (telemetry.jsonl,
  audit.jsonl, foundry_calls, session_events); build the cost / latency / success dashboard so it is
  visible instead of buried.
- **P5 — Wire the learning layer to live spawns.** Connect gastown-spawn -> guardrails (scoped-diff,
  reward-hacking, topology-fitness) -> archive -> rubric -> company grade. This is the transmission
  gap: the engine (P13-P21) is built but not connected to the wheels (the live spawner).
- **P6 — Reliability plumbing (smaller gaps).** Category 1/2: model failover-on-error + a retry /
  cancellation policy. Category 9: real tool sandboxing + a prompt-injection defense (input
  delimiting / spotlighting). Category 1: a clean multi-provider abstraction (Codex a2a + Foundry are
  ad hoc today).
- **P7 — 2027 stretch.** DAG workflow engine (Workflow is pipeline/parallel, not arbitrary DAG),
  speculative execution, multi-modal memory, a mathematical planner. Only after P1-P5 land.

## Shipped (auto-flight 2026-07-11, 326 -> 386 tests, ruff+mypy --strict clean)

- A1 done: fixed the lying eval-gate counter (self-improve.py now reports per-repo; our gate was 28/28 all along).
- A2 done: `cache.py` (semantic cache, normalized sha256 key + TTL jsonl store + hit/miss stats).
- A3 done (first pass): `memory.py` (typed episodic/semantic/procedural/scratchpad + tf-idf recall + pluggable EmbeddingBackend interface; dense impl still a stub).
- A4 done (data layer): `observe.py` (telemetry/foundry aggregation: success rate, p50/p95, per-strategy, cost). GUI dashboard not built.
- A6 done (first pass): `reliability_policy.py` (model failover ladder, retry+backoff decision, injection screen). Real sandbox still open.
- A-seam done: `durable.py` (DurableBackend Protocol + InMemoryBackend, proves transitions.py is swappable for DBOS/Temporal without a rewrite).
- REMAINING: A5 (wire gastown-spawn -> guardrails/rubric/archive/company), wire these 5 modules into cli.py + their consumers (they are built+tested but UNWIRED), A7 stretch, dense-embedding impl, dashboard GUI, real sandbox.

## Track D — View / TUI (the input under-weighted; local, spawnable)

The view is our weakest layer and a standing want (gamified HUD, Mosaic's watch+takeover, the
harness-command-center, the stalled custom-TUI rainfall/meme work). Promoted from a deferred spec
note to an explicit track.

- **D1 — Gamified HUD to designer-grade.** The statusline HUD + spinner verbs + party cards exist but
  are not at the bar. Iterate to craft (Widgora OKLCH standards, screenshot-diff), Diablo/WoW/Maple feel.
- **D2 — Live agent watch + take-over.** The one Mosaic feature worth copying, watch any running
  agent and seize control of a pane, on Linux/web (Mosaic itself is macOS-only). This is what "see the
  dogs in action" actually needs, beyond the current gastown-spawn stream + /workflows.
- **D3 — Rebuild harness-command-center as the real view (or a proper TUI)**, not the scaffold, with
  D2's takeover as the centerpiece. Fold in the custom-TUI work (rainfall loader, meme integration).

## Track A addendum — substrate seam (the Temporal input, the part to do now)

- **A-seam — Durable-execution interface behind `transitions.py`.** Define advance/current/compensate
  as a swappable interface so a later DBOS (crash-resume) or Temporal (fleet) backend is a backend
  change, not a rewrite. The rest of the Temporal/DBOS adoption stays trigger-gated per
  `2026-07-11-substrate-view-mosaic-temporal.md`.

## Maturity (corrected from the checklist author's estimate)

core harness ~75, tool orchestration ~85, DX ~80 (view layer weak), memory/context ~45 (not 60),
evaluation ~40 and currently BROKEN (not 55), observability ~45, production reliability ~40, and the
row the checklist omits: self-improvement/learning ~70 (built, wiring pending). Sequence: P1 first.
