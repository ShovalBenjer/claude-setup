# Corpus Similarity Store

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/similarity_store.py

## Problem

The semantic analyser (`tools/corpus/semantic.py`) can compute pairwise
chunk similarities on demand via `find_similar()`, but each call
rebuilds the full TF-IDF matrix from scratch. The embedding layer
(`tools/corpus/embed.py`) stores pre-fitted PCA-reduced vectors, yet
no tool materialises the nearest-neighbor relationships into the
database. Without persistence, similarity queries cannot be expressed
in SQL joins, and every "find similar" operation pays the full
vectorisation cost.

## Solution

A new tool `tools/corpus/similarity_store.py` that reads the fitted
embedding vectors and persists nearest-neighbor pairs above a cosine
threshold into a dynamically created `chunk_similarities` table.

### Schema (created dynamically via `_ensure_table`)

```sql
CREATE TABLE IF NOT EXISTS chunk_similarities (
    chunk_id_a     TEXT NOT NULL REFERENCES chunks(chunk_id),
    chunk_id_b     TEXT NOT NULL REFERENCES chunks(chunk_id),
    cosine_score   REAL NOT NULL,
    computed_utc   TEXT NOT NULL,
    PRIMARY KEY (chunk_id_a, chunk_id_b)
);
CREATE INDEX IF NOT EXISTS ix_sim_a
    ON chunk_similarities(chunk_id_a);
CREATE INDEX IF NOT EXISTS ix_sim_b
    ON chunk_similarities(chunk_id_b);
```

### Tool commands

- `persist [--db PATH] [--threshold F] [--top-k N] [--dry-run]`:
  loads the fitted embedding vectors, computes pairwise cosine
  similarities, and stores the top-k neighbours per chunk that
  exceed the threshold. Idempotent: unchanged scores are skipped,
  changed scores are updated.
- `similar --chunk-id CID [--db PATH] [--json]`: returns the most
  similar chunks with metadata from the chunks table, excludes
  superseded chunks, sorted by cosine score descending.
- `mutual --chunk-id CID [--db PATH] [--json]`: returns chunks
  that are mutually similar (A appears in B's neighbours and B
  appears in A's neighbours), a stronger signal of topical
  relatedness.
- `stats [--db PATH] [--json]`: summary statistics including total
  pairs, distinct chunks, average/min/max scores, and mutual pair
  count.
- `selftest`: exercises 14 checks.

### Design properties

- **Vector-based**: uses the L2-normalised PCA-reduced TF-IDF
  vectors from embed.py rather than recomputing TF-IDF from raw
  text. Cosine similarity reduces to a dot product.
- **Idempotent**: re-persisting with unchanged scores increments
  the `unchanged` counter. Score changes are detected with a
  tolerance of 0.0001.
- **Configurable**: threshold and top-k are tunable per run,
  controlling the density of the similarity graph.
- **Graceful degradation**: returns `status: unavailable` when
  vectors are not fitted, rather than raising an error.
- **Mutual pairs**: the `mutual` subcommand surfaces bidirectional
  neighbours, filtering out asymmetric similarities that arise
  from hub nodes.
- **Dynamic schema**: the table is created on first use, requiring
  no schema migration in `research.py`.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/similarity_store.py`: new tool
- `docs/specs/2026-08-30-corpus-similarity-store.md`: this spec

## See also

- [corpus-embedding-rerank](2026-08-30-corpus-embedding-rerank.md):
  produces the fitted vectors this tool consumes.
- [corpus-semantic-dedup](2026-08-30-corpus-semantic-dedup.md): uses
  the same vectors for paraphrase detection with a higher threshold.
- [corpus-cluster-store](2026-08-30-corpus-cluster-store.md): another
  persistence layer for ML-computed chunk relationships.

## Non-goals

- Replacing embed.py's vector fitting or PCA parameters.
- Approximate nearest-neighbour indexing (exact computation is fast
  enough for the corpus size).
- Automatic re-computation when new chunks are added.
- Graph visualisation of the similarity network.
