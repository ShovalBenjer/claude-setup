# Corpus Edge Bridge Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_bridge_analysis.py

## Problem

edge_chain_analysis.py walks multi-hop acyclic paths.
edge_cycle_detection.py finds closed loops.
No tool identifies bridge edges whose removal would disconnect
components of the argumentation graph, measuring structural fragility
and which edge types serve as critical single-point connectors.

## Solution

A new tool `tools/corpus/edge_bridge_analysis.py` with four subcommands:

- `bridges [--db PATH] [--json]`: enumerate all bridge edges in the
  claim_edges graph (treated as undirected for connectivity), reporting
  edge id, endpoints, and edge type.
- `components [--db PATH] [--json]`: analyze connected components of
  the undirected claim_edges graph, showing chunk count, edge count,
  edge type diversity, and member list per component.
- `by-type [--db PATH] [--json]`: bridge count per edge type with
  bridge rate (bridges / total edges of that type), revealing which
  edge types disproportionately serve as structural connectors.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  edges, total nodes, component count, largest component size, bridge
  count, bridge rate, and fragility (fraction of nodes incident to a
  bridge).
- `selftest`: exercises 14 checks covering bridge detection in a
  triangle-plus-chain topology, non-bridge verification for cycle
  edges, per-type bridge rates, component analysis, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Undirected connectivity**: treats the directed claim_edges graph as
  undirected for bridge detection, since argumentative connectivity
  flows in both directions for structural analysis.
- **Bridge detection**: tests each edge by removing it and checking
  reachability, identifying edges that are single points of failure
  in the argumentative structure.
- **Fragility metric**: measures what fraction of graph nodes are
  incident to at least one bridge, quantifying how much of the
  structure depends on non-redundant connections.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_bridge_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-bridge-analysis.md`: this spec

## See also

- [corpus-edge-chain-analysis](2026-08-31-corpus-edge-chain-analysis.md):
  walks multi-hop acyclic paths; this tool identifies structurally
  critical edges.
- [corpus-edge-cycle-detection](2026-08-31-corpus-edge-cycle-detection.md):
  finds closed loops; edges within cycles are never bridges.

## Non-goals

- Tarjan's algorithm optimization for large graphs.
- Articulation point detection (vertex bridges).
- Edge connectivity or minimum cut computation.
- Automatic bridge strengthening suggestions.
