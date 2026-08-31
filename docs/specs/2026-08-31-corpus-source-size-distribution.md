# Corpus Source Size Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_size_distribution.py

## Problem

The sources table records byte counts for each source, but no tool
analysed how those sizes distribute across the corpus.  Unusually
small sources may indicate truncated downloads or empty stubs, while
unusually large ones may signal unbounded extraction or duplicate
content.  Detecting these patterns required manual SQL queries
against the sources table.

## Solution

A new tool `tools/corpus/source_size_distribution.py` with four
subcommands:

- `histogram [--db PATH] [--json]`: five-bin histogram of source
  sizes (<1KB, 1-10KB, 10-100KB, 100KB-1MB, >1MB) with counts
  and share percentages.
- `per-kind [--db PATH] [--json]`: size statistics per source kind
  (mean, median, min, max, total, stddev), sorted by mean
  descending to surface the largest kinds first.
- `outliers [--db PATH] [--threshold F] [--json]`: sources whose
  byte count deviates beyond a configurable number of standard
  deviations from the corpus mean, with z-scores and direction
  labels.
- `summary [--db PATH] [--json]`: aggregate size statistics
  including total sources, total bytes, mean, median, range,
  standard deviation, and counts of tiny (<=1KB) and large (>1MB)
  sources.
- `selftest`: exercises 14 checks covering bin count, share sum,
  total count, tiny-bin membership, kind enumeration, mean
  ordering, mean-within-range, outlier detection, large-outlier
  direction, z-score sorting, summary totals, mean bounds, JSON
  serialisation, and empty corpus.

### Design properties

- **Fixed bins**: five size bands cover the practical range from
  sub-kilobyte stubs through multi-megabyte datasets, matching
  the ingestion pipeline's typical source sizes.
- **Per-kind breakdown**: reveals whether particular source kinds
  (papers, repos, datasets) cluster at different sizes, aiding
  ingestion threshold tuning.
- **Z-score outlier detection**: configurable threshold (default
  2.0 SD) surfaces sources that are statistically unusual without
  requiring domain-specific size limits.
- **Graceful degradation**: returns empty results when no sources
  have byte counts recorded.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_size_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-source-size-distribution.md`: this spec

## See also

- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates quality dimensions; source size outliers are a
  complementary data-quality signal.
- [corpus-word-count-distribution](2026-08-31-corpus-word-count-distribution.md):
  analyses chunk-level word counts; this tool analyses source-level
  byte counts.
- [corpus-ingestion-regression](2026-08-31-corpus-ingestion-regression.md):
  detects ingestion quality changes; truncated or oversized sources
  are an ingestion signal this tool can surface.
- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  analyses domain classifications; this tool analyses source
  size patterns that may correlate with domain coverage.
- [corpus-publisher-license-distribution](2026-08-31-corpus-publisher-license-distribution.md):
  analyses publisher and license metadata; this tool analyses
  source byte-count patterns.

## Non-goals

- Automatic source removal or quarantine based on size.
- Content-aware size analysis (compression ratios, deduplication).
- Cross-corpus size comparison.
- Size-based ingestion filtering.
