# Corpus Tag Edge Correlation

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_edge_correlation.py

## Problem

tag_citation_correlation.py correlates tags with citations.
domain_citation_profile.py correlates domains with citations.
No tool joins chunk_tags with claim_edges to measure which tags
appear on chunks with high edge connectivity, or which edge types
are most common for each tag.

## Solution

A new tool `tools/corpus/tag_edge_correlation.py` with four
subcommands:

- `by-tag [--db PATH] [--json]`: edge density per tag with tagged
  chunk count, total edges touching tagged chunks, and
  edges-per-chunk rate.
- `by-edge-type [--db PATH] [--json]`: tag distribution per edge
  type with distinct tag count, edge count, and tagged endpoint count.
- `cross [--db PATH] [--json]`: full tag by edge_type
  cross-tabulation with counts.
- `summary [--db PATH] [--json]`: aggregate statistics including
  tagged-with-edges count, edge coverage rate, tagged edge share,
  and densest tag.
- `selftest`: exercises 14 checks covering per-tag edge density,
  tag exclusion (no edges), per-edge-type distribution,
  cross-tabulation, summary totals, edge share, JSON serialisation,
  and empty corpus.

### Design properties

- **Tag-edge join**: joins chunk_tags with claim_edges on both
  source_chunk and target_chunk, capturing edges where either
  endpoint carries the tag.
- **Bidirectional matching**: a tag on a chunk counts for all edges
  that touch that chunk, whether as source or target.
- **Edge type stratification**: breaks down tag-edge correlation by
  edge type, surfacing whether tags predict supportive, contradictory,
  or refinement relationships.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_edge_correlation.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-edge-correlation.md`: this spec

## See also

- [corpus-tag-citation-correlation](2026-08-31-corpus-tag-citation-correlation.md):
  correlates tags with citations; this tool correlates tags with edges.
- [corpus-domain-citation-profile](2026-08-31-corpus-domain-citation-profile.md):
  correlates domains with citations; the domain-edge analogue is a
  separate gap.

## Non-goals

- Causal inference between tagging and edge formation.
- Tag recommendation based on edge patterns.
- Edge confidence adjustment based on tag presence.
- Multi-tag co-occurrence edge analysis.
