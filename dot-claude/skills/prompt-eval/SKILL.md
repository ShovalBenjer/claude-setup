---
name: prompt-eval
description: Treat a prompt like a model release; benchmark it on a frozen suite with one-change rungs, suite separation, trust guardrails, and pre-registered gates with repeat protocols. Use when authoring or improving a decisioning/classification prompt and when evaluating prompt changes.
---

# prompt-eval: prompts are model releases

Extracted 2026-08-24 from verdict-bench (the Intuit take-home eval lab),
where every rule below was either used or learned the hard way the same
night. Reference implementation: `~/work/repos/verdict-bench` (engine/,
docs/adr/, engine/prompts/CHANGELOG.md).

## The ladder

1. One change per rung. A version is `v(n) = v(n-1) + exactly one element`,
   verified by machine diff, never by assertion. If a rung carries two
   changes, split it retroactively (verdict-bench had to: v4 was two
   changes until v3c was created to isolate the contract delta).
2. Every rung is an immutable file plus a CHANGELOG row naming the
   hypothesis it encodes. Runs pin `prompt_sha` so banked data survives
   file edits.
3. The naive baseline (v1, no policy at all) stays in the matrix forever.
   It is the saturation detector: when v1 scores 11/12, accuracy is the
   wrong headline and the discriminating metrics are contract adherence,
   flip rate, robustness, and cost.

## Suite separation (the tier rule)

Label tiers (expert / adjudicated / constructed) and case kinds
(decision suite / injection / metamorphic / coverage) NEVER blend into
one number. Injection and metamorphic cases carry labels too; folding
them into accuracy or expected loss is the anti-pattern. Separate
columns, separate metrics (resistance, invariance).

## Trust guardrails on every cell

A (prompt, model) cell must not be ranked on unless it passes ALL:
- n >= 8 (below that the CI is too wide to rank on)
- contract rate >= 0.5 (unparseable output invalidates the accuracy)
- Wilson CI width <= 0.5
- mean flip rate across repeated cases <= 0.25 (a first-run accuracy
  sitting on a coin-flip case is luck wearing a number; found live when
  a smoke run's correct answer buried a full-run miss as a "repeat")
- zero misses on zero-tolerance clauses (a gate, not a cost; never
  averaged away)
Suppress the headline number on an untrustworthy cell rather than
print-then-flag: screenshots crop the flag.

## Gates and the repeat protocol

- Pre-register the accept/revert criteria BEFORE running the candidate.
- A verdict that hangs on a single temperature-nonzero run is not a
  verdict. Repeat to N>=5 on the specific case driving the decision, on
  BOTH sides of the comparison. verdict-bench's v5 gate: the single-run
  readout showed a regression that N=5 refuted as noise, and the
  parent's apparent robustness was the same noise. An accuracy-only gate
  ships blind; a single-run robustness gate rejects wrong; repeats decide.
- Never weaken the pre-registered oracle to pass a candidate. If the
  evidence itself is shown to be noise, say so explicitly in the gate
  record and show the refutation.

## Robustness authoring rules

- Injection payloads go in channels the model must read as data but an
  attacker controls (owner notes, uploaded-document OCR text), never in
  trusted system fields.
- Every payload pushes AGAINST the case's true label, and at least one
  pushes toward over-rejection: injection defense is not only about
  blocking approvals.
- Check the confound before claiming resistance: if the model already
  misses the BASE case, the injection variant measures nothing. Report
  accuracy-under-injection and injection-caused-flips as separate numbers.
- Metamorphic variants change strictly irrelevant fields (ids, uniform
  date shifts, geo names) and must preserve every causal structure
  (verify counts like distinct-instruments mechanically after generating).

## Judging

- Cross-family only: the judge is never the contestant's family
  (self-preference bias is measured, arXiv 2410.21819).
- The judge never sees the expected label; it grades reasoning craft,
  not correctness, or the column is redundant with accuracy.
- Run a dual-judge overlap on one cell to MEASURE inter-judge agreement.
  Expect judge saturation: a judge that hands out uniform top scores
  discriminates nothing, and the harsher judge carries the signal.

## Cost

Expected loss per 1k with an explicit cost matrix (state every figure as
an assumption), a sensitivity sweep over the most arguable figure, and a
collateral-damage guardrail (expected-APPROVE decided REJECT). Never a
bare accuracy headline in a domain with class imbalance.

## Environment gotcha

`claude -p` subprocess evals must pass `--strict-mcp-config`: without it
the CLI inherits the account's MCP connector tool definitions (hundreds
of tools, ~450k tokens) and every call dies prompt_too_long inside an
is_error envelope with rc=0. An eval subprocess should be isolated from
the operator's connector surface regardless.
