# Corpus Version Edge Impact

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_edge_impact.py

## Problem

chunk_versions tracks content revisions. claim_edges records
relationships between chunks with detection timestamps. No tool
cross-references these two tables to find edges whose endpoint
content changed after the edge was detected, leaving potentially
stale relationship claims undetected.

## Solution

A new tool `tools/corpus/version_edge_impact.py` with four
subcommands:

- `stale [--db PATH] [--json]`: edges where at least one endpoint
  has a chunk_version with snapshot_utc after the edge's detected_utc,
  with revision counts and latest revision timestamps for each endpoint.
- `by-type [--db PATH] [--json]`: per edge_type statistics with total
  edges, stale count, and staleness rate.
- `by-depth [--db PATH] [--json]`: stale edges bucketed by maximum
  endpoint version depth, showing which revision depths carry the most
  stale edges.
- `summary [--db PATH] [--json]`: aggregate statistics including
  stale rate, both-revised/source-only/target-only breakdown, most
  stale edge type, and versioned chunk count.
- `selftest`: exercises 14 checks covering stale edge detection,
  non-stale exclusion, edge-type breakdown, version-depth bucketing,
  summary totals, revision-side classification, JSON serialisation,
  and empty corpus.

### Design properties

- **Temporal join**: joins chunk_versions on both source_chunk and
  target_chunk of each edge, comparing snapshot_utc against
  detected_utc to identify post-detection revisions.
- **Revision-side classification**: categorises each stale edge as
  both_revised, source_only, or target_only based on which endpoints
  were revised after edge detection.
- **Version depth bucketing**: groups stale edges by the maximum
  version count across their endpoints, surfacing whether deeply
  revised chunks accumulate more stale edges.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_edge_impact.py`: new tool
- `docs/specs/2026-08-31-corpus-version-edge-impact.md`: this spec

## See also

- [corpus-edge-reachability](2026-08-31-corpus-edge-reachability.md):
  computes multi-hop paths in the claim graph; this tool checks whether
  edges in that graph are stale due to content revisions.
- [corpus-evidence-chain-audit](2026-08-31-corpus-evidence-chain-audit.md):
  audits provenance chains from source through chunk; this tool audits
  temporal validity of edges relative to chunk versions.

## Non-goals

- Automatic edge invalidation or re-detection.
- Version diff content comparison.
- Edge confidence adjustment based on revision count.
- Cascade analysis across transitive edge chains.
