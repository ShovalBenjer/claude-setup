---
prd: intent-control-plane
ticket: none (internal platform brain)
status: active
supersedes: none
created: 2026-07-11
---

# Spec: the self-evolving depth harness (four layers + fix-commit provenance)

PRD delta against `docs/prd/intent-control-plane.md`. Implements new items P13-P21. Does not
amend or supersede P1-P12 (they stand). This spec is the control plane for the depth-harness
build; slices land against the acceptance criteria here and flip the PRD rows.

## Thesis

Depth is not the fitness rubric (the persona contract). Depth is the SEARCH a swarm of cheap
models runs against that rubric: many small local passes, each layering one improvement onto a
shared artifact, scored, kept only if better AND non-regressive, looped until the gradient
flattens. Depth becomes a measured count of accepted passes, not a claim. The moat is the
harness, not the model (sol5.6 Level 3 -> Level 4). In the 2026 self-evolving-agent literature
the model weights are frozen and the agents/personas/prompts/tools are the evolvable population;
`intent-control-plane` already has the fitness engine (persona rubrics + telemetry + policy
bandit + evolution + eval tiers), so this is wiring, not a new harness.

Grounding (dated primaries; full sweep in workflow wo3q223jk): ShinkaEvolve (arXiv:2509.19349),
Darwin-Godel-Machine (2505.22954), Self-Harness (2606.09498), Meta-Harness (2603.28052), GEPA
(2507.19457), Rubric-Grounded RL (2606.08625), RECAP/Physical-Intelligence (2511.14759),
Budget-Aware Routing (2602.21227), durable-execution "agents as state machines" (2605.02584),
SZZ (2005) + JIT defect prediction (Kamei 2013), agentic-JIT-retrieval-beats-vector-DB
(Amazon AAAI 2026, 2602.23368), tree-sitter symbol-graph repo maps (Aider; Codebase-Memory
2603.27277).

## Design constraints (the SOTA corrections, binding on every slice)

1. Separate editor and grader. The cheap worker proposing an edit is never the same call that
   scores it. Self-grading is measurably lenient (Anthropic harness-design).
2. Decomposed rubric, deterministic-disposes. Score each rubric axis as an independent weighted
   criterion; where a deterministic check exists (tests/lint/types/schema) it DISPOSES the
   reward, the judge only proposes. A single holistic judge score is a reward-hacking surface.
3. Keep an archive, do not prune to best-only. Weaker variants are stepping stones (DGM). A
   "fired" persona is BENCHED with its failure-tagged history intact, not deleted.
4. Held-out regression gate on keep-if-better. A promoted pass must be re-scored on a held-out
   rubric slice, not only the case it targeted; overfit-to-the-targeted-case is the #1
   self-improve failure mode (Self-Harness, Meta-Harness).
5. Raw traces, not summaries, into the record's evidence (compression is the dominant optimizer
   failure mode); the compressed key is for retrieval only.
6. Cost-aware, per-pass model routing with a hard budget cap; scoped diffs only for workers
   (full-file-rewrite freedom increases reward-hacking); an explicit anti-gaming screen.
7. Topology-fitness pre-check before fanout: swarm the independent passes, orchestrate the
   coupled ones (optimal topology is predictable from task decomposability).
8. Human gate on blast-radius org changes. Auto-demote (down-weight) is unattended; auto-fire
   or spawn-a-persona-that-then-acts-autonomously needs a held-out/golden-parity gate + OK.

## Layer 1 - Knowledge (repo map fed to the swarm)

AC-K1: `project_map` grows a multi-language symbol/call/import graph via tree-sitter (the one
accepted new dependency), stored as sqlite `symbols`/`edges` tables, no daemon (mtime check).
AC-K2: `retrieval.py` ranking gains a `graph_relevance` term biased toward session-active files.
AC-K3: Stays agentic-JIT + sqlite-first; no vector-DB-first rewrite, no LangGraph-for-knowledge,
no GraphRAG. Dense embeddings remain a deferred, conditional Stage-2 secondary index.

## Layer 2 - Orchestration (durable, guarded state machine)

