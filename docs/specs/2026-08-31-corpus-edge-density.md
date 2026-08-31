# Corpus Claim Edge Density

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/edge_density.py

## Problem

The claim_edges table records relationships between chunks, but no
tool measured how densely connected the claim network is.  Sources
with many edges per chunk have well-linked knowledge; sources with
few edges contain isolated content that participates in no claim
relationships.  Identifying these content islands required manually
checking edge counts against chunk inventories.

## Solution

A new tool `tools/corpus/edge_density.py` with three subcommands:

- `density [--db PATH] [--json]`: per-source edge density (edges per
  accepted chunk).  Includes edge type breakdown per source.  Sorted
  by density descending to surface the most interconnected sources
  first.
- `islands [--db PATH] [--json]`: accepted chunks with no claim edges
  at all.  These represent isolated knowledge that participates in
  no support, contradiction, or refinement relationships.  Sorted by
  word count descending to surface the largest islands first.
- `summary [--db PATH] [--json]`: aggregate density statistics
  including overall density, connected vs island chunk counts, island
  rate, edge type totals, and per-kind density breakdowns.
- `selftest`: exercises 14 checks covering density computation, sort
  order, edge count accuracy, edge type breakdown, island detection,
  connected exclusion, island ordering, summary structure, connected
  plus island totals, positive density, edge types, kind breakdown,
  JSON serialisation, and empty corpus.

### Design properties

- **Per-source granularity**: density per source reveals which
  documents contribute well-linked vs isolated knowledge.
- **Island detection**: chunks with zero edges are content islands
  that may need claim edge annotation.
- **Kind-stratified density**: per-kind breakdowns reveal whether
  certain chunk types (code, config) are systematically less
  connected than claims.
- **Edge type awareness**: per-source edge type breakdown shows the
  mix of supports, contradicts, refines, etc.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/edge_density.py`: new tool
- `docs/specs/2026-08-31-corpus-edge-density.md`: this spec

## See also

- [corpus-claim-consensus](2026-08-31-corpus-claim-consensus.md):
  measures cross-source agreement; this tool measures network
  connectivity density.
- [corpus-edge-resolution](2026-08-30-corpus-edge-resolution.md):
  analyses resolution patterns; this tool analyses edge distribution
  and isolated chunks.
- [corpus-readability](2026-08-31-corpus-readability.md):
  measures text complexity; this tool measures claim network
  interconnectedness.
- [corpus-claim-network](2026-08-30-corpus-claim-network.md):
  maps the claim network topology; this tool quantifies its density.
- [corpus-edge-confidence](2026-08-31-corpus-edge-confidence.md):
  analyses confidence values on claim edges; this tool measures
  edge count and density ratios.

## Non-goals

- Edge creation or annotation suggestions.
- Minimum density enforcement or gating.
- Cross-source edge density comparison.
- Edge weight or confidence analysis.
