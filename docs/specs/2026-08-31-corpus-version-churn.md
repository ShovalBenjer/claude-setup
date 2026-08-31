# Corpus Version Churn Rate

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_churn.py

## Problem

The chunk evolution tool counts revisions per chunk, but no tool
measured the temporal velocity of those changes.  A corpus with
steady monthly revisions behaves differently from one with bursts
of activity followed by quiet periods.  Identifying churn hotspots
and trend direction required manually grouping version timestamps
by period and computing rates.

## Solution

A new tool `tools/corpus/version_churn.py` with three subcommands:

- `rate [--db PATH] [--json]`: per-month revision counts with
  month-over-month delta and trend direction (accelerating, stable,
  or decelerating).  Sorted chronologically.
- `hotspots [--db PATH] [--top N] [--json]`: chunks with the
  highest churn rate measured as revisions per day of active life.
  Only multi-revision chunks qualify.  Sorted by churn rate
  descending to surface the most volatile content first.
- `summary [--db PATH] [--json]`: aggregate churn statistics
  including total revisions, versioned and multi-revision chunk
  counts, months active, mean monthly revisions, peak month, and
  latest trend direction.
- `selftest`: exercises 14 checks covering monthly enumeration,
  chronological sort, positive revisions, delta correctness, trend
  validity, hotspot detection, revision counts, positive rates,
  rate ordering, single-revision exclusion, summary structure,
  peak identification, JSON serialisation, and empty corpus.

### Churn metrics

Two complementary views of revision velocity:

1. **Monthly rate**: aggregates revision timestamps by calendar
   month, computing the month-over-month delta and labelling the
   trend as accelerating (delta > 0), decelerating (delta < 0),
   or stable (delta = 0).
2. **Per-chunk churn rate**: revisions divided by the span in days
   between first and last version snapshot.  High rates indicate
   content that changes frequently relative to its age.

### Design properties

- **Graceful degradation**: works without the chunk_versions table,
  returning empty results rather than failing.
- **Accepted-only hotspots**: joins through chunks to filter
  hotspots to accepted content only.
- **Single-revision exclusion**: hotspots require at least two
  revisions, since a single snapshot has no meaningful churn rate.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_churn.py`: new tool
- `docs/specs/2026-08-31-corpus-version-churn.md`: this spec

## See also

- [corpus-chunk-evolution](2026-08-31-corpus-chunk-evolution.md):
  counts revisions and measures content drift; this tool measures
  the temporal velocity and acceleration of those revisions.
- [corpus-chunk-versions](2026-08-30-corpus-chunk-versions.md):
  the versioning infrastructure whose snapshots feed churn analysis.
- [corpus-ingestion-regression](2026-08-31-corpus-ingestion-regression.md):
  detects quality regressions between versions; this tool measures
  revision frequency patterns.
- [corpus-freshness-scorer](2026-08-31-corpus-freshness-scorer.md):
  scores chunk freshness from timestamps; this tool measures how
  actively content is being revised.
- [corpus-timeline](2026-08-31-corpus-timeline.md):
  tracks ingestion velocity over time; this tool tracks revision
  velocity over time.

## Non-goals

- Content diffing between version snapshots.
- Churn prediction or forecasting.
- Automated response to high churn.
- Per-source churn aggregation.
