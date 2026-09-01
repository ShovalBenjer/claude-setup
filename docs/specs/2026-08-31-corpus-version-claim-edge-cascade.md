# Corpus Version Claim Edge Cascade

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/version_claim_edge_cascade.py

## Problem

version_source_profile.py measures revision activity per source.
fts_edge_reachability.py measures edge density relative to word count.
No tool measures whether heavily-revised chunks attract more edges,
how edge types distribute across version depths, or whether edges
connect chunks at similar or different revision counts.

## Solution

A new tool `tools/corpus/version_claim_edge_cascade.py` with four
subcommands:

- `by-depth [--db PATH] [--json]`: edge counts grouped by source
  chunk version depth, showing how many edges originate from chunks
  at each revision level.
- `edge-type-depth [--db PATH] [--json]`: edge type distribution
  across source chunk version depths, with average confidence per
  type-depth combination.
- `depth-pairs [--db PATH] [--json]`: edge counts by source-target
  version depth pairs, showing whether edges connect chunks at
  similar or different revision levels, with a same-depth flag.
- `summary [--db PATH] [--json]`: aggregate statistics including
  edges from versioned and unversioned chunks, edges where both
  endpoints are versioned, maximum depth, and average source
  version depth.
- `selftest`: exercises 14 checks covering per-depth edge counts,
  edge type at depth, depth pair analysis, same-depth flags,
  summary totals, JSON serialisation, and empty corpus.

### Design properties

- **Version depth as MAX(version_num)**: uses the highest version
  number per chunk as its depth, treating version_num as a
  monotonically increasing revision counter.
- **Unversioned as depth zero**: chunks with no entries in
  chunk_versions default to depth 0, keeping them visible in the
  analysis rather than excluded.
- **Depth pair symmetry**: source-target depth pairs are not
  collapsed (3,1 differs from 1,3), preserving directionality
  of the edge relationship.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/version_claim_edge_cascade.py`: new tool
- `docs/specs/2026-08-31-corpus-version-claim-edge-cascade.md`: this spec

## See also

- [corpus-version-source-profile](2026-08-31-corpus-version-source-profile.md):
  measures revision activity per source; this tool measures how
  revisions relate to edge formation.
- [corpus-fts-edge-reachability](2026-08-31-corpus-fts-edge-reachability.md):
  measures edge density relative to word count; this tool measures
  edge density relative to version depth.

## Non-goals

- Causal analysis of whether revisions trigger edge creation.
- Temporal ordering of version and edge events.
- Edge prediction based on version patterns.
- Version-weighted edge confidence adjustment.
