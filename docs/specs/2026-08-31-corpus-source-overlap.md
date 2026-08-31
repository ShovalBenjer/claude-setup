# Corpus Source Overlap Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/source_overlap.py

## Problem

Multiple sources can cover the same material, but no tool measured
content overlap between sources.  Understanding redundancy required
manually querying chunk_similarities and cross-referencing with the
sources table, and there was no way to identify which sources
contributed mostly duplicated content or which source pairs had the
highest overlap.

## Solution

A new tool `tools/corpus/source_overlap.py` with three subcommands:

- `pairs [--db PATH] [--top N] [--min-score F] [--json]`: ranks source
  pairs by overlap ratio.  For each pair, reports the number of similar
  chunk pairs, average and maximum cosine scores, and the overlap ratio
  (similar pairs divided by the smaller source's chunk count).
- `detail --source-id SID [--db PATH] [--json]`: per-source overlap
  breakdown.  Shows each overlapping source with its pair count, average
  score, and the top five most similar chunk pairs.
- `redundant [--db PATH] [--threshold F] [--json]`: lists sources where
  a high fraction of chunks have near-duplicates in other sources.
  Reports each source's total chunks, overlapping chunk count, and
  redundancy ratio.
- `selftest`: exercises 14 checks covering all three subcommands,
  overlap ratio correctness, detail breakdown, redundancy detection,
  superseded-chunk exclusion, empty corpus, and JSON serialisation.

### Design properties

- **Ratio-based ranking**: overlap ratio normalises for source size,
  so small sources with high overlap rank above large sources with
  incidental matches.
- **Threshold-driven redundancy**: the redundant subcommand uses a
  configurable similarity threshold (default 0.7) to define
  near-duplication.
- **Superseded-chunk aware**: only active chunks participate.
- **Graceful degradation**: empty corpus or missing similarity data
  returns empty results.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/source_overlap.py`: new tool
- `docs/specs/2026-08-31-corpus-source-overlap.md`: this spec

## See also

- [corpus-similarity-store](2026-08-30-corpus-similarity-store.md):
  provides the chunk_similarities data this tool aggregates.
- [corpus-semantic-dedup](2026-08-30-corpus-semantic-dedup.md):
  deduplicates individual chunks; this tool measures overlap at the
  source level.
- [corpus-source-impact](2026-08-31-corpus-source-impact.md): scores
  sources by analytical footprint; this tool measures their content
  redundancy.
- [corpus-timeline](2026-08-31-corpus-timeline.md): analyses temporal
  patterns; this tool analyses content redundancy patterns.

## Non-goals

- Automated source removal or merging.
- Embedding-based similarity (uses pre-computed cosine scores).
- Cross-corpus overlap.
- Temporal overlap trends.
