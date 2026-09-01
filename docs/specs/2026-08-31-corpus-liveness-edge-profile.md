# Corpus Liveness Edge Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/liveness_edge_profile.py

## Problem

liveness_cross_analysis.py cross-tabulates liveness against kind,
publisher, and license. liveness_citation_profile.py correlates
liveness with citations. No tool joins sources.liveness with
claim_edges to measure whether live sources produce more edges than
stale ones, how edge types distribute across liveness states, or
which edges cross liveness boundaries.

## Solution

A new tool `tools/corpus/liveness_edge_profile.py` with four
subcommands:

- `by-liveness [--db PATH] [--json]`: edge distribution per source
  liveness state, showing total edges, distinct edge types, source
  chunk count, and average confidence.
- `by-type [--db PATH] [--json]`: edge type distribution per
  liveness state, showing how supports, contradicts, and other
  edge types distribute across live, stale, and archived sources.
- `cross-liveness [--db PATH] [--json]`: edges that cross source
  liveness boundaries, grouped by source state, target state, and
  edge type, identifying inter-state claim relationships.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total edges, liveness states with edges, total states, coverage
  ratio, cross-liveness edge count and rate, average edges per
  state, and distinct edge types.
- `selftest`: exercises 14 checks covering per-state edge counts,
  edge type distribution, cross-liveness detection, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Source-based liveness attribution**: edges are attributed to
  the liveness state of the source that contains the source chunk.
- **Cross-liveness detection**: uses IS NOT comparison to catch
  edges between different liveness states.
- **Maintenance correlation**: reveals whether actively maintained
  sources participate in more claim relationships than stale or
  archived ones.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/liveness_edge_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-liveness-edge-profile.md`: this spec

## See also

- [corpus-liveness-citation-profile](2026-08-31-corpus-liveness-citation-profile.md):
  correlates liveness with citations; this tool correlates liveness
  with claim edges.
- [corpus-liveness-cross-analysis](2026-08-31-corpus-liveness-cross-analysis.md):
  cross-tabulates liveness against kind, publisher, and license;
  this tool adds the claim edge dimension.

## Non-goals

- Liveness state transition prediction from edge patterns.
- Automatic staleness detection based on edge activity.
- Edge recommendation based on liveness state.
- Liveness-based source retirement decisions.
