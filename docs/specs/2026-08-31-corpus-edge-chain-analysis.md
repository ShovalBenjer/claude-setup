# Corpus Edge Chain Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_chain_analysis.py

## Problem

claim_network.py measures direct connections between chunks.
edge_reachability.py measures which chunks are reachable from a starting node.
No tool walks multi-hop chains to find transitive support paths
(A supports B, B supports C), transitive tension paths
(A supports B, B contradicts C), or mixed chains, measuring how
argumentative structure propagates across the corpus.

## Solution

A new tool `tools/corpus/edge_chain_analysis.py` with four subcommands:

- `chains [--db PATH] [--json] [--max-hops N]`: enumerate all chains of
  length 2..max_hops in the claim_edges graph via DFS, reporting path,
  edge types, tension (contradicts mixed with non-contradicts), and
  uniformity (all edges same type).
- `tension [--db PATH] [--json]`: filter chains to those containing
  both contradicts and non-contradicts edges, surfacing where
  argumentative structure shifts polarity across hops.
- `hub-chains [--db PATH] [--json]`: identify chunks appearing in the
  most chains, broken down by position (start, middle, end), to find
  nodes that serve as structural hubs in transitive argumentation.
- `summary [--db PATH] [--json] [--max-hops N]`: aggregate chain
  statistics including total chains, max chain length, tension chain
  count, uniform chain count, average chain length, and distinct
  chunks participating in chains.
- `selftest`: exercises 14 checks covering 1-hop chain counts,
  multi-hop chain discovery, tension detection, hub position tracking,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **DFS chain enumeration**: walks the directed adjacency list built
  from claim_edges, visiting each node at most once per path to avoid
  cycles, collecting chains from length 1 (single edge) through
  max_hops.
- **Tension detection**: a chain has tension when it contains at least
  one contradicts edge and at least one non-contradicts edge, indicating
  a polarity shift in the transitive argumentation.
- **Hub analysis**: counts each chunk's appearances as chain start,
  middle, or end, revealing which nodes serve as structural connectors
  in the argumentative graph.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_chain_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-chain-analysis.md`: this spec

## See also

- claim_network.py: measures direct edge connections; this tool measures
  transitive multi-hop paths.
- edge_reachability.py: measures reachable node sets; this tool
  enumerates the specific paths and their edge-type composition.

## Non-goals

- Cycle detection or strongly connected component analysis.
- Edge weight propagation across chains.
- Shortest-path or minimum-cost path computation.
- Chain pruning by confidence threshold.
