# Corpus Similarity Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/similarity_analysis.py

## Problem

The chunk_similarities, chunk_outliers, and chunk_clusters tables store
computed relatedness signals, but no tool analysed these signals
together.  Finding the similarity score distribution, the most similar
chunk pairs, which outliers are in which kinds, or how cohesive each
cluster is required manual queries across three tables.

## Solution

A new tool `tools/corpus/similarity_analysis.py` with four subcommands:

- `distribution [--db PATH] [--json]`: similarity score distribution
  across all chunk pairs.  Reports total pairs, average, min, and max
  cosine scores, and a five-band histogram (0-0.2 through 0.8-1.0).
- `closest [--db PATH] [--top N] [--json]`: most similar chunk pairs,
  ranked by cosine score descending.  Reports both chunk kinds, both
  source IDs, and a cross-source flag indicating whether the pair
  spans different sources.
- `outliers [--db PATH] [--json]`: outlier chunk analysis from
  chunk_outliers.  Reports total outliers, average max similarity,
  kind distribution, and individual outlier details (max similarity,
  threshold, kind, heading).
- `cluster-cohesion [--db PATH] [--json]`: per-cluster cohesion
  based on intra-cluster similarity scores.  Reports cluster size,
  average intra-cluster cosine score, and number of similarity pairs
  within each cluster.
- `selftest`: exercises 14 checks covering distribution totals, score
  stats, band distribution, closest pair ordering, cross-source flag,
  top-N limiting, outlier report, outlier kind distribution, outlier
  similarity, cluster cohesion, intra-cluster scores, single-member
  clusters, JSON serialisation, and empty corpus.

### Design properties

- **Multi-table integration**: combines chunk_similarities,
  chunk_outliers, and chunk_clusters into a unified relatedness view.
- **Band histogram**: five-band distribution reveals whether the
  corpus is dominated by low or high similarity pairs.
- **Cross-source detection**: closest pairs flag whether high
  similarity spans different sources, indicating potential redundancy.
- **Cluster cohesion**: measures how well clusters hold together by
  averaging intra-cluster similarity scores.
- **Graceful degradation**: each function checks for its required
  tables independently, returning empty results when absent.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/similarity_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-similarity-analysis.md`: this spec

## See also

- [corpus-tag-landscape](2026-08-31-corpus-tag-landscape.md):
  analyses tag patterns; this tool analyses similarity patterns.
- [corpus-semantic-dedup](2026-08-30-corpus-semantic-dedup.md):
  the deduplication infrastructure that writes similarity scores.
- [corpus-cluster-store](2026-08-30-corpus-cluster-store.md):
  the clustering infrastructure this tool reads from.
- [corpus-source-overlap](2026-08-31-corpus-source-overlap.md):
  measures source-level overlap; this tool measures chunk-level
  similarity.

- [corpus-health-scorecard](2026-08-31-corpus-health-scorecard.md):
  aggregates all signal tables into a unified quality summary;
  this tool provides the similarity dimension's underlying data.

## Non-goals

- Similarity recomputation or threshold adjustment.
- Cluster reassignment or merging.
- Embedding generation or dimensionality reduction.
- Cross-corpus similarity comparison.
