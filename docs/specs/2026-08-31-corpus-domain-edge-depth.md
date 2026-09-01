# Corpus Domain Edge Depth

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/domain_edge_depth.py

## Problem

tag_edge_correlation.py correlates tags with claim_edges.
domain_citation_profile.py correlates domains with citations.
No tool joins chunk_domains with claim_edges to measure which
knowledge domains have the highest edge connectivity, or which
edge types dominate each domain's claim graph.

## Solution

A new tool `tools/corpus/domain_edge_depth.py` with four
subcommands:

- `by-domain [--db PATH] [--json]`: edge density per domain with
  classified chunk count, total edges, edges-per-chunk rate, and
  average domain score.
- `by-edge-type [--db PATH] [--json]`: domain distribution per edge
  type with distinct domain count, edge count, and classified
  endpoint count.
- `cross [--db PATH] [--json]`: full domain by edge_type
  cross-tabulation with counts.
- `summary [--db PATH] [--json]`: aggregate statistics including
  classified-with-edges count, edge coverage rate, classified edge
  share, and densest domain.
- `selftest`: exercises 14 checks covering per-domain edge density,
  domain exclusion (no edges), per-edge-type distribution,
  cross-tabulation, summary totals, edge share, JSON serialisation,
  and empty corpus.

### Design properties

- **Domain-edge join**: joins chunk_domains with claim_edges on both
  source_chunk and target_chunk, capturing edges where either
  endpoint is classified into the domain.
- **Bidirectional matching**: a domain classification on a chunk
  counts for all edges that touch that chunk as source or target.
- **Edge type stratification**: breaks down domain-edge correlation
  by edge type, surfacing whether domains are dominated by
  supportive, contradictory, or refinement relationships.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/domain_edge_depth.py`: new tool
- `docs/specs/2026-08-31-corpus-domain-edge-depth.md`: this spec

## See also

- [corpus-tag-edge-correlation](2026-08-31-corpus-tag-edge-correlation.md):
  correlates tags with edges; this tool correlates domains with edges.
- [corpus-domain-citation-profile](2026-08-31-corpus-domain-citation-profile.md):
  correlates domains with citations; this tool correlates domains
  with edges.

## Non-goals

- Domain-level graph diameter or path analysis.
- Cross-domain edge flow measurement.
- Edge confidence adjustment by domain.
- Domain hierarchy or taxonomy analysis.
