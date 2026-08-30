# Corpus Diff

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/diff.py

## Problem

The research corpus had tools for querying current state (health, export,
coverage) but no way to answer "what changed since my last session?" An
operator returning to the corpus after time away had to compare full exports
or query individual tables to understand what evolved.

## Solution

A new tool `tools/corpus/diff.py` with three subcommands:

- `since DATE [--db PATH] [--json]`: computes what changed since a cutoff
  timestamp. Reports new sources, new chunks (with status breakdown), new
  citations, new and resolved contradictions, and new artifacts.
- `snapshot [--db PATH]`: captures current corpus state as a concise summary
  with source, chunk, citation, contradiction, and artifact counts.
- `selftest`: exercises 18 checks covering both subcommands, all fields,
  edge cases (future cutoff, past cutoff), and JSON serialization.

### Diff shape

```json
{
  "cutoff": "2026-08-25T00:00:00Z",
  "new_sources": [{"source_id": "...", "uri": "...", "title": "...", "kind": "local_md"}],
  "new_chunks": {
    "total": 5937,
    "by_status": {"accepted": 1362, "quarantined": 4507, "superseded": 68},
    "details": [...]
  },
  "new_citations": 3584,
  "new_contradictions": 11,
  "resolved_contradictions": 0,
  "new_artifacts": [{"name": "...", "type": "library", "implemented": false}],
  "corpus_totals": {"sources": 366, "chunks": 5937}
}
```

### Snapshot shape

```json
{
  "timestamp": "2026-08-30T...",
  "sources": 366,
  "chunks": 5937,
  "by_status": {"accepted": 1362, "quarantined": 4507, "superseded": 68},
  "citations": 3584,
  "unresolved_contradictions": 11,
  "artifacts": 1602,
  "implemented_artifacts": 46
}
```

### Design properties

- **Timestamp-based**: uses `ingested_utc` and `fetched_utc` already in the
  schema, requiring no additional tracking tables.
- **Status breakdown**: new chunks are split by status so the operator sees
  how many were accepted vs quarantined.
- **Contradiction tracking**: reports both new and resolved contradictions
  to show whether defect count is trending up or down.
- **Capped details**: chunk and artifact details are capped at 50 entries
  to keep output manageable for large diffs.

## Results

First run against the real corpus (since 2026-08-25):
- 366 new sources, 5937 new chunks (all ingested on same date)
- 3584 new citations, 11 new contradictions, 0 resolved
- 50 new artifacts shown (of 1602 total)
- Selftest: 18 checks, all passing

## Scope

- `tools/corpus/diff.py`: new tool
- `docs/specs/2026-08-30-corpus-diff.md`: this spec

## Non-goals

- Storing snapshots persistently (the operator can redirect `snapshot` output
  to a file and diff against it later).
- Tracking per-chunk status transitions (would require a status history table
  not in the current schema).
- Diffing between two arbitrary snapshots (compare two `snapshot` outputs
  externally).
