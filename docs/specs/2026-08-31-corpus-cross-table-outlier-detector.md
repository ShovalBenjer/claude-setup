# Corpus Cross-Table Outlier Detector

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/cross_table_outlier_detector.py

## Problem

source_enrichment_completeness.py measures enrichment coverage.
enrichment_lag_profile.py measures enrichment timing.
No tool detects statistical outliers that span multiple tables,
such as chunks with extreme word counts relative to their source,
edges whose confidence deviates from their type mean, or citations
concentrated in a narrow band of chunks within a source.

## Solution

A new tool `tools/corpus/cross_table_outlier_detector.py` with four
subcommands:

- `chunk-words [--db PATH] [--json]`: chunks whose word count
  deviates more than 2 standard deviations from their source mean,
  with z-score for each outlier.
- `edge-confidence [--db PATH] [--json]`: edges whose confidence
  deviates more than 2 standard deviations from their edge type
  mean, flagging suspiciously high or low confidence values.
- `citation-concentration [--db PATH] [--json]`: sources where
  citations concentrate in a small fraction of chunks, with
  cited fraction and citations-per-cited-chunk metrics.
- `summary [--db PATH] [--json]`: aggregate statistics including
  outlier counts, corpus-wide word count and confidence means
  and standard deviations, and highly concentrated source count.
- `selftest`: exercises 14 checks covering word count outlier
  detection, z-score thresholds, identical-word-count exclusion,
  edge confidence outliers, citation concentration metrics,
  summary totals, JSON serialisation, and empty corpus.

### Design properties

- **Per-group z-scores**: computes standard deviation within each
  group (source for word counts, edge type for confidence) rather
  than corpus-wide, so outliers are relative to their peers.
- **Sample standard deviation**: uses n-1 denominator for unbiased
  estimation, and skips groups with zero variance (all identical
  values cannot produce outliers).
- **Minimum group size**: requires at least 2 chunks per source
  before computing word count outliers, avoiding false positives
  from single-chunk sources.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/cross_table_outlier_detector.py`: new tool
- `docs/specs/2026-08-31-corpus-cross-table-outlier-detector.md`: this spec

## See also

- [corpus-source-enrichment-completeness](2026-08-31-corpus-source-enrichment-completeness.md):
  measures enrichment coverage; this tool detects statistical
  anomalies across enrichment tables.
- [corpus-enrichment-lag-profile](2026-08-31-corpus-enrichment-lag-profile.md):
  measures enrichment timing; this tool detects outlier values
  rather than timing anomalies.

## Non-goals

- Automated outlier remediation or quarantine.
- Machine-learning-based anomaly detection.
- Time-series anomaly detection across versions.
- Alerting or notification on new outliers.
