# Work-Side General Setup — Full (mojuco + artifixer + latent path)

Date: 2026-06-28
Owner: Shoval
Status: Standalone setup for general work
Scope: a reusable, self-contained work discipline. Carries the full detail so it can travel
to the work machine without the personal doc.
Companion: `2026-06-28-personal-autonomy-loop-CLAUDE-LOCAL.md` (separate; personal,
Claude-subscription-only)
Substrate: `2026-06-25-local-intent-control-plane.md`
Implementation plan: `docs/specs/2026-06-28-work-general-mojuco-artifixer-foundry-plan.md`

## Purpose

The personal loop proves the engine cheaply on resumes/self-promotion. This is the *general
work* version: the same two primitives, full mechanics inlined, adapted to work surfaces
(CS agent, KB, content QC, eval). Unlike the personal side, work may use the full work
toolchain — Codex executor, Azure Foundry eval judges where deployed, and (for the latent
path) self-hosted open-weight models.

## Execution Model

| Role | How it runs on work side |
|---|---|
| grounding/opacity gate (veto, workhorse) | local `uv run python` — output→source trace, schema, dedupe, redaction; free, first |
| adversarial refuter | a **different model** than the generator (grok/DeepSeek vs Claude/Codex) — real decorrelation, refute-by-default |
| artifixer generator/repair | Codex (source-of-truth runner) + Claude (compatibility worker) |
| calibration | sim-to-real agreement vs live production outcomes |
| bandit allocation | small local script (Thompson sampling) |
| latent edges (forward path) | self-hosted open-weight models, trainable transfer modules |
| storage / truth | local intent ledger + Hive beads (control-plane spec) |

## Anti-Goals (mature attitude)

- No single weighted-sum scorer `score = Σ wᵢ·featureᵢ` posing as intelligence.
- No regex/keyword judge standing in for a simulated reviewer/user.
- No "RL"/"learning" claim for what is measurement + calibration.
- No hand-edited artifacts — only regenerable sources.
- No completion claim without proof; no bead closed from a summary.
- **No persona-flavoring panel** ("spawn N PhD reviewers + a CTO auditor" on one model):
  same model + role label = correlated errors = false confidence. Independence comes from
  different evidence, a different model, and adversarial framing — never a job title.

Math is allowed only in: Thompson allocation, the sim-to-real agreement metric, and (on the
latent path) genuine gradient training of transfer edges.

---

## Primitive 1 — mojuco (LLM-as-environment, full)

A *simulated environment* of reviewers/users that produces reward cheaply, before paying
real production cost. **Sim-to-real transfer** = shipping to the live surface.

### Judges are environment dynamics, not checklists
A judge is a **simulated persona** (config + model). The subject (agent output, KB answer,
content asset) is run *through* it; you observe where it snags ("contact"). It scores and
explains — it never edits.

### Judge contract (uniform verdict)
```json
{
  "judge_id": "skeptical_customer_he",
  "subject_id": "cs_answer@conv_123",
  "pass": false,
  "score": 0.58,
  "findings": [
    {"criterion": "grounding", "severity": "fail",
     "span": "<the ungrounded claim>",
     "why": "no KB source supports this",
     "fix_hint": "ground in KB doc or refuse"}
  ]
}
```

### Decorrelation, not persona-flavoring (the part naive setups get wrong)
**Anti-pattern:** spawning N "expert personas" (PhD reviewer, CTO auditor) on the *same*
model. Same model + role label = correlated errors = false confidence; their agreement
proves nothing. Real independence comes from three sources, in order of strength:

- **Different evidence:** feed each judge different inputs (raw output only / + source of
  truth / + policy). Different evidence → genuinely different verdicts.
- **Different model:** a refuter on grok/DeepSeek vs a Claude/Codex generator is an actual
  second distribution. Work side has this — use it for the audit role.
- **Adversarial framing:** the refuter must *refute*, default-reject unless evidence forces
  a pass — not a free-to-nod "reviewer".

"Domain randomization" then = vary the *evidence and adversarial pressure* (customer types,
languages he/en/ar, adversarial probes), not the job title in the prompt. The minimal
mature set is: grounding gate (veto) + one different-model adversarial refuter + sim-to-real
calibration — not a panel.

