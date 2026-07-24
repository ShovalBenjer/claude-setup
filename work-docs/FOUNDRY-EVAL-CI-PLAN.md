# Foundry-Only Eval CI Plan for CS Agents

**Date:** 2026-03-30  
**Scope:** `axia-seekapa-cs-agents-devops`  
**Primary goal:** make evaluation part of CI without recreating the runaway cost pattern from continuous full-size evals.

---

## Non-Negotiable Constraints

This plan uses only these Azure AI Foundry model deployments as evaluator judges:

- `grok-4-1-fast-reasoning-2-eval`
- `DeepSeek-V3.2`

It does **not** use Braintrust as the primary evaluator.

It does **not** run a large full-suite agent evaluation on every PR.

It does **not** send full raw transcripts to judges unless multi-turn behavior is the thing being evaluated.

---

## Why This Plan Exists

The current exported Foundry evaluation showed the real weaknesses are:

- task completion
- task adherence
- groundedness
- relevance

The main issue is not missing safety rails. The main issue is that the eval strategy was too expensive and too broad for routine CI use.

The CI gate therefore needs to be:

- small
- stable
- high-signal
- cheap enough to run on PRs
- strict enough to catch obvious prompt or routing regressions

---

## Evaluation Strategy

## Phase 0: Deterministic Build Gate

Run first, always:

- dependency install
- ruff
- mypy
- unit tests
- existing webhook/channel router integration checks

This stays ahead of model-based evaluation because deterministic failures should never consume evaluator tokens.

## Phase 1: Foundry Smoke Eval Gate in CI

Run in the Build stage after deterministic tests.

Purpose:

- catch prompt/routing regressions early
- validate the deployed/stage agent behavior on a tiny frozen set
- keep cost bounded

Dataset:

- `tests/test_data/foundry_smoke_eval.jsonl`
- 10 rows only
- English only
- no CRM-heavy authenticated flows
- mostly KB, escalation, redirect, and financial-advice edge cases

Judge policy:

- `grok-4-1-fast-reasoning-2-eval` scores all rows
- `DeepSeek-V3.2` audits only a tiny subset

Output:

- JUnit XML for Azure Pipelines
- JSON report artifact
- Markdown summary artifact

Gate outcome:

- any failed smoke row fails the build

## Phase 2: Expanded Pre-Merge Eval

Run on `stage` PRs and optionally on scheduled builds.

Dataset target:

- 40-80 rows
- multilingual coverage
- KB
- complaint/escalation
- off-topic redirect
- financial advice refusal
- account security escalation

Still judge-limited to:

- `grok-4-1-fast-reasoning-2-eval`
- `DeepSeek-V3.2`

But `DeepSeek-V3.2` remains a sampled audit judge, not the full primary pass.

## Phase 3: Nightly Benchmark

Run on `stage` nightly.

Purpose:

- broader drift detection
- compare candidate prompt behavior to baseline behavior
- track cost, pass rate, disagreement rate, and failure clusters

Target dataset size:

- 80-150 rows max

This should remain bounded until we have stable cost and signal.

## Phase 4: Portal-Native Continuous Evaluation

This is still part of the long-term plan, but it should be explicitly budgeted and sampled.

Policy:

- low production sample rate
- hourly run cap
- rollback if evaluator token usage spikes

The previous continuous setup was too expensive for the observed signal quality.

---

## Token Budget Policy

Evaluator prompts must be compact.

Per-row input budget:

- target: `<= 1500` tokens
- hard cap: compact question + compact answer only

Per-row output budget:

- `<= 120` tokens

Prompt rules:

- JSON-only output
- binary pass/fail where possible
- one-sentence evidence only
- no request for chain-of-thought
- no long examples

Compression rules:

- include user message
- include assistant answer
- include required keywords
- include forbidden keywords
- include expected route
- exclude full internal traces unless specifically needed

---

## Optimized Evaluator Prompts

## Primary judge prompt

Use `grok-4-1-fast-reasoning-2-eval` for all smoke rows.

Design:

- compact JSON payload
- evaluates:
  - correct route
  - directness/completeness
  - forbidden behavior
- returns:
  - `pass`
  - `score`
  - `reason`

This is intentionally broader than a single metric because the smoke gate is cost-constrained.

## Audit judge prompt

Use `DeepSeek-V3.2` only on a small subset.

Design:

- compact JSON payload
- checks whether it agrees with the primary evaluator
- returns:
  - `agree`
  - `reason`

Purpose:

- detect judge instability
- avoid paying for full dual-judge runs

---

## What We Keep From The Old Stack

- the old scenario taxonomy
- the old escalation cases
- the old KB coverage ideas
- Braintrust only as optional external experiment tracking

## What We Stop Doing

- Braintrust as the primary evaluation system
- large expensive evals on every PR
- full-suite parallel runs
- judge prompts with long transcripts and verbose rubrics

---

## CI Design

## Build stage ordering

1. install dependencies
2. lint
3. type check
4. deterministic tests
5. Foundry smoke eval
6. artifact packaging

The model-based eval is part of Build, but not literally first.

## Secret and deployment usage

Pipeline must provide:

- Foundry project endpoint
- Foundry API key
- agent name under test
- primary evaluator deployment
- audit evaluator deployment

This plan assumes:

- target agent: `seekapa`
- primary judge: `grok-4-1-fast-reasoning-2-eval`
- audit judge: `DeepSeek-V3.2`

---

## What “Implemented Now” Means

This repository change implements:

- the plan document
- a smoke dataset
- a CI helper script
- pipeline wiring for the Foundry smoke eval gate
- JUnit/JSON/Markdown output for CI visibility

This repository change does **not** yet implement:

- full multilingual expanded eval
- nightly benchmark suite
- portal-native sampled continuous eval orchestration
- judge disagreement dashboards

Those are next steps after the smoke gate proves stable and affordable.

---

## Success Criteria

The CI eval gate is successful if it does all of the following:

- fails obvious routing regressions
- fails financial-advice regressions
- fails missed-human-handoff regressions
- keeps evaluator cost small
- produces artifacts that can be audited quickly
- does not make the build brittle with CRM-dependent test rows

---

## Next Implementation Steps

1. Expand the smoke set from 10 to ~20 rows using the existing JSON test library.
2. Add multilingual smoke rows.
3. Add a nightly dataset capped at 80-150 rows.
4. Add baseline-vs-candidate comparison instead of absolute-only pass/fail.
5. Add portal-native continuous eval with explicit hourly caps.
