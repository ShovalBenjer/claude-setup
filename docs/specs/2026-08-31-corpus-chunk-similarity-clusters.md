# Corpus Chunk Similarity Clusters

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/chunk_similarity_clusters.py

## Problem

heading_simhash_profile.py profiles simhash collisions by heading path.
No tool clusters chunks by simhash bit distance to find near-duplicate
content across the corpus, measuring how much material is redundant
and which sources contribute overlapping content.

## Solution

A new tool `tools/corpus/chunk_similarity_clusters.py` with four
subcommands:

- `clusters [--db PATH] [--json] [--threshold N]`: find clusters of
  chunks whose simhash values are within N bits of each other, using
  single-linkage clustering. Reports cluster size, member chunks,
  source count, and whether the cluster spans multiple sources.
- `by-source [--db PATH] [--json] [--threshold N]`: per-source cluster
  participation, showing how many clusters each source contributes to
  and the fraction of its chunks that fall into clusters.
- `cross-source [--db PATH] [--json] [--threshold N]`: filter to
  clusters spanning multiple sources, surfacing content overlap across
  different documents.
- `summary [--db PATH] [--json] [--threshold N]`: aggregate statistics
  including total clusters, chunks in clusters, cluster rate, cross-source
  cluster count, largest cluster size, and average cluster size.
- `selftest`: exercises 14 checks covering hamming distance computation,
  cluster formation, cross-source detection, single-linkage behavior,
  per-source statistics, summary totals, JSON round-trip, and empty
  corpus.

### Design properties

- **Simhash hamming distance**: uses XOR and popcount to measure bit
  distance between simhash fingerprints, grouping chunks that share
  structural similarity in their normalized text.
- **Single-linkage clustering**: if chunk A is near B and B is near C,
  all three join the same cluster, capturing transitive similarity
  chains.
- **Cross-source detection**: flags clusters spanning multiple sources,
  which indicates content duplication or close paraphrasing across
  different documents.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/chunk_similarity_clusters.py`: new tool
- `docs/specs/2026-08-31-corpus-chunk-similarity-clusters.md`: this spec

## See also

- heading_simhash_profile.py: profiles simhash collisions by heading;
  this tool clusters by bit distance across the whole corpus.

## Non-goals

- Locality-sensitive hashing for approximate nearest neighbor search.
- Cluster merging or deduplication recommendations.
- Simhash recomputation or normalization adjustment.
- Hierarchical clustering with configurable linkage.
