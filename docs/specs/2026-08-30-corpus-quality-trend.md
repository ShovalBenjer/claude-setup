# Corpus Quality Trend

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/quality_trend.py

## Problem

The quality scorer (`tools/corpus/quality.py`) computes per-chunk and
per-source quality metrics at a single point in time.  There was no way
to track how aggregate quality evolves across ingestion cycles, corpus
edits, or deduplication passes.  A declining mean score after a bulk
import, or a rising p90 after curating high-citation sources, was
invisible without manual re-runs and comparison.

## Solution

A new tool `tools/corpus/quality_trend.py` that records aggregate
quality metric snapshots into a `quality_snapshots` table.

### Schema (created dynamically via `_ensure_table`)

```sql
CREATE TABLE IF NOT EXISTS quality_snapshots (
    snapshot_id    TEXT PRIMARY KEY,
    snapshot_utc   TEXT NOT NULL,
    chunk_count    INTEGER NOT NULL,
    mean_score     REAL NOT NULL,
    median_score   REAL NOT NULL,
    p10_score      REAL NOT NULL,
    p90_score      REAL NOT NULL,
    below_050      INTEGER NOT NULL,
    above_080      INTEGER NOT NULL,
    distribution   TEXT NOT NULL
);
```

### Tool commands

- `snapshot [--db PATH] [--dry-run]`: computes quality scores for all
  non-superseded chunks using `quality.py`'s `_chunk_quality()`, then
  stores aggregate statistics (mean, median, p10, p90, distribution
  histogram with 10 buckets, counts below 0.5 and above 0.8).
- `history [--db PATH] [--limit N] [--json]`: returns snapshots newest
  first with all stored metrics and the distribution histogram.
- `trend [--db PATH] [--json]`: computes overall direction (improving,
  declining, or stable) from the mean score delta between the first
  and most recent snapshots.  Returns `no_data` when no snapshots
  exist, `single_point` when only one has been taken.
- `selftest`: exercises 14 checks covering dry run, snapshot
  persistence, history ordering, distribution bucket sums, percentile
  ordering, trend computation, empty corpus, score bounds, primary key
  uniqueness, and superseded chunk exclusion.

### Design properties

- **Reuses quality.py scoring**: does not redefine quality signals;
  calls `_chunk_quality()` with the same five weighted dimensions.
- **Aggregate only**: stores summary statistics, not per-chunk scores,
  keeping the table small regardless of corpus size.
- **Deterministic snapshot ID**: SHA-256 of timestamp, chunk count,
  and mean score prevents accidental duplicates.
- **10-bucket histogram**: the `distribution` column stores a JSON
  array of 10 buckets (0.0--0.1, 0.1--0.2, ..., 0.9--1.0), giving
  shape information beyond percentiles.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/quality_trend.py`: new tool
- `docs/specs/2026-08-30-corpus-quality-trend.md`: this spec

## See also

- [corpus-quality](2026-08-30-corpus-quality.md): the scorer whose
  `_chunk_quality()` this tool aggregates over time.

## Non-goals

- Per-chunk score history (only aggregates are stored).
- Automatic alerting on quality regression.
- Score decomposition by signal (mean is across the composite score).
