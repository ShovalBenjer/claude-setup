# Corpus Outlier Store

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/outlier_store.py

## Problem

The semantic analyser (`tools/corpus/semantic.py`) can detect topically
isolated chunks via `find_outliers()`, which identifies chunks whose
maximum cosine similarity to any other chunk falls below a threshold.
But the results are discarded after printing.  Downstream tools that
need outlier status for quality monitoring, review prioritisation, or
corpus health checks must re-run the full pairwise similarity
computation each time.

## Solution

A new tool `tools/corpus/outlier_store.py` that persists outlier
detection results into a dynamically created `chunk_outliers` table.

### Schema (created dynamically via `_ensure_table`)

```sql
CREATE TABLE IF NOT EXISTS chunk_outliers (
    chunk_id         TEXT NOT NULL REFERENCES chunks(chunk_id),
    max_similarity   REAL NOT NULL,
    threshold_used   REAL NOT NULL,
    detected_utc     TEXT NOT NULL,
    PRIMARY KEY (chunk_id)
);
```

### Tool commands

- `persist [--db PATH] [--threshold F] [--dry-run]`: runs
  `find_outliers()` from `semantic.py` and inserts or updates rows.
  Chunks that are no longer outliers (above the threshold after
  re-computation) are removed from the table.
- `lookup --chunk-id CID [--db PATH] [--json]`: returns the outlier
  record for a specific chunk, or None if it is not an outlier.
- `list [--db PATH] [--limit N] [--json]`: returns all outliers with
  chunk metadata, sorted by isolation (lowest max_similarity first),
  excludes superseded chunks.
- `stats [--db PATH] [--json]`: summary including total outliers,
  outlier rate, average and minimum max_similarity, and a per-kind
  breakdown.
- `selftest`: exercises 14 checks.

### Design properties

- **ML-based**: uses scikit-learn TF-IDF cosine similarity via
  `semantic.py`'s `find_outliers()`, not heuristic isolation.
- **Self-cleaning**: chunks that stop being outliers (because new
  similar content was added or the threshold changed) are removed
  from the table on the next persist.
- **Idempotent**: re-persisting with unchanged scores skips the row.
  Score or threshold changes trigger updates.
- **Dry-run safe**: `--dry-run` computes and reports without writing.
- **Composable**: `persist_outliers()` returns a dict consumable by
  `pipeline.py`. `list_outliers()` returns structured results for
  programmatic use.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/outlier_store.py`: new tool
- `docs/specs/2026-08-30-corpus-outlier-store.md`: this spec

## See also

- [corpus-semantic](2026-08-30-corpus-semantic.md): the ML analyser
  whose `find_outliers()` this tool persists.
- [corpus-similarity-store](2026-08-30-corpus-similarity-store.md):
  persists pairwise similarity pairs (the complement of outlier
  detection).
- [corpus-cluster-store](2026-08-30-corpus-cluster-store.md): another
  persistence layer for ML-computed chunk relationships.

## Non-goals

- Replacing the semantic analyser's outlier threshold or algorithm.
- Automatic outlier remediation (marking outliers as superseded).
- Outlier trend tracking over time.
