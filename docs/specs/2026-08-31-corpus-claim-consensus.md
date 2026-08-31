# Corpus Claim Consensus

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/claim_consensus.py

## Problem

The claim_edges table records support, contradiction, refinement,
duplication, and supersession relationships between chunks, but no tool
measured cross-source agreement on individual claims.  Answering whether
a claim has independent corroboration or faces contradiction required
manual edge traversal and source-ID comparison.

## Solution

A new tool `tools/corpus/claim_consensus.py` with three subcommands:

- `consensus [--db PATH] [--top N] [--json]`: per-claim consensus
  scores ranked most contested first.  For each claim (target chunk in
  claim_edges), reports supports, contradicts, refines, duplicates,
  supersedes counts, distinct source count, cross-source edge count,
  average edge confidence, and a consensus score from -1 (all
  contradict) to +1 (all support).
- `contested [--db PATH] [--json]`: claims with at least one
  contradiction edge.  Surfaces knowledge conflicts that need
  resolution.
- `summary [--db PATH] [--json]`: aggregate consensus statistics
  including total claims with edges, average consensus, contested
  count, unanimous support count, cross-source claim count, and
  per-edge-type totals.
- `selftest`: exercises 14 checks covering superseded exclusion,
  unanimous detection, mixed edge handling, score bounds, sort order,
  cross-source detection, distinct source counting, contested
  filtering, summary structure, unanimous count, contested count,
  edge type totals, JSON serialisation, and empty corpus.

### Consensus formula

For each claim chunk that is the target of at least one claim_edge:

    consensus_score = (supports - contradicts) / total_edges

This yields a value from -1.0 (every edge contradicts) to +1.0 (every
edge supports).  Edges of type refines, duplicates, and supersedes are
counted in total_edges but are neutral in the numerator.

### Design properties

- **Cross-source detection**: flags edges where source_chunk and
  target_chunk come from different sources, indicating independent
  corroboration or disagreement.
- **Contested-first ordering**: results sort by consensus ascending,
  putting the most disputed claims at the top.
- **Edge-type granularity**: counts all five edge types separately,
  enabling analysis beyond the binary support/contradict axis.
- **Confidence tracking**: reports average edge confidence per claim,
  surfacing how certain the edges themselves are.
- **Graceful degradation**: returns empty results when no claim_edges
  exist.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/claim_consensus.py`: new tool
- `docs/specs/2026-08-31-corpus-claim-consensus.md`: this spec

## See also

- [corpus-freshness-scorer](2026-08-31-corpus-freshness-scorer.md):
  temporal freshness of chunks; this tool measures inter-source
  agreement on claims.
- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  the health scorecard includes edge_resolution rate; this tool
  provides the deeper per-claim consensus view.
- [corpus-source-overlap](2026-08-31-corpus-source-overlap.md):
  measures source-level content overlap; this tool measures
  claim-level agreement through edges.
- [corpus-ingestion-regression](2026-08-31-corpus-ingestion-regression.md):
  detects within-chunk quality drops across versions; this tool
  detects cross-source disagreement on claims.

## Non-goals

- Claim merging or resolution automation.
- Edge creation or confidence recalibration.
- Consensus-weighted search ranking.
- Historical consensus tracking over time.
