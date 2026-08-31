# Corpus Version Timeline

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_timeline.py

## Problem

The chunk_versions.snapshot_utc column had no temporal distribution
analysis.  No tool examined when version snapshots are taken, how
versioning activity varies over time, or the relationship between
version depth and snapshot timing.

## Solution

A new tool `tools/corpus/version_timeline.py` with four subcommands:

- `timeline [--db PATH] [--json]`: distribution of version snapshot
  times by month, with count and share per month.
- `depth [--db PATH] [--json]`: distribution of max version depth
  per chunk, bucketed into 1, 2-3, 4-5, 6-10, >10.
- `churn [--db PATH] [--json]`: version churn per month showing
  total versions created and distinct chunks versioned, revealing
  whether versioning is concentrated or spread across the corpus.
- `summary [--db PATH] [--json]`: aggregate version statistics
  including total versions, distinct chunks, distinct months,
  snapshot range, mean versions per chunk, and max version depth.
- `selftest`: exercises 14 checks covering timeline entry count,
  monthly counts, share summation, depth distribution entries,
  bucket counts, churn entries, churn distinct chunks, churn
  version counts, summary totals, mean versions per chunk, JSON
  serialisation, and empty corpus.

### Design properties

- **Monthly granularity**: snapshot times grouped by month reveal
  whether versioning happens in bursts or at a steady pace.
- **Depth bucketing**: version depth distribution reveals how many
  chunks accumulate many revisions versus staying at version 1.
- **Churn measurement**: distinct chunks per month measures whether
  versioning concentrates on a few chunks or spreads broadly.
- **Non-base-schema awareness**: the selftest creates the
  chunk_versions table with CREATE TABLE IF NOT EXISTS since it is
  not part of the base init_schema.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_timeline.py`: new tool
- `docs/specs/2026-08-31-corpus-version-timeline.md`: this spec

## See also

- [corpus-temporal-distribution](2026-08-31-corpus-temporal-distribution.md):
  analyses ingestion, publication, and fetch timestamps; this tool
  analyses the version snapshot timestamp.
- [corpus-chunk-position-analysis](2026-08-31-corpus-chunk-position-analysis.md):
  analyses chunk ordinal patterns; this tool analyses how chunks
  evolve through versions over time.

## Non-goals

- Automatic version pruning or cleanup scheduling.
- Version diff or content comparison between snapshots.
- Version quality assessment or regression detection.
- Snapshot frequency recommendation or optimisation.
