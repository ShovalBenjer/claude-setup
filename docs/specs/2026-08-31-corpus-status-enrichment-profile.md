# Corpus Status Enrichment Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/status_enrichment_profile.py

## Problem

source_enrichment_completeness.py measures enrichment per source.
cross_table_outlier_detector.py finds statistical anomalies.
No tool measures whether accepted chunks carry richer enrichment
than quarantined or rejected chunks, how each enrichment type
distributes across statuses, or which accepted chunks still have
enrichment gaps.

## Solution

A new tool `tools/corpus/status_enrichment_profile.py` with four
subcommands:

- `by-status [--db PATH] [--json]`: enrichment depth per chunk
  status across five dimensions (tags, domains, citations, edges,
  artifacts), with an enrichment rate per status.
- `by-type [--db PATH] [--json]`: per-enrichment-type record
  counts broken down by chunk status, showing where enrichment
  activity concentrates.
- `gaps [--db PATH] [--json]`: chunks missing at least one
  enrichment dimension, grouped by status, with per-chunk flags
  showing which dimensions are present and a dimensions-hit count.
- `summary [--db PATH] [--json]`: aggregate statistics including
  accepted chunk counts, accepted tagged and classified counts,
  accepted chunks with gaps, and gap rate.
- `selftest`: exercises 14 checks covering per-status enrichment,
  type-by-status counts, gap detection, dimension flags, summary
  totals, JSON serialisation, and empty corpus.

### Design properties

- **Five-dimension enrichment model**: measures tags, domains,
  citations, edges, and artifacts as the five enrichment
  dimensions, consistent with source_enrichment_completeness.
- **Status-aware gap detection**: identifies which accepted chunks
  still lack enrichment, prioritising gaps in searchable content
  over gaps in quarantined content.
- **Subquery isolation**: uses separate subqueries per enrichment
  dimension joined on status, avoiding row multiplication from
  multi-table joins.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/status_enrichment_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-status-enrichment-profile.md`: this spec

## See also

- [corpus-source-enrichment-completeness](2026-08-31-corpus-source-enrichment-completeness.md):
  measures enrichment per source; this tool measures enrichment
  per chunk status.
- [corpus-cross-table-outlier-detector](2026-08-31-corpus-cross-table-outlier-detector.md):
  finds statistical anomalies; this tool finds enrichment gaps
  stratified by status.

## Non-goals

- Automated enrichment triggering based on gaps.
- Status transition analysis or promotion workflows.
- Enrichment quality scoring beyond presence or absence.
- Cross-source status comparison.
