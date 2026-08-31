# Corpus Cluster Store

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/cluster_store.py

## Problem

The semantic clusterer (`tools/corpus/semantic.py`) computes ML-based
KMeans cluster assignments for every chunk using TF-IDF vectors, but
discards the results after printing them. Downstream tools that need
per-cluster retrieval, cluster-based chunking strategies, or topical
navigation must re-run the clustering from scratch every time.
Without persistence, cluster membership is unavailable in SQL queries
and cannot be joined with other corpus tables.

## Solution

A new tool `tools/corpus/cluster_store.py` that bridges the semantic
clusterer and the database, persisting cluster assignments into a
dynamically created `chunk_clusters` table.

### Schema (created dynamically via `_ensure_table`)

```sql
CREATE TABLE IF NOT EXISTS chunk_clusters (
    chunk_id       TEXT NOT NULL REFERENCES chunks(chunk_id),
    cluster_label  INTEGER NOT NULL,
    top_terms      TEXT NOT NULL,
    clustered_utc  TEXT NOT NULL,
    PRIMARY KEY (chunk_id)
);
CREATE INDEX IF NOT EXISTS ix_clusters_label
    ON chunk_clusters(cluster_label);
```

The table is created on first use rather than in `research.py`'s
`init_schema`, keeping the core schema stable and letting the tool
manage its own storage lifecycle.

### Tool commands

- `persist [--db PATH] [--n-clusters N] [--dry-run]`: runs
  `cluster_chunks()` from `semantic.py`, then inserts or updates rows
  in `chunk_clusters`. Idempotent: unchanged assignments are skipped,
  changed labels or terms are updated.
- `lookup --chunk-id CID [--db PATH] [--json]`: returns the cluster
  assignment for a specific chunk including label, top terms, and
  timestamp.
- `members --cluster-label N [--db PATH] [--json]`: lists chunks in a
  cluster with metadata from the chunks table, excludes superseded
  chunks, ordered by word count descending.
- `stats [--db PATH] [--json]`: cluster store statistics including
  total rows, distinct clusters, active chunk coverage ratio, and
  per-cluster counts with top terms.
- `selftest`: exercises 13 checks.

### Design properties

- **ML-based**: uses scikit-learn MiniBatchKMeans on TF-IDF vectors
  via `semantic.py`'s `cluster_chunks()`, not heuristic grouping.
- **Idempotent**: re-persisting with unchanged assignments increments
  the `unchanged` counter. Label and top-term changes are detected
  by value comparison.
- **Dry-run safe**: `--dry-run` computes and reports without writing.
- **Composable**: `persist_clusters()` returns a dict consumable by
  `pipeline.py`. `cluster_members()` returns structured results for
  programmatic use.
- **Selective**: `cluster_members` excludes superseded chunks via the
  `status != 'superseded'` filter on the chunks join.
- **Dynamic schema**: the table is created on first use by any
  function that touches it, so the tool works on any corpus database
  without requiring a schema migration.

## Results

- Selftest: 13 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/cluster_store.py`: new tool
- `docs/specs/2026-08-30-corpus-cluster-store.md`: this spec

## See also

- [corpus-semantic](2026-08-30-corpus-semantic.md): the ML clusterer
  whose results this tool persists.
- [corpus-domain-store](2026-08-30-corpus-domain-store.md): similar
  persistence pattern for domain classification results.
- [corpus-cluster](2026-08-30-corpus-cluster.md): heuristic clustering
  (simhash, citation, source overlap) as distinct from ML clustering.
- [corpus-xray](2026-08-31-corpus-xray.md): cross-table analysis that
  joins chunk_clusters with topics, similarities, and contradictions.

## Non-goals

- Replacing the semantic clusterer's algorithm or parameters.
- Incremental cluster updates (re-clustering is fast enough to run
  from scratch).
- Automatic re-clustering on chunk content changes.
- Optimal cluster count selection (the caller chooses n-clusters).
