# Corpus Cross-Table Analysis

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/xray.py

## Problem

The corpus has four analytical tables (chunk_clusters, chunk_topics,
chunk_similarities, claim_edges) populated by separate tools, but no
tool joins them together.  Questions like "which clusters have the most
contradictions?", "does topic 3 span one cluster or five?", and "which
chunks are both topically orphaned and semantically isolated?" required
manual multi-table SQL.

## Solution

A new tool `tools/corpus/xray.py` with four subcommands:

- `topic-clusters [--db PATH] [--topic N] [--json]`: shows which
  clusters each topic spans.  Without `--topic`, lists all topics with
  their cluster count and spread (clusters/chunks ratio).  With
  `--topic`, drills into one topic showing per-cluster member counts
  and cluster top terms.
- `cluster-health [--db PATH] [--cluster N] [--json]`: measures
  intra-cluster contradiction count and density, total edge count,
  and average/min/max cosine similarity.  Sorted by contradiction
  density descending to surface the most contested clusters first.
- `hotspots [--db PATH] [--top N] [--json]`: ranks topics by
  open-contradiction density (contradictions per chunk).  Shows the
  top terms for each topic so the hotspot is immediately nameable.
- `isolation [--db PATH] [--top N] [--json]`: finds chunks with low
  maximum similarity and small topic membership.  Computes an
  isolation score ((1 - max_similarity) / topic_size) to surface
  chunks that are both semantically distant from all neighbours and
  topically marginal.
- `selftest`: exercises 14 checks.

### Design properties

- **Pure SQL joins**: no new dependencies; queries the tables that
  cluster_store, topic_model, similarity_store, and contradict already
  populate.
- **Superseded-chunk aware**: only chunks with `status != 'superseded'`
  participate.
- **Resolved-edge aware**: only unresolved claim_edges (resolution IS
  NULL) count as open contradictions.
- **Table-creation safe**: creates analytical tables with IF NOT EXISTS
  so xray works even if upstream tools have not run yet (returning
  empty results).

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/xray.py`: new tool
- `docs/specs/2026-08-31-corpus-xray.md`: this spec

## See also

- [corpus-cluster-store](2026-08-30-corpus-cluster-store.md): persists
  chunk_clusters data this tool reads.
- [corpus-topic-model](2026-08-31-corpus-topic-model.md): persists
  chunk_topics and topic_terms data this tool reads.
- [corpus-similarity-store](2026-08-30-corpus-similarity-store.md):
  persists chunk_similarities data this tool reads.
- [corpus-contradiction-detection](2026-08-30-corpus-contradiction-detection.md):
  populates claim_edges with contradiction edges this tool queries.
- [corpus-citation-graph](2026-08-31-corpus-citation-graph.md): also
  analyses claim_edges, but per-chunk rather than per-topic/cluster.

## Non-goals

- Writing or modifying any analytical table (read-only joins).
- Graph traversal or PageRank over the joined data.
- Automated remediation (culling outliers, merging clusters).
- Cross-corpus analysis.