### Deterministic-first eval pyramid (cost discipline)
1. Deterministic, free, every run: schema, parse, dedupe, redaction (`.env`/secrets/PII),
   policy checks.
2. Sampled LLM personas after: default ~5% sample + 100% of deterministic failures.
3. Nightly/before-release: replay set, mutation tests, **pass^k** (repeat-consistency, not
   one lucky pass), adversarial judge.

### Sim-to-real gap (makes it falsifiable)
`agreement(mojuco_predicted, real_outcome)` per persona, where real_outcome is the live
production signal (resolution rate, escalation rate, eval pass). When sim passes things that
fail in production, the simulator is miscalibrated — retune personas until sim predicts real.
This is the difference between an instrument and theater.

---

## Primitive 2 — artifixer (opacity-masked grounded generation, full)

Generates and repairs outputs by treating the source of truth as observed views and the
gaps as under-observed regions (after NVIDIA ArtiFixer's opacity-mixing for 3D
reconstruction).

### Opacity map = grounding density
| Zone | Evidence | Legal move |
|---|---|---|
| High opacity | direct KB / source-of-truth grounding | **byte-faithful** — never embellish a grounded fact |
| Low opacity | partial / derivable from grounded facts | **interpolate**, consistency-constrained to the sources, marked as synthesis |
| Zero opacity / off-trajectory | no grounding, inconsistent | **artifact (hallucination) → kill / honest-block** |

"Off-trajectory artifacts" = answers that go beyond grounded territory and read as wrong.
artifixer either smooths the reach while staying consistent, or refuses.

### The repair loop
```text
artifixer run --subject <id> --panel <work-panel> --max-rounds N
  1. generate (or take live output)
  2. mojuco judges -> verdicts
  3. all pass -> done
  4. else: sort findings (veto/grounding first), repair the SOURCE at cited spans only
  5. re-judge; loop
  6. max-rounds with open fails -> HONEST BLOCK with the exact missing grounding
```

### Three rules that keep it honest (not a slop amplifier)
1. Repair the **source**, never the rendered artifact (single source of truth, regenerable).
2. Grounding/veto findings cannot be repaired by softening — only **ground it or cut it**
   (enforce as a reward-machine illegal transition, per control-plane spec).
3. **Honest block beats fake pass** — a blocked item becomes a Hive bead naming the missing
   proof, not a silently-shipped weak answer.

### Teacher → student (generation economy)
A slow, high-context "teacher" pass crafts the canonical grounded answer/asset once; a fast
"student" pass distills it into all variants / channels / languages. Quality once, variants
many.

---

## Forward Architecture — Latent / Vector Communication

