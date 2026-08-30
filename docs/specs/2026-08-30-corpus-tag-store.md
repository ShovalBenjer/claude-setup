# Corpus Tag Store

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/tag_store.py

## Problem

The auto-tagger (`tools/corpus/tagger.py`) computes domain tags for
every chunk using TF-IDF scoring against 20 domain vocabularies, but
discards the results after printing them.  Downstream tools (retrieval,
search, export) need persisted tag data for faceted queries and
filtering.  Without persistence, every consumer must re-run the tagger
from scratch, and tag-based filtering is impossible in SQL queries.

## Solution

A new table `chunk_tags` in the corpus schema and a companion tool
`tools/corpus/tag_store.py` that bridges the tagger and the database.

### Schema addition (in research.py)

```sql
CREATE TABLE IF NOT EXISTS chunk_tags (
    chunk_id  TEXT NOT NULL REFERENCES chunks(chunk_id),
    tag       TEXT NOT NULL,
    score     REAL NOT NULL,
    tagged_utc TEXT NOT NULL,
    PRIMARY KEY (chunk_id, tag)
);
CREATE INDEX IF NOT EXISTS ix_tags_tag ON chunk_tags(tag);
```

### Tool commands

- `persist [--db PATH] [--top-k N] [--min-score F] [--dry-run]`:
  runs the tagger, then inserts or updates rows in `chunk_tags`.
  Idempotent: unchanged scores are skipped, changed scores are updated.
- `lookup --chunk-id CID [--db PATH] [--json]`: returns tags for a
  specific chunk, sorted by score descending.
- `find --tag TAG [--db PATH] [--min-score F] [--json]`: finds chunks
  carrying a given tag, joins the chunks table for metadata, excludes
  superseded chunks.
- `stats [--db PATH] [--json]`: tag store statistics including total
  rows, distinct chunks tagged, distinct tags used, coverage ratio,
  and per-tag counts with average scores.
- `selftest`: exercises 13 checks.

### Design properties

- **Idempotent**: re-persisting with unchanged scores increments the
  `unchanged` counter, not `inserted`.  Score changes are detected
  with a tolerance of 0.0001.
- **Dry-run safe**: `--dry-run` computes and reports without writing.
- **Composable**: `persist_tags()` returns a dict consumable by
  `pipeline.py`.  `find_by_tag()` returns structured results for
  programmatic use.
- **Selective**: `find_by_tag` excludes superseded chunks via the
  `status != 'superseded'` filter on the chunks join.

## Results

- Selftest: 13 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/research.py`: schema addition (chunk_tags table)
- `tools/corpus/tag_store.py`: new tool
- `docs/specs/2026-08-30-corpus-tag-store.md`: this spec

## Non-goals

- Replacing the tagger's scoring algorithm.
- Tag taxonomy management or tag renaming.
- Automatic re-tagging on chunk content changes.
