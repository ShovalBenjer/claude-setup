# ADR 0003: The platform brain is a measured, self-improving loop (Level-4 floor)

- Status: Accepted
- Date: 2026-07-11
- Deciders: Shoval
- Builds on: ADR 0002 (knowledge-and-capability delivery)

## Context

A 2026-07-10 brainstorm on AI-runtime maturity (model-centric -> agent -> harness -> self-
improving harness) mapped the frontier onto this package. The finding: the substrate for a
self-improving loop already existed but was open-loop. Orchestration telemetry recorded per-
strategy pass_rate/tokens/duration; evidence recorded proof pass/fail; the sim2real cores
(pass^k, kappa, trace-diff, tier-1) were pure and tested but unwired. The reward was logged
and thrown away; verification happened but never changed the next decision.

The essay's temptation was a cathedral: master 40 math fields, add typed memory, model
auctions, tool invention, self-mutating prompts. That is the exact unwired-scaffold debt this
codebase spent days paying down. The senior read: the moat is that the harness MEASURES and is
TESTED, not that it is baroque. Level 4 is not "add machinery"; it is "wire the machinery you
have to the reward you already log, and prove weekly improvement on a frozen golden set."

## Decision

Close the loop on the cheapest, most reversible surface first (strategy/routing selection),
because the reward is already logged and the action space is small.

1. Strategy bandit (`policy.py`): aggregate telemetry into per-strategy Beta posteriors, and
   Thompson-sample a cost/latency-aware recommendation. `intent telemetry record` closes the
   data intake; `intent policy recommend|stats` reads it. Implements the operator's /loop
   intent (which orchestration strategy wins, recorded over time).
2. Wire the sim2real cores into a recorded `intent eval` pipeline (`eval_cmds.py`): tier-1
   (T4.1), pass^k (T4.3), trace-diff (T4.4), kappa (T4.7) are reachable and write eval_results
   rows. The parked pure rungs become live and queryable.
3. `intent evolve` (`evolution.py`): score the golden set, compare to the last recorded
   baseline, record the delta, report improved/regressed/same. Measurable week over week.
4. `intent retrieve`: the ~/docs corpus is a first-class typed retrieval tool (name+path+
   content), not just a per-turn hook side effect.

## Consequences

Positive: the harness can now answer "which strategy wins" and "did we get better this week"
from data, not vibes; the unwired sim2real cores are live and recorded; every new component
earns its place by moving a measured number.

Negative / honest limitations (do not overclaim): the bandit optimizes the LOGGED objective,
and solo's real cost (lead-context / compaction pressure) is not yet a telemetry field, so the
bandit over-favors solo (pass_rate 1.0 / 0 tokens); the objective needs a lead-context term.
Statistical power is the real gate on the weekly signal (low volume + a non-frozen golden set
make the delta noise). Context-pack memory decay/entropy (relevance x freshness x novelty +
dedup) is designed but not yet built.

## Rejected

- Auto-mutating prompts or code in the loop: speculative and unverifiable at this volume; the
  loop measures and recommends, a human keeps or reverts.
- The 40-topic math syllabus: earn each technique (bandits, information theory, Bayesian
  sequential decisions first) against a measured bottleneck, not upfront.
- Dense embeddings / MCP / model auctions now: still gated per ADR-0002 until measured need.