Today our agents (mojuco personas, artifixer) talk in **text**. That is convenient for
humans but a computational bottleneck: encoding to discrete tokens severs gradient flow and
loses information at every hop, and it blocks end-to-end optimization of the whole
multi-agent system. This is the thesis Mike Erlihson summarizes ("collective AI is not
achieved by speaking English to each other, but through latent spaces and flowing
gradients") and it is backed by concrete work:

- **Language Model Networks / Dense Communication** (arXiv 2505.12741): LLMs as graph nodes
  stripped of embedding/de-embedding layers; edges are trainable seq2seq transfer modules
  passing **dense vectors**; MLP-like topology; weight-sharing/recursive to cut training
  load; the whole network is **end-to-end differentiable**; roles and protocols are learned
  from final-task supervision with **no intermediate-message labels**; reported large
  reasoning gains at **<0.1%** of original training cost.
- **Interlat / latent-space agent communication** (arXiv 2511.09149), **Thought
  Communication in Multiagent Collaboration** (arXiv 2510.20733), RecursiveMAS: pass
  continuous last-hidden-states directly between agents ("vector telepathy").
- Related architectural pressure Mike flags: recurrence / State-Space Models for *implicit
  activation dynamics* — internal state that evolves in real time rather than passive
  scanning of a long context window.

### Honest constraint
True vector-to-vector requires access to model **internals** (hidden states) and **training
over the graph**. It is **not implementable on a frozen text-only API** (Claude
subscription, hosted Foundry chat). It becomes real only with self-hosted open-weight models
we control. So this is a work-side R&D path, not a quick win — but the *design* can be made
ready now.

### Maturity ladder (be ahead without faking it)
| Level | Channel | Implementable with |
|---|---|---|
| L0 — now | **Structured dense messages**, not prose: typed JSON verdicts/cards, minimal text round-trips | any text API (Claude/Codex/Foundry) |
| L1 — soon | **Embedding-space routing & retrieval**: opacity map, context-pack ranking, persona routing done in vector space (embeddings we compute), not via re-reading prose | embeddings endpoint (Foundry/local) |
| L2 — R&D | **Latent edges**: stripped open-weight nodes + trainable transfer modules, end-to-end differentiable (LMN/Interlat) | self-hosted open-weight models + training budget |

### Swappable message contract (the actual "be ahead" move)
Define every inter-agent edge as a contract object so the *transport* can change without
redesigning the graph:
```json
{
  "edge_id": "mojuco->artifixer",
  "from": "judge:skeptical_customer_he",
  "to": "artifixer:repair",
  "transport": "text_json | embedding | latent_vector",
  "payload_ref": "verdict_id | vector_id | hidden_state_ref",
  "differentiable": false
}
```
Build the graph topology and contracts at L0 today. When L1/L2 substrate exists, flip
`transport` from `text_json` to `embedding`/`latent_vector` per edge — the orchestration
graph, personas, and opacity rules stay. You inhabit the 2030 architecture incrementally
instead of waiting for it.

---

## Where math lives (and only there)

- **Thompson sampling** (Beta-Bernoulli on the real outcome) for allocation across
  variants/personas — correct under low volume, no hand-set ε.
- **Sim-to-real agreement** metric for calibration.
- **Gradient training** of transfer edges — only on the L2 latent path, only with
  self-hosted models.

Everywhere else, the signal is an LLM environment grounded in retrieval, or a real outcome.
No linear scorer is ever the decision authority.

## How it sits on the control plane

- Intents captured before work; context packs compiled from the local ledger (cited).
- Evidence attached to every completion claim; beads gated on proof — no close from summary.
- Foundry endpoints are utilities (embeddings/extraction/eval), never source of truth.

## Setup checklist (general work)

1. Intent ledger + Hive bead bus available for the work repo (control-plane spec).
2. One eval surface defined as a mojuco **persona distribution** (not a single judge), with
   deterministic-first pyramid wired.
3. artifixer opacity rule wired on one surface: grounded → faithful, partial → marked
   interpolation, ungrounded → honest-block.
4. Thompson allocator + sim-to-real gap logged once against real production outcomes.
5. Every inter-agent edge expressed as the swappable contract (transport=`text_json` at L0).

## Acceptance Criteria

1. Outputs clear a deterministic grounding gate **and** an adversarial refuter (different
   model where available) — never a panel of same-model flavored personas.
2. Every output line resolves to grounding (high), a marked interpolation (low), or is cut
   (zero) — no ungrounded assertions.
3. Allocation is Thompson-sampled from real outcomes, not a predicted score.
4. Sim-to-real gap computed; ≥1 persona recalibrated from production data.
5. Edges carry the swappable transport contract, ready for L1/L2.
6. No completion claim without attached proof.

## Non-Goals

- Not the personal resume/self-promotion engine (see companion doc).
- No autonomous outward action without proof + approval.
- No single linear scorer as decision authority.
- No claim of latent/vector communication on a frozen text-only API — L2 requires
  self-hosted open-weight models.

## Sources

- Language Model Networks / Dense Communication between Language Models — arXiv 2505.12741
- Enabling Agents to Communicate Entirely in Latent Space (Interlat) — arXiv 2511.09149
- Thought Communication in Multiagent Collaboration — arXiv 2510.20733
- NVIDIA ArtiFixer — research.nvidia.com/labs/sil/projects/artifixer
- DeepMind MuJoCo — github.com/google-deepmind/mujoco
- Framing: Mike Erlihson (#אייאיי_עם_מייק) summaries on latent/vector LLM communication