AC-O1: Each pass is a committed guarded transition over `state_transitions` (table exists):
`drafted -> rubric-scored -> {kept|rejected} -> regression-tested -> shipped`; reaching a later
state without its predecessor is structurally impossible (`allowed_by_contract`).
AC-O2: Append-only event log per pass; checkpoint-before-next; undo = compensating transition
(revert artifact to last kept version), DBOS-style over the existing sqlite, no Temporal.

## Layer 3 - Depth engine (the swarm)

AC-D1: `archive.py` population store: variant records, parent selection with exploitation_ratio
(keeps weak stepping-stones eligible), novelty rejection (reuse `text_index.cosine`), held-out
keep gate. [SLICE 1 - this spec's first tracer.]
AC-D2: `swarm_pass` decomposes a craft task into local passes, fans out cheap-model workers,
scores each against the decomposed rubric, keeps-if-better-and-non-regressive, loops to gradient
flat. Emits compact trajectory summaries (PDR/RTV), evidence points at raw traces.
AC-D3: Cost-aware per-pass bandit (extend `policy.py`) with hard budget cap; advantage-
conditioning (reuse pos/neg-labelled exemplars to steer the next generation, RECAP).

## Layer 4 - Company / population (grade -> PIP -> bench -> rehire -> grow)

AC-C1: Per-persona scorecard from telemetry + evidence + fix-commit survival: reward, cost,
asymmetric earned-trust (+success / -failure, larger penalty).
AC-C2: `roster_status` in {active, pip, benched} with a significance guard (never demote/fire on
noise; trend + minimum-sample gate; 3-strike escalation).
AC-C3: Reflective rehire: mutate a benched persona's contract (model tier / role split /
sharpened depth principles) and validate on a held-out slice before it returns to active.
AC-C4: Grow-on-gap: spawn a new sub-persona when the roster has a coverage gap for a task class
(topology-fitness), human-gated before it acts autonomously.

## Layer 0 - Fix-commit provenance (feeds Layer 4 grading)

AC-F1: `git-provenance` walks git log, classifies feat/fix (conventional-commit), runs a
lightweight SZZ (`git blame` a fix's lines -> introducing commit) as a confidence-weighted edge.
AC-F2: A heuristic JIT risk score per diff (churn x touched-file fix-density x cross-file spread);
join to telemetry (which session/persona/model/token-cost produced the commit).
AC-F3: Per-persona survival % (agent LOC alive at 14/30d) + rework-adjusted throughput feed the
Layer-4 scorecard and the bandit reward. Kill LOC-as-productivity.

## Sequencing (vertical TDD slices)

- S1: `archive.py` (AC-D1) - the shared spine (stepping-stones + held-out keep gate + novelty).
- S2: `company.py` grading (AC-C1/C2) - scorecard + asymmetric trust + significance-guarded status.
- S3: guarded transitions helper over `state_transitions` (AC-O1/O2).
- S4: decomposed-rubric scorer (constraint 2) + `swarm_pass` skeleton (AC-D2), code-first
  (objective test/lint scoring) before UI (visual scoring).
- S5: cost-aware per-pass bandit + advantage-conditioning (AC-D3).
- S6: `git-provenance` SZZ + JIT + survival (AC-F1/F2/F3).
- S7: tree-sitter symbol graph + graph_relevance (AC-K1/K2).
- S8: reflective rehire + grow-on-gap, human-gated (AC-C3/C4).

## Non-goals

Vector-DB-first retrieval; LangGraph adoption for knowledge; MS-GraphRAG; Temporal; Code World
Model; auto-firing or auto-spawning autonomous personas without a human gate; SSM/Mamba model
work; any corp-repo or Azure resource change (this package is local-only).

## Premortem (5 failure modes)

1. The swarm reward-hacks the rubric. Mitigation: constraint 2 (deterministic-disposes) +
   anti-gaming screen + scoped diffs only.
2. Keep-if-better overfits and silently regresses neighbors. Mitigation: AC-D1 held-out gate.
3. The company layer fires good agents on noise. Mitigation: AC-C2 significance guard + archive
   (benched, recoverable), never delete.
4. tree-sitter breaks the zero-dep property. Mitigation: label it "zero-dep except tree-sitter";
   it is the ONLY accepted new dep, isolated to Layer 1, JIT-retrieval still works without it.
5. Slices stall as scaffolds (the unwired-confidence trap). Mitigation: each slice ships a
   subcommand + green gate + PRD row flip; no slice claimed done without pasted test output.
