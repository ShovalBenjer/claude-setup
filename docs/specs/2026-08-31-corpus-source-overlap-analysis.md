# Corpus Source Overlap Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_overlap_analysis.py

## Problem

chunk_similarity_clusters.py clusters chunks by simhash distance but
does not measure pairwise overlap between sources. No tool quantifies
which source pairs share the most near-duplicate content, which sources
are isolated (no overlap with anything), or what the overall
inter-source redundancy rate is.

## Solution

A new tool `tools/corpus/source_overlap_analysis.py` with four
subcommands:

- `pairs [--db PATH] [--json] [--threshold N]`: find source pairs with
  overlapping chunks by comparing simhash fingerprints across source
  boundaries, reporting match count, overlapping chunk counts per side,
  and overlap rates.
- `matrix [--db PATH] [--json] [--threshold N]`: per-source overlap
  summary across all other sources, showing how many sources and chunks
  each source overlaps with.
- `isolated [--db PATH] [--json] [--threshold N]`: list sources with no
  overlapping chunks in any other source, identifying unique content.
- `summary [--db PATH] [--json] [--threshold N]`: aggregate statistics
  including overlapping pairs, sources with overlap, isolated sources,
  total matches, and average overlap rate.
- `selftest`: exercises 14 checks covering pair detection, match counts,
  per-side chunk counts, isolation detection, matrix overlap rates,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Pairwise comparison**: compares chunks from every source pair by
  simhash hamming distance, measuring directional overlap rates for
  each side of the pair.
- **Isolation detection**: sources with no near-duplicate chunks in
  any other source are flagged as isolated, representing unique
  content contributions.
- **Configurable threshold**: the simhash bit-distance threshold
  controls sensitivity, with lower values finding only near-exact
  duplicates and higher values capturing paraphrases.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff, slop_lint)

## Scope

- `tools/corpus/source_overlap_analysis.py`: new tool
- `docs/specs/2026-08-31-corpus-source-overlap-analysis.md`: this spec

## See also

- chunk_similarity_clusters.py: clusters chunks by simhash distance;
  this tool measures pairwise source-level overlap.

## Non-goals

- Content deduplication or merge recommendations.
- Plagiarism detection or attribution scoring.
- Source priority ranking by uniqueness.
- Simhash recomputation from raw text.
