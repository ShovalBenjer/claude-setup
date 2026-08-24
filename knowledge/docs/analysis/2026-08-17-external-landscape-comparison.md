# External landscape comparison: 7 talks, 3 repos, one preprint (2026-08-17)

Point-in-time scan, operator-ordered. Sources: four AI Engineer conference talks
(Horthy/HumanLayer, Mishra/Amazon AGI, Chin/Neo4j, Brick/Google), three YouTube
essays (Vizuara research-agents, Cloud Codes deepseek-harness breakdown, Kai VRAM
tiers), the CommandCodeAI org, deepseek-ai/deepseek-harness, and cordiverse/paper.
Video evidence is auto-captions read whole; proper nouns and benchmark numbers from
captions are ASSUMED until checked against a primary source. Repo claims are
VERIFIED reads (clones in the session job dir, not retained).

## The one repeated cross-source signal

Three independent sources (Horthy, the deepseek-harness architecture, Amazon's
RL-to-IRL) converge on the same failure class: the rule exists as prose while the
oracle does not. Our own adopt list below is mostly instances of closing that gap.

## Adopt (cheap, concrete, fits tools/audit or hooks)

1. Append-only-write oracle for `state/*.jsonl`: convention today, checked by
   nothing. A grep-level audit check formalizes it. (deepseek-harness: the request
   log is append-only and reconstructible; corrections are rows, never rewrites.)
2. Enforced pre-implementation design gate: product review, architecture doc,
   type-level design, vertical slices exist here as skills and rules (/diverge,
   premortem, docs/prd), not as a gate step. (Horthy: pre-planning is what keeps
   human review feasible; HumanLayer's lights-out July 2025 experiment failed.)
3. "Model-visible means logged" invariant, one rule sentence: anything reaching a
   model request must be reconstructible from the session log. Catches silent
   prompt drift in subagent task packets. (deepseek-harness AGENTS.md.)
4. Risk-classified pre-action guard: couple the-loop-may-act's MAY/MAY-NOT list to
   a PreToolUse check on push/merge/deploy verbs. (Amazon: action risk classifier.)
5. Loop/repetition detector for long sessions; one loop-shaped failure is already
   on record (gate-fingerprint Stop-hook loop). (Amazon: execution monitor.)
6. Skill-routing accuracy as a measured number from `state/routing.jsonl` and
   `state/skill-use.jsonl` against the Gastown registry. Router-vs-spawn agreement
   measured 0 of 20 in the week to 2026-08-12; this makes the number continuous.
   (Google FunctionGemma: 46 to 90 percent selection reliability as the metric.)
7. Real graph edges over ADR/lesson/rule IDs: latent-vector-workflows.md already
   specifies `next_edges`; nothing populates or traverses it. An SQLite adjacency
   table, not Neo4j; a Neo4j dependency would need to win a /diverge comparison at
   our entity count. (Neo4j CrabRAG: markdown-plus-vector memory fails multi-hop.)

## Watch

Maintainability benchmarks maturing (Sweep Marathon, Deep Sweep, Frontier Code);
shadow replay-and-diff of gate verdicts against the ledger (stronger fix for the
review domain's sha-vs-tree weakness); prefix-cache-aware context ordering; a
persistent remote execution box for long unattended runs; coverage floor on
intent-control-plane; CommandCodeAI "taste" accept/reject learning (mechanism not
public); cordiverse/paper as citable prior art if self-modifying harness behavior
is ever formalized in an ADR (the paper's own next target is self-evolving agent
harnesses, and it concedes Cordis does not runtime-verify its revertibility
obligation, which is exactly what our falsifier discipline would demand).

## Ignore, with reasons

Plugin-runtime machinery (Cordis revertible effects, agent presets, WASM
sandboxes): we ship no agent runtime. RL training loops and on-device fine-tuning:
no training pipeline here. Full lights-out autonomy: contradicted by
merges-are-the-operators, and the talk's own failure data supports the rule. The
VRAM-tier local-model guide: every tier assumes NVIDIA/AMD VRAM; this machine has
an Intel GPU, so only the CPU-runnable 2 to 4B class is even testable locally, and
the open-model plan's blocks A to E remain the real gate.

## What the sources validate that already exists here

Human-gated merges; append-only hash-chained evidence; verification instruments
that distrust the agent's own report; alternatives-considered decision records
with expiry (the deepseek 683-memo discipline is the same species as
docs/prior-art plus ADRs); progressive skill disclosure (SKILL.md frontmatter is
structurally Google's load_skill pattern).
