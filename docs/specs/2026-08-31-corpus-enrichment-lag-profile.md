# Corpus Enrichment Lag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/enrichment_lag_profile.py

## Problem

source_enrichment_completeness.py measures enrichment presence.
No tool measures the temporal lag between chunk ingestion and each
enrichment event, or which enrichment types and sources lag
furthest behind.

## Solution

A new tool `tools/corpus/enrichment_lag_profile.py` with four
subcommands:

- `by-type [--db PATH] [--json]`: average, minimum, and maximum
  enrichment lag per enrichment type (tagging, classification,
  versioning, edge detection), measured in seconds from ingestion.
- `by-source [--db PATH] [--json]`: average enrichment lag per
  source, aggregated across all enrichment types.
- `outliers [--db PATH] [--json]`: enrichment events with lag
  exceeding 24 hours, listing chunk, type, and timestamps.
- `summary [--db PATH] [--json]`: aggregate statistics including
  types measured, total events, weighted average lag, slowest type,
  slowest source, and outlier count.
- `selftest`: exercises 14 checks covering per-type lag computation,
  per-source aggregation, outlier detection at two thresholds,
  summary totals, JSON serialisation, and empty corpus.

### Design properties

- **Julian day arithmetic**: computes lag using SQLite julianday
  difference multiplied by 86400, yielding seconds with sub-second
  precision.
- **First-version semantics**: versioning lag uses only the first
  version snapshot (version_num = 1), measuring time to initial
  version capture rather than subsequent revisions.
- **Outlier detection**: configurable threshold (default 24h) flags
  enrichment events that lag behind ingestion by more than the
  threshold.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/enrichment_lag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-enrichment-lag-profile.md`: this spec

## See also

- [corpus-source-enrichment-completeness](2026-08-31-corpus-source-enrichment-completeness.md):
  measures enrichment presence; this tool measures enrichment timing.
- [corpus-version-source-profile](2026-08-31-corpus-version-source-profile.md):
  measures revision activity per source; this tool measures time to
  first enrichment.

## Non-goals

- Enrichment scheduling or queue management.
- Lag-based alerting or SLA enforcement.
- Causal analysis of why enrichment is slow.
- Cross-enrichment-type dependency tracking.
