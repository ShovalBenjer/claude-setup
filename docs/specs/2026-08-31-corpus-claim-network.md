# Corpus Claim Network Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/claim_network.py

## Problem

The claim_edges table records pairwise relationships between chunks
(contradicts, supports, supersedes, duplicates, refines), but no tool
analysed the network structure of these relationships.  Finding
connected groups of claims, identifying chunks that bridge separate
groups, or locating dense contradiction clusters all required manual
graph traversal.

## Solution

A new tool `tools/corpus/claim_network.py` with three subcommands:

- `components [--db PATH] [--json]`: finds connected components in the
  claim graph.  Reports each component's size, members, and edge type
  breakdown.
- `bridges [--db PATH] [--top N] [--json]`: identifies chunks with high
  degree or cross-component connections.  Reports degree, edge count,
  and number of components bridged.
- `clusters [--db PATH] [--min-size N] [--json]`: finds connected
  components in the contradiction-only subgraph (unresolved edges).
  Reports each cluster's size, members, contradiction count, and
  average confidence.
- `selftest`: exercises 14 checks covering all three subcommands,
  component detection, bridge degree, contradiction clustering,
  resolved-edge exclusion, superseded-chunk exclusion, empty corpus,
  and JSON serialisation.

### Design properties

- **Full edge type coverage**: components use all edge types;
  contradiction clusters filter to unresolved contradicts edges only.
- **Resolution aware**: contradiction clusters exclude resolved edges.
- **Superseded-chunk aware**: only active chunks participate.
- **Graceful degradation**: empty edge set returns empty results.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/claim_network.py`: new tool
- `docs/specs/2026-08-31-corpus-claim-network.md`: this spec

## See also

- [corpus-citation-graph](2026-08-31-corpus-citation-graph.md):
  per-chunk traversal of claim_edges; this tool analyses the network
  structure.
- [corpus-contradiction-detection](2026-08-30-corpus-contradiction-detection.md):
  detects contradictions; this tool clusters them into groups.
- [corpus-timeline](2026-08-31-corpus-timeline.md): temporal analysis;
  this tool analyses relational structure.

## Non-goals

- PageRank or centrality scoring (uses degree and component bridging).
- Automated resolution of contradictions.
- Visualization or graph rendering.
- Cross-corpus network comparison.
