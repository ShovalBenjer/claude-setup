# Corpus Source Edge Stance

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_edge_stance.py

## Problem

source_impact.py ranks sources by total edge count but does not
break down edge types per source. edge_confidence_profile.py
profiles confidence distribution across types and bands. No tool
measures how edge_type distributes per source, revealing which
sources produce predominantly supportive vs contradictory
argumentation and whether cross-source connections are
adversarial or reinforcing.

## Solution

A new tool `tools/corpus/source_edge_stance.py` with four
subcommands:

- `stance [--db PATH] [--json]`: per-source edge-type distribution
  from outgoing edges, showing total edges, supports/contradicts
  rates, and the dominant edge type for each source.
- `cross-source [--db PATH] [--json]`: pairwise source connections
  via claim_edges where source and target chunks belong to different
  sources, with edge-type breakdown per pair.
- `outliers [--db PATH] [--json]`: sources whose edge-type ratios
  deviate most from the corpus-wide average, measured by maximum
  absolute deviation across all edge types.
- `summary [--db PATH] [--json]`: aggregate stance statistics
  including corpus-wide supports/contradicts rates, dominant-type
  source counts, and cross-source pair count.
- `selftest`: exercises 14 checks covering per-source edge counts,
  dominant type detection, rate computation, cross-source pair
  enumeration, outlier detection, summary totals, JSON round-trip,
  and empty corpus.

### Design properties

- **Directional stance**: measures outgoing edge types from each
  source's chunks, treating each source as an argumentative actor.
- **Cross-source profiling**: identifies how sources argue with
  each other by filtering to edges crossing source boundaries.
- **Deviation detection**: flags sources whose edge-type mix
  differs most from the corpus norm, surfacing biased or
  one-sided sources.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/source_edge_stance.py`: new tool
- `docs/specs/2026-08-31-corpus-source-edge-stance.md`: this spec

## See also

- source_impact.py: ranks sources by edge count; this tool breaks
  down edge types per source.
- edge_confidence_profile.py: profiles confidence by type; this
  tool profiles type distribution by source.
- source_overlap_analysis.py: measures content overlap between
  sources; this tool measures argumentative stance between sources.

## Non-goals

- Stance scoring or bias classification.
- Sentiment analysis of chunk text.
- Automatic source credibility ranking.
- Edge-type recommendation or rebalancing.
