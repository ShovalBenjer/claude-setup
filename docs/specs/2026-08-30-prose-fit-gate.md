# Prose Fit Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** prose_fit

## Problem

`prose_metrics.py` collects density and variance scores to
`state/prose-scores.jsonl` but explicitly defers thresholds: "the threshold
comes from a week of distribution rather than from taste" (line 21 of
`slop_lint.py`). L-2026-07-31-b records the operator complaint that prompted
the collector. The collector has run long enough to fit (256 scores), but
nothing computes the bands or verifies they exist.

## Solution

A new tool `tools/audit/prose_fit.py` with three subcommands:

- `fit`: reads the score corpus, computes percentile bands (p5 through p95)
  for `hyphen_rate`, `sent_words_cv`, and `sent_chars_cv`, and writes
  `state/prose-thresholds.json`.
- `check`: verifies thresholds exist, were fitted from enough data (20+),
  and have not gone stale (corpus grew >50% and by 20+ scores since last
  fit).
- `selftest`: exercises the fit, too-few-data, stale-detection, current,
  and no-thresholds paths.

A new `cmd` domain `prose_fit` in `quality-contract.json` runs `check`.

## Scope

- `tools/audit/prose_fit.py`: new oracle
- `state/prose-thresholds.json`: fitted bands from the corpus
- `quality-contract.json`: `prose_fit` domain entry (cmd, timeout 60s)

## Design decisions

- The domain verifies the infrastructure (thresholds exist and are fresh),
  not individual documents. Per-document enforcement is a follow-up change
  in `slop_lint.py` that reads the thresholds file.
- Staleness is detected when the corpus grows by more than 50% AND 20+
  scores since the last fit. This avoids false positives from small
  increments while catching meaningful distribution shifts.
- The percentile bands use the same `_pct` interpolation as
  `prose_metrics.py` for consistency.

## Non-goals

- Enforcing per-document thresholds in this domain. That belongs in
  `slop_lint.py` which already runs as part of the prose gate.
- Fitting from raw texts. The scores are already computed and stored;
  re-measuring would duplicate work.
