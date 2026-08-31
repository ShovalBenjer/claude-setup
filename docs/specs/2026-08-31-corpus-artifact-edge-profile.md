# Corpus Artifact-Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/artifact_edge_profile.py

## Problem

No tool cross-tabulates artifact_type or implemented status against
edge_type or confidence.  artifact_graph.py uses claim_edges only to
connect artifact pairs.  Understanding whether chunks containing
implemented APIs attract more supports edges than chunks with
unimplemented patterns, and whether confidence differs by artifact
type, required a manual multi-table join.

## Solution

A new tool `tools/corpus/artifact_edge_profile.py` with four
subcommands:

- `edge-by-type [--db PATH] [--json]`: edge type distribution per
  artifact type with total count, dominant edge type, and full
  breakdown.
- `confidence [--db PATH] [--json]`: mean edge confidence per
  artifact type with min and max.
- `impl-edges [--db PATH] [--json]`: edge patterns for implemented
  vs unimplemented artifacts with dominant edge type and breakdown.
- `summary [--db PATH] [--json]`: aggregate artifact-edge statistics
  including types with edges, total edges, highest edge type, highest
  confidence type, and implementation comparison.
- `selftest`: exercises 14 checks covering edge-by-type entries,
  per-type edge counts, confidence values, implementation edge
  profiles, implemented vs unimplemented comparison, summary totals,
  highest confidence identification, JSON serialisation, and empty
  corpus.

### Design properties

- **Bidirectional edge counting**: a chunk participates in an edge
  whether it is source or target, so artifact-edge counts reflect
  full connectivity rather than directionality.
- **Implementation comparison**: the impl-edges subcommand directly
  contrasts implemented and unimplemented artifact edge patterns,
  answering whether implementation status correlates with edge
  density or type.
- **Confidence dimension**: mean confidence per artifact type reveals
  whether certain artifact categories attract higher-confidence
  edges than others.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/artifact_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-artifact-edge-profile.md`: this spec

## See also

- [corpus-artifact-graph](2026-08-31-corpus-artifact-graph.md):
  builds artifact pair connections from claim_edges; this tool adds
  the artifact_type and implementation dimension to edge analysis.
- [corpus-edge-detection-timeline](2026-08-31-corpus-edge-detection-timeline.md):
  analyses edge detection timing; this tool crosses edges with
  artifact metadata rather than temporal distribution.

## Non-goals

- Artifact recommendation based on edge patterns.
- Causal analysis of why certain artifact types attract more edges.
- Edge pruning or weight adjustment based on artifact type.
- Artifact implementation prediction from edge profiles.
