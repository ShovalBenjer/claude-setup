# Corpus Version Source Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_source_profile.py

## Problem

version_edge_impact.py joins chunk_versions with claim_edges.
version_citation_drift.py joins chunk_versions with citations.
version_tag_stability.py joins chunk_versions with chunk_tags.
No tool joins chunk_versions with sources to show which sources
have the most revision activity, or which source kinds accumulate
the most churn.

## Solution

A new tool `tools/corpus/version_source_profile.py` with four
subcommands:

- `by-source [--db PATH] [--json]`: revision density per source
  with total chunks, revised chunks, total revisions,
  revisions-per-chunk rate, and maximum version depth.
- `by-kind [--db PATH] [--json]`: revision activity aggregated
  by source kind with source count, chunk count, and revision rate.
- `top-churners [--db PATH] [--json]`: sources with highest revision
  churn, filtered to sources with at least two revised chunks.
- `summary [--db PATH] [--json]`: aggregate statistics including
  sources with revisions, revision coverage rate, total revisions,
  revised chunks, and most revised source.
- `selftest`: exercises 14 checks covering per-source revision
  counts, revised chunk counts, source exclusion (no revisions),
  max depth, per-kind aggregation, top-churner filtering, summary
  totals, coverage rate, JSON serialisation, and empty corpus.

### Design properties

- **Source-version join**: joins sources through chunks to
  chunk_versions, aggregating revision counts at the source level.
- **Kind stratification**: groups revision activity by source kind,
  surfacing whether local_md, repo, or other kinds drive churn.
- **Churn ranking**: the top-churners subcommand uses an INNER JOIN
  on chunk_versions and filters to sources with at least two revised
  chunks, isolating genuinely active sources.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_source_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-version-source-profile.md`: this spec

## See also

- [corpus-version-edge-impact](2026-08-31-corpus-version-edge-impact.md):
  joins chunk_versions with claim_edges.
- [corpus-version-citation-drift](2026-08-31-corpus-version-citation-drift.md):
  joins chunk_versions with citations.
- [corpus-version-tag-stability](2026-08-31-corpus-version-tag-stability.md):
  joins chunk_versions with chunk_tags.

## Non-goals

- Source quality scoring by revision pattern.
- Temporal revision trend analysis.
- Cross-source revision correlation.
- Revision diffing or content change analysis.
