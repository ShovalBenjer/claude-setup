# Corpus Status Reason Trends

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/status_reason_trends.py

## Problem

The promote tool reports flat counts of status reasons (why chunks
were quarantined or rejected), but no tool tracked how those
reasons change over time or which sources produce the most
non-accepted chunks.  A spike in "uncited" quarantines in a
particular month may indicate a batch extraction issue, while a
source that consistently produces "duplicate" rejections may need
dedup tuning.  Identifying these patterns required manual SQL joins
across chunks and sources with date truncation.

## Solution

A new tool `tools/corpus/status_reason_trends.py` with four
subcommands:

- `by-time [--db PATH] [--bucket month|week] [--json]`: status
  reason counts bucketed by time period, showing how quarantine
  and rejection patterns evolve.
- `by-source [--db PATH] [--json]`: per-source breakdown of
  non-accepted chunk reasons, identifying sources that
  systematically produce quality issues.
- `by-kind [--db PATH] [--json]`: status reason frequency per
  chunk kind, revealing whether certain content types are more
  prone to specific quality failures.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total and non-accepted counts, non-accepted rate, unique reasons,
  top reason, status breakdown, and affected source count.
- `selftest`: exercises 14 checks covering temporal entries,
  multi-month span, specific month accuracy, source entries,
  source coverage, per-source reasons, kind entries, kind totals,
  kind ordering, summary totals, non-accepted rate, unique reason
  count, JSON serialisation, and empty corpus.

### Design properties

- **Temporal bucketing**: month and week granularity reveals
  ingestion batch issues that flat counts hide.
- **Source correlation**: identifies sources that consistently
  produce non-accepted chunks, guiding extraction tuning.
- **Kind correlation**: reveals whether certain content types
  (code, config, tables) are disproportionately quarantined.
- **All non-accepted statuses**: analyses quarantined, superseded,
  and rejected chunks together, not just one status.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/status_reason_trends.py`: new tool
- `docs/specs/2026-08-31-corpus-status-reason-trends.md`: this spec

## See also

- [corpus-promote](2026-08-30-corpus-promote.md): manages chunk
  status transitions and flat reason counts; this tool analyses
  reason trends over time and by source.
- [corpus-quality-trend](2026-08-31-corpus-quality-trend.md):
  tracks quality metrics over time; this tool tracks specific
  failure reasons over time.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; status reason trends add a
  failure-pattern dimension.
- [corpus-ingestion-regression](2026-08-31-corpus-ingestion-regression.md):
  detects version-to-version regressions; this tool detects
  temporal patterns in quality failures.

## Non-goals

- Automated quarantine or rejection.
- Status reason taxonomy normalisation.
- Root cause analysis of individual failures.
- Alerting on reason spikes.
