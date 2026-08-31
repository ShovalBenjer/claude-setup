# Corpus Citation Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_edge_profile.py

## Problem

citation_tag_profile.py profiles citation buckets by chunk tags.
domain_edge_profile.py profiles domains by claim edges.
No tool cross-tabulates chunks.citation_count with claim_edges to measure
whether highly cited chunks carry more claim edges, or how edge types
distribute across citation buckets.

## Solution

A new tool `tools/corpus/citation_edge_profile.py` with four subcommands:

- `by-bucket [--db PATH] [--json]`: edge statistics per citation bucket
  (0, 1-5, 6-20, 21+), showing chunks with edges, total edges, edge
  types, and edges per chunk.
- `by-type [--db PATH] [--json]`: citation bucket distribution per edge
  type, showing distinct buckets, chunks involved, and edge count.
- `concentration [--db PATH] [--json]`: per-bucket edge concentration
  ordered by edges per chunk to surface citation ranges with the
  densest argumentative structure.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  chunks, chunks with edges, total edges, cited chunks with edges,
  cited chunks total, cited edge rate, and total citations.
- `selftest`: exercises 14 checks covering per-bucket edge counts,
  per-type bucket distribution, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Citation bucketing**: uses the standard bucket scheme (0, 1-5, 6-20,
  21+) to group chunks by citation density before measuring edge
  participation.
- **Citation-edge correlation**: reveals whether highly cited chunks also
  carry more claim edges, testing the hypothesis that citation density
  correlates with argumentative density.
- **Edge type spread**: by-type view shows whether certain edge types
  concentrate in particular citation ranges.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-edge-profile.md`: this spec

## See also

- [corpus-citation-tag-profile](2026-08-31-corpus-citation-tag-profile.md):
  profiles citation buckets by chunk tags; this tool profiles citation
  buckets by claim edges.
- [corpus-domain-edge-profile](2026-08-31-corpus-domain-edge-profile.md):
  profiles domains by claim edges; this tool uses citation buckets
  instead.

## Non-goals

- Automatic edge prediction from citation counts.
- Citation count normalization by edge density.
- Cross-bucket edge merging or deduplication.
- Edge weight adjustment from citation counts.
