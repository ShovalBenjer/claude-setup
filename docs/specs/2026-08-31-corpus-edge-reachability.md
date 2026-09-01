# Corpus Edge Reachability

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_reachability.py

## Problem

citation_graph.py computes degree and authority scores.  claim_network.py
computes connected components and bridges.  No tool computes multi-hop
paths between chunks or the diameter of the claim graph.  Understanding
how many hops separate two chunks, or what the longest shortest-path is,
required manual BFS traversal.

## Solution

A new tool `tools/corpus/edge_reachability.py` with four subcommands:

- `diameter [--db PATH] [--json]`: longest shortest-path in the claim
  graph, with endpoints and node count.
- `path <src> <tgt> [--db PATH] [--json]`: shortest path between two
  chunks with hop count and the full path.
- `hop-distribution [--db PATH] [--json]`: distribution of pairwise
  shortest-path distances with pair counts and rates.
- `summary [--db PATH] [--json]`: aggregate reachability statistics
  including connected components, diameter, mean hops, and
  reachable/unreachable pair counts.
- `selftest`: exercises 14 checks covering diameter computation,
  shortest path correctness, unreachable pair detection, hop
  distribution counts, rate summation, component counting, summary
  totals, JSON serialisation, and empty corpus.

### Design properties

- **Undirected adjacency**: builds an undirected adjacency list from
  claim_edges, since reachability in the claim graph is symmetric.
- **BFS traversal**: standard breadth-first search for shortest paths
  and distance computation, guaranteeing optimal hop counts.
- **Pair deduplication**: hop distribution counts each unordered pair
  once, avoiding double-counting.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_reachability.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-reachability.md`: this spec

## See also

- [corpus-claim-network](2026-08-31-corpus-claim-network.md):
  computes connected components and bridges; this tool adds multi-hop
  path analysis and diameter computation.
- [corpus-citation-graph](2026-08-31-corpus-citation-graph.md):
  computes degree and authority scores; this tool measures how far
  apart chunks are in the claim graph.

## Non-goals

- Directed path analysis or asymmetric reachability.
- Weighted shortest paths using edge confidence.
- Path enumeration beyond a single shortest path.
- Dynamic graph updates or incremental recomputation.
