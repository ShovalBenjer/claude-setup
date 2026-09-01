# Corpus Publisher and License Distribution

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_license_distribution.py

## Problem

The sources table stores publisher and license_spdx columns, but no
tool analysed their distributions.  Understanding which publishers
contribute the most sources, how concentrated the corpus is across
publishers, and which license types dominate required manual SQL.
The existing license_gate.py validates individual sources at
ingestion but does not report corpus-wide license patterns.

## Solution

A new tool `tools/corpus/publisher_license_distribution.py` with
four subcommands:

- `publishers [--db PATH] [--top N] [--json]`: publishers ranked by
  source count, showing share of total, cumulative bytes, and kind
  diversity.  Null publishers appear as "(unknown)".
- `licenses [--db PATH] [--json]`: license type distribution grouped
  by SPDX identifier and verdict, with source counts, share, and
  total bytes per combination.
- `cross-tab [--db PATH] [--json]`: publisher-license cross-
  tabulation showing which publishers use which licenses, sorted by
  frequency.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total sources, distinct publisher/license/verdict counts, unknown
  publisher count, Gini coefficient for publisher concentration, and
  top publisher and license by frequency.
- `selftest`: exercises 14 checks covering publisher ranking, share
  summation, unknown publisher detection, license distribution, cross-
  tabulation accuracy, summary totals, Gini bounds, JSON
  serialisation, and empty corpus.

### Design properties

- **Gini coefficient**: measures publisher concentration on a 0-1
  scale, where 0 means perfectly even distribution and values near
  1 indicate a single dominant publisher.
- **Cross-tabulation**: reveals publisher-license affinities that
  single-dimension breakdowns miss.
- **Unknown tracking**: null publishers are counted explicitly to
  surface metadata gaps.
- **Verdict pairing**: license breakdown groups by both SPDX
  identifier and verdict, since the same SPDX string can carry
  different access verdicts.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_license_distribution.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-license-distribution.md`: this spec

## See also

- [corpus-source-size-distribution](2026-08-31-corpus-source-size-distribution.md):
  analyses source byte-count patterns; this tool analyses source
  metadata dimensions (publisher, license).
- [corpus-domain-analysis](2026-08-30-corpus-domain-analysis.md):
  analyses domain coverage across sources; publisher distribution
  is a complementary source diversity dimension.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus health metrics; publisher concentration and
  license diversity are complementary quality signals.
- [corpus-source-provenance](2026-08-31-corpus-source-provenance.md):
  scores individual source provenance including license verdict;
  this tool analyses the aggregate license distribution.

## Non-goals

- License compatibility checking or conflict detection.
- Publisher normalisation or deduplication.
- Temporal trend analysis of publisher/license changes.
- License text retrieval or SPDX validation.
