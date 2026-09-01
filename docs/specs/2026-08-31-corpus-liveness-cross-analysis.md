# Corpus Liveness Cross-Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/liveness_cross_analysis.py

## Problem

The sources table stores a liveness column (live, stale, archived,
dead) that indicates each source's current availability status.
Existing tools only performed flat GROUP BY on liveness alone,
producing a simple count per status.  No tool cross-tabulated
liveness against source kind, publisher, or license to reveal which
dimensions correlate with staleness or archival.  Finding whether
certain publishers have higher dead-source rates or whether specific
source kinds tend toward staleness required manual multi-column
queries.

## Solution

A new tool `tools/corpus/liveness_cross_analysis.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: liveness distribution per source
  kind, showing live count, live rate, and full liveness breakdown.
  Sorted by live rate ascending to surface the least healthy kinds
  first.
- `by-publisher [--db PATH] [--json]`: liveness distribution per
  publisher with live count and rate.  Sorted by source count
  descending.
- `by-license [--db PATH] [--json]`: liveness distribution per
  license with live count and rate.  Sorted by source count
  descending.
- `summary [--db PATH] [--json]`: aggregate cross-analysis
  statistics including total sources, liveness counts, overall live
  rate, count of kinds and publishers with non-live sources, and
  byte totals for live versus non-live sources.
- `selftest`: exercises 14 checks covering by-kind entries, per-kind
  counts, liveness breakdowns, sort order, by-publisher entries,
  publisher live counts, by-license entries, license breakdowns,
  summary totals, non-live byte counts, JSON serialisation, and
  empty corpus.

### Design properties

- **Worst-first sorting**: by-kind results are sorted by live rate
  ascending, surfacing the most problematic source kinds first.
- **Byte-level impact**: summary reports total bytes in live versus
  non-live sources, quantifying the data volume at risk.
- **Publisher accountability**: per-publisher breakdown reveals which
  content providers have the highest non-live rates.
- **All-source scope**: analyses all sources regardless of chunk
  status, since liveness is a source-level property.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/liveness_cross_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-liveness-cross-analysis.md`: this spec

## See also

- [corpus-source-lifecycle](2026-08-31-corpus-source-lifecycle.md):
  analyses liveness transitions as flat counts; this tool
  cross-tabulates liveness against other dimensions.
- [corpus-upstream-provenance](2026-08-31-corpus-upstream-provenance.md):
  analyses upstream timestamps that drive liveness decisions; this
  tool analyses the resulting liveness status across dimensions.
- [corpus-publisher-license-distribution](2026-08-31-corpus-publisher-license-distribution.md):
  analyses publisher and license metadata; this tool adds the
  liveness dimension to those same categories.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates corpus quality metrics; liveness patterns are a
  complementary availability signal.

## Non-goals

- Automatic liveness reclassification or staleness resolution.
- Source availability checking or link validation.
- Liveness-based source filtering or removal.
- Temporal liveness trend analysis.
