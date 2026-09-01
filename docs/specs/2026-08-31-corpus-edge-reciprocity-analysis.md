# Corpus Edge Reciprocity Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_reciprocity_analysis.py

## Problem

edge_chain_analysis.py walks directed multi-hop paths.
chunk_connectivity_profile.py measures degree per chunk. No tool
measures whether edges between chunk pairs are reciprocal (A->B and
B->A both exist), whether reciprocal pairs agree or disagree in
edge type, or what fraction of the graph consists of mutual vs
one-way argumentation.

## Solution

A new tool `tools/corpus/edge_reciprocity_analysis.py` with four
subcommands:

- `reciprocal [--db PATH] [--json]`: chunk pairs with edges in
  both directions, showing forward/reverse edge counts, edge types
  per direction, and whether the types agree.
- `asymmetric [--db PATH] [--json]`: edges whose reverse direction
  has no counterpart, representing one-way argumentative claims.
- `type-agreement [--db PATH] [--json]`: pattern analysis of
  reciprocal pairs showing how often mutual edges share the same
  type vs differ (e.g. supports both ways vs supports one way and
  contradicts the other).
- `summary [--db PATH] [--json]`: aggregate statistics including
  reciprocal pair count, reciprocal edge count, asymmetric edge
  count, reciprocity rate, and type agreement rate.
- `selftest`: exercises 14 checks covering reciprocal pair
  detection, type agreement, asymmetric edge identification,
  pattern counting, summary totals, JSON round-trip, and empty
  corpus.

### Design properties

- **Bidirectional pair detection**: identifies chunk pairs connected
  in both directions, measuring mutual argumentation density.
- **Type agreement scoring**: for each reciprocal pair, checks
  whether both directions use the same edge type, surfacing
  reinforcing (both support) vs conflicting (support/contradict)
  mutual relationships.
- **Asymmetry identification**: edges with no reverse counterpart
  represent unreciprocated claims, a structural signal for
  argumentative gaps.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/edge_reciprocity_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-reciprocity-analysis.md`: this spec

## See also

- edge_chain_analysis.py: walks directed paths; this tool measures
  bidirectional edge symmetry.
- chunk_connectivity_profile.py: measures degree; this tool
  decomposes connectivity into reciprocal vs asymmetric components.
- edge_cycle_detection.py: finds closed loops; reciprocal pairs
  are the simplest two-node cycle.

## Non-goals

- Reciprocity-weighted path scoring.
- Automatic edge suggestion for asymmetric pairs.
- Reciprocity trend analysis over time.
- Source-level reciprocity aggregation.
