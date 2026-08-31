# Corpus Freshness Scorer

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/freshness_scorer.py

## Problem

Each chunk carries temporal signals across multiple tables: ingestion
timestamps in chunks, source liveness in sources, version snapshots in
chunk_versions, and aggregate quality trends in quality_snapshots.  No
tool correlated these signals into a single per-chunk freshness score.
Identifying stale knowledge required manually cross-referencing dates,
liveness states, and version histories.

## Solution

A new tool `tools/corpus/freshness_scorer.py` with three subcommands:

- `score [--db PATH] [--top N] [--json]`: per-chunk freshness scores
  ranked highest first.  Each result includes the freshness score
  (0 to 1), age in days, source liveness, and whether the chunk has
  version tracking.  The `--top N` flag limits output to the N
  freshest chunks.
- `stale [--db PATH] [--threshold F] [--json]`: chunks with freshness
  below a configurable threshold (default 0.4).  Surfaces knowledge
  that needs review or re-ingestion.
- `summary [--db PATH] [--json]`: aggregate freshness statistics
  including average, min, max, stale and fresh counts, and a
  five-band histogram.
- `selftest`: exercises 14 checks covering superseded exclusion,
  score ordering, value bounds, sort order, version flag, age
  calculation, liveness propagation, stale filtering, summary
  structure, band totals, JSON serialisation, and empty corpus.

### Freshness formula

The per-chunk freshness score is a weighted combination of four signals:

1. **age_score (0.3)**: exponential decay from ingested_utc with a
   180-day half-life.  A chunk ingested today scores 1.0; one
   ingested 180 days ago scores 0.5.
2. **liveness_score (0.3)**: source liveness mapped to numeric
   values (live=1.0, stale=0.5, archived=0.25, dead=0.0).
3. **version_score (0.2)**: exponential decay from the most recent
   version snapshot (90-day half-life).  Chunks without version
   tracking use half of their age_score as a pessimistic estimate.
4. **trend_score (0.2)**: corpus-wide quality trend from the three
   most recent quality_snapshots.  Rising trends push toward 1.0,
   falling trends toward 0.0, neutral holds at 0.5.

### Design properties

- **Multi-table correlation**: combines chunks.ingested_utc,
  sources.liveness, chunk_versions.snapshot_utc, and
  quality_snapshots.mean_score into a single metric.
- **Exponential decay**: uses half-life-based decay rather than
  linear cutoffs, giving smooth degradation without hard boundaries.
- **Configurable staleness**: the stale subcommand accepts a
  threshold parameter for different freshness requirements.
- **Graceful degradation**: works without chunk_versions or
  quality_snapshots tables, falling back to available signals.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/freshness_scorer.py`: new tool
- `docs/specs/2026-08-31-corpus-freshness-scorer.md`: this spec

## See also

- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates all signal tables into quality scores; this tool provides
  the temporal freshness dimension that the scorecard does not cover.
- [corpus-chunk-versions](2026-08-30-corpus-chunk-versions.md):
  the versioning infrastructure whose snapshots feed version_score.
- [corpus-quality-trend](2026-08-30-corpus-quality-trend.md):
  the quality trend tracker whose snapshots feed trend_score.
- [corpus-claim-consensus](2026-08-31-corpus-claim-consensus.md):
  cross-source claim agreement; this tool measures temporal freshness
  while that tool measures inter-source consensus.

## Non-goals

- Automatic re-ingestion or refresh scheduling.
- Per-source freshness aggregation (use health_scorecard).
- Freshness-weighted search ranking.
- Historical freshness tracking over time.
