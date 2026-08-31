# Corpus Chunk Recommender

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/recommend.py

## Problem

Each analytical tool operates on a single signal: similarity_store
ranks by cosine distance, topic_model groups by topic, cluster_store
by cluster membership.  There was no way to ask "what is most related
to chunk X across all signals at once?" without manually querying each
table and mentally combining the results.

## Solution

A new tool `tools/corpus/recommend.py` with two subcommands:

- `related --chunk-id CID [--db PATH] [--top N] [--json]`: finds the
  most related chunks by a weighted composite of five signals: topic
  overlap (0.25), cosine similarity (0.25), cluster co-membership
  (0.20), tag Jaccard overlap (0.15), and citation/edge link (0.15).
  Returns each candidate's per-signal breakdown and composite score.
- `explain --chunk-id CID --target TID [--db PATH] [--json]`: details
  the relationship between two specific chunks including all signal
  scores and any claim_edges connecting them.
- `selftest`: exercises 14 checks.

### Design properties

- **Multi-signal fusion**: combines five independent analytical signals
  into a single relevance ranking.
- **Transparent scoring**: every recommendation includes the per-signal
  breakdown so the user sees why a chunk ranked where it did.
- **Superseded-chunk aware**: only active chunks participate.
- **Resolved-edge aware**: only unresolved claim_edges count.
- **Graceful degradation**: missing analytical data (no topic, no
  cluster, no similarity) scores zero for that signal rather than
  failing.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/recommend.py`: new tool
- `docs/specs/2026-08-31-corpus-recommend.md`: this spec

## See also

- [corpus-xray](2026-08-31-corpus-xray.md): cross-table analysis by
  topic and cluster; this tool analyses by individual chunk.
- [corpus-similarity-store](2026-08-30-corpus-similarity-store.md):
  provides the cosine similarity signal.
- [corpus-topic-model](2026-08-31-corpus-topic-model.md): provides
  the topic overlap signal.
- [corpus-cluster-store](2026-08-30-corpus-cluster-store.md): provides
  the cluster co-membership signal.

## Non-goals

- Embedding-based similarity (uses pre-computed cosine scores).
- Learning weights from user feedback.
- Batch recommendation across all chunks.
- Cross-corpus recommendation.
