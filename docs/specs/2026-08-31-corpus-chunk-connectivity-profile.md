# Corpus Chunk Connectivity Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/chunk_connectivity_profile.py

## Problem

chunk_position_analysis.py profiles ordinal distribution across
sources. edge_text_correlation.py correlates word count with edge
patterns. No tool profiles per-chunk connectivity in the claim_edges
graph, measuring in-degree, out-degree, and total degree to identify
argumentative hubs and isolated chunks, or how connectivity varies
with document position.

## Solution

A new tool `tools/corpus/chunk_connectivity_profile.py` with four
subcommands:

- `degree [--db PATH] [--json]`: per-chunk in-degree (incoming
  edges), out-degree (outgoing edges), and total degree, sorted by
  total degree descending to surface argumentative hubs.
- `by-position [--db PATH] [--json]`: average connectivity metrics
  grouped by ordinal position band (first, early, middle, late),
  revealing whether document position correlates with edge
  participation.
- `isolated [--db PATH] [--json]`: chunks with no edges in either
  direction, representing content not yet integrated into the
  argumentative graph.
- `summary [--db PATH] [--json]`: aggregate statistics including
  connected vs isolated counts, isolation rate, average and maximum
  degree, and hub chunk count (chunks with degree exceeding twice
  the average).
- `selftest`: exercises 14 checks covering degree computation,
  in/out separation, position band aggregation, isolation detection,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Directed degree**: separates in-degree (target of edges) from
  out-degree (source of edges), distinguishing chunks that receive
  argumentation from those that produce it.
- **Position correlation**: groups connectivity by ordinal band to
  test whether early document sections attract more edge activity.
- **Hub detection**: identifies chunks with disproportionately high
  connectivity as argumentative hubs using a threshold of twice the
  mean degree.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/chunk_connectivity_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-chunk-connectivity-profile.md`: this spec

## See also

- chunk_position_analysis.py: profiles ordinal distribution; this
  tool correlates position with edge connectivity.
- edge_text_correlation.py: correlates word count with edges; this
  tool profiles degree-level connectivity patterns.
- edge_bridge_analysis.py: identifies structural bridges; this tool
  profiles per-chunk degree and isolation.

## Non-goals

- Centrality metrics beyond degree (betweenness, closeness).
- Community detection or graph partitioning.
- Connectivity-based chunk ranking or prioritization.
- Automatic edge suggestion for isolated chunks.
