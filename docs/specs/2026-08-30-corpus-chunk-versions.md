# Corpus Chunk Versioning

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/chunk_versions.py

## Problem

When a source is re-ingested, the chunker replaces old chunk content
with no record of what changed.  There is no way to audit how the
corpus evolves over time, detect content drift, or compare a chunk's
current text against earlier ingestions.

## Solution

A new `chunk_versions` table in the corpus schema and a companion tool
`tools/corpus/chunk_versions.py` that records version snapshots keyed
on content hash changes.

### Schema addition (in research.py)

```sql
CREATE TABLE IF NOT EXISTS chunk_versions (
    version_id   TEXT PRIMARY KEY,
    chunk_id     TEXT NOT NULL REFERENCES chunks(chunk_id),
    version_num  INTEGER NOT NULL,
    norm_sha256  TEXT NOT NULL,
    word_count   INTEGER NOT NULL,
    snapshot_utc TEXT NOT NULL,
    UNIQUE(chunk_id, version_num)
);
CREATE INDEX IF NOT EXISTS ix_versions_chunk ON chunk_versions(chunk_id);
```

### Tool commands

- `snapshot [--db PATH] [--dry-run]`: scans all non-superseded chunks
  and records a new version row when a chunk's `norm_sha256` differs
  from the latest recorded version.  First snapshot creates version 1
  for every chunk.
- `history --chunk-id CID [--db PATH] [--json]`: returns version
  history for a specific chunk, newest first.
- `drift [--db PATH] [--json]`: finds chunks with multiple versions
  (content changed across ingestions), sorted by version count.
- `stats [--db PATH] [--json]`: summary including total version rows,
  coverage, multi-version count, and the most-revised chunk.
- `selftest`: exercises 14 checks.

### Design properties

- **Content-addressed**: version creation is triggered by hash change,
  not by re-running the snapshot command.  Unchanged content is skipped.
- **Idempotent**: re-snapshotting unchanged chunks increments the
  `unchanged` counter, not `new_versions`.
- **Selective**: superseded chunks are excluded from snapshotting.
- **Audit-ready**: each version records the content hash and word
  count at snapshot time, enabling size-drift and hash-drift queries.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/research.py`: schema addition (chunk_versions table)
- `tools/corpus/chunk_versions.py`: new tool
- `docs/specs/2026-08-30-corpus-chunk-versions.md`: this spec

## See also

- [corpus-tag-store](2026-08-30-corpus-tag-store.md): another schema
  extension for persisted metadata on chunks.

## Non-goals

- Storing full text content in the version table (only the hash and
  word count are recorded; the text lives in the chunks table).
- Automatic rollback to a previous version.
- Diff rendering between version contents.
