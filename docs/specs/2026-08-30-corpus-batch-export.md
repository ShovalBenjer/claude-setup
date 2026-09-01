# Corpus Batch Export

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/export.py (extended)

## Problem

The export tool supports filtering by chunk status and kind, but lacks
filters for source kind, tags, and date ranges.  Downstream consumers
(dashboards, audits, cross-tool pipelines) need faceted export to
avoid post-processing the full dump.  Tags from the chunk_tags table
are computed and persisted but never surfaced in export records.

## Solution

Extended `tools/corpus/export.py` with four new filters and tag
inclusion in the `full` export command:

### New filters

- `--source-kind KIND`: filter by source type (e.g. `paper`, `local_md`,
  `repo`).  Comma-separated for multiple kinds.
- `--tag TAG`: filter by tag from the `chunk_tags` table.  Comma-separated
  for multiple tags (OR logic).
- `--since DATE`: include chunks ingested on or after an ISO date.
- `--before DATE`: include chunks ingested before an ISO date.
- `--out FILE`: write output to a file instead of stdout.

All filters compose with the existing `--status` and `--kind` filters.

### Tags in export records

Every exported chunk record now includes a `tags` field: a list of
`{tag, score}` objects sorted by score descending, drawn from the
`chunk_tags` table.  Chunks with no tags get an empty list.

### Design properties

- **Composable**: all six filters (status, kind, source-kind, tag,
  since, before) can be combined in a single query.
- **Backward-compatible**: existing CLI invocations produce identical
  output except for the added `tags` field in records.
- **SQL-level filtering**: joins and WHERE clauses push filtering into
  SQLite rather than post-filtering in Python.

## Results

- Selftest: 27 checks (up from 19), all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/export.py`: extended with new filters, tags field, file
  output
- `docs/specs/2026-08-30-corpus-batch-export.md`: this spec

## Non-goals

- Streaming export for very large corpora.
- Export to formats other than JSON/JSONL (CSV, Parquet).
- Scheduled or incremental export.
