# Corpus Tag Co-occurrence Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_cooccurrence.py

## Problem

The chunk_tags table records which domain tags apply to each chunk, but
no tool analysed which tags appear together.  Understanding tag
relationships required manual SQL joining chunk_tags to itself, and
there was no way to find tag communities (groups that co-occur
frequently) or hub tags that bridge otherwise separate groups.

## Solution

A new tool `tools/corpus/tag_cooccurrence.py` with three subcommands:

- `matrix [--db PATH] [--top N] [--min-pmi F] [--json]`: ranks tag
  pairs by pointwise mutual information (PMI).  Returns each pair's
  co-occurrence count, PMI score, and individual frequencies.
- `communities [--db PATH] [--json]`: discovers tag communities as
  connected components in the co-occurrence graph (edges require at
  least two shared chunks).  Reports each community's members, size,
  and total frequency.
- `hubs [--db PATH] [--top N] [--json]`: identifies tags that bridge
  multiple communities by neighbour count and cross-community edges.
- `selftest`: exercises 14 checks covering all three subcommands,
  PMI correctness, community isolation, hub frequency, superseded-chunk
  exclusion, empty corpus, and JSON serialisation.

### Design properties

- **PMI ranking**: pointwise mutual information surfaces
  disproportionately linked pairs, not merely frequent ones.
- **Graph-based communities**: connected components on the
  co-occurrence graph reveal thematic clusters of tags.
- **Hub detection**: tags bridging multiple communities highlight
  cross-cutting concerns.
- **Superseded-chunk aware**: only active chunks participate.
- **Graceful degradation**: empty corpus returns empty results.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_cooccurrence.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-cooccurrence.md`: this spec

## See also

- [corpus-tagger](2026-08-30-corpus-tagger.md): computes the domain
  tags this tool analyses for co-occurrence.
- [corpus-tag-store](2026-08-30-corpus-tag-store.md): persists tags
  into chunk_tags, the table this tool reads.
- [corpus-diversity](2026-08-31-corpus-diversity.md): measures
  corpus-level tag entropy; this tool analyses tag-to-tag structure.
- [corpus-vocab-analysis](2026-08-31-corpus-vocab-analysis.md):
  profiles vocabulary per kind; this tool profiles tag relationships.

## Non-goals

- Tag merging or renaming (read-only analysis).
- Weighted edges from tag scores (uses binary presence).
- Modularity-based community detection (uses connected components).
- Temporal co-occurrence drift.
