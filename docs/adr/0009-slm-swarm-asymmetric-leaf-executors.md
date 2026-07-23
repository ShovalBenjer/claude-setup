# ADR-0009 — SLM swarm = asymmetric leaf executors + trace flywheel (not a debate swarm)

Status: Accepted (2026-07-23)

## Context
Question: should the Claude OS run a swarm of small language models (SLM, 1-14B,
local CPU or rented GPU) alongside the frontier orchestrator? The 2025-2026
literature answers clearly, and the answer depends entirely on SHAPE.

Key evidence:
- NVIDIA "SLMs are the Future of Agentic AI" (arXiv:2506.02153): SLMs are
  sufficient/suitable/economical for the repetitive, narrow calls that dominate
  agent graphs; 7B serves 10-30x cheaper than 70B+; 10k-100k examples specialize.
  Proposes a 6-step LLM->SLM conversion recipe: log calls -> curate+PII-strip ->
  cluster tasks -> pick SLM per cluster -> LoRA/distill -> iterate. A data flywheel
  off the orchestrator's own logs.
- Routing/cascade (FrugalGPT 98% cost cut; RouteLLM 85% cut at ~95% GPT-4 quality)
  and speculative decoding (2-3x, identical output) are the ROBUST asymmetric wins.
- SLMs win on tool-calling (xLAM-7B > several GPT-4s on BFCL-v2), structured
  extraction (NuExtract-4B > GPT-4.1 zero-shot), routing/intent, WITH constrained
  decoding (JSONSchemaBench erases the format gap). They LOSE on hard reasoning,
  agentic code (7B ~23% vs frontier ~80-95% SWE-bench), judgment, world knowledge.
- The rebuttals are equally clear: Self-MoA (a single strong model sampled beats
  mixed swarms); MAST (41-87% multi-agent failure, structural); Cognition
  "Don't Build Multi-Agents"; SLM-in-loop cascade emits invalid tool calls ~19x
  more and cannot self-recover past ~6 hops.

## Decision
Run a SMALL, ASYMMETRIC swarm, never a symmetric one:
- The frontier (Claude) PLANS, DECIDES, JUDGES, and DRIVES the loop.
- SLMs are STATELESS LEAF EXECUTORS for bounded, format-constrained, high-volume
  sub-tasks, behind a calibrated cheap-first router, every output schema-checked,
  every uncertain case escalated to the frontier.
- Specialists are fine-tuned (LoRA/QLoRA) off the OS's OWN trace logs (audit.jsonl,
  skill-usage, a2a-audit) — the NVIDIA flywheel, PII-stripped first (pii-handling).
- Compute: local CPU / cheap on-demand 4090 for serving the small tier; rent an
  A100/4090 for the ~$3-10, 2-4h fine-tuning jobs (ADR direction: ephemeral GPU).

## What we explicitly do NOT do
- No SLM driving a multi-hop agentic loop (19x invalid-call rate, no-recovery).
- No symmetric SLM debate/vote swarm to replace the frontier (proposer quality
  beats diversity; adds O(n^1.4-2.1) coordination cost for little/negative gain).
- No SLM as a judge that gates a decision (position bias, single-token-foolable).
- No assumption the local cost win holds at low volume (self-hosting beats the API
  only above ~50% GPU util; for a solo operator, local CPU / on-demand is the host).

## Consequences
+ Biggest solo-operator wins are cheap: a local router (biggest bill reducer) and
  local structured-extraction/classification, both on hardware already owned.
+ The flywheel compounds: the OS's own logs become free specialist training data.
+ Guards are concrete (schema-check + escalate-on-uncertain), enforceable in code.
- Requires the router escalation threshold to be calibrated and audited (mis-tuned
  router silently degrades quality) — every "kept local" decision is logged.
- Fine-tuning specialists is a real (small) MLOps effort, sequenced as R&D, not a
  blocker for the closed harness.
