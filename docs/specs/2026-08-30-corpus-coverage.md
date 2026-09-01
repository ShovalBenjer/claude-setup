# Corpus Coverage

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/coverage.py

## Problem

The research corpus had tools for ingestion, querying, export, and staleness
checking, but no way to answer the question "what is indexed vs what is on
disk?" An operator could not tell whether new files had been added to the
source directories without being ingested, or whether indexed sources
pointed to files that no longer existed.

## Solution

A new tool `tools/corpus/coverage.py` with two subcommands:

- `report [--db PATH] [--books-db PATH] [--json] [--missing-only]`:
  walks source directories, compares against the sources table, and reports
  indexed, missing, and orphaned files. Optionally checks books index
  coverage.
- `selftest`: exercises 16 checks covering disk scanning, indexed matching,
  missing detection, orphaned detection, per-directory rates, books coverage,
  error handling, and JSON serialization.

### Report shape

```json
{
  "corpus": {
    "on_disk": 365,
    "indexed": 365,
    "missing": 0,
    "orphaned": 0,
    "coverage_rate": 1.0,
    "total_chunks": 5936,
    "per_directory": {
      "work-docs": {"on_disk": 189, "indexed": 189, "missing": 0, "rate": 1.0},
      "research-papers": {"on_disk": 89, "indexed": 89, "missing": 0, "rate": 1.0},
      "docs/analysis": {"on_disk": 87, "indexed": 87, "missing": 0, "rate": 1.0}
    },
    "missing_files": [],
    "orphaned_uris": []
  },
  "books": null
}
```

### Design properties

- **Per-directory breakdown**: coverage rate for each source directory so
  gaps are immediately attributable.
- **Bidirectional**: detects both missing files (on disk but not indexed) and
  orphaned URIs (indexed but file deleted).
- **Books-aware**: optionally checks books index coverage when the books
  database is available.
- **Structured output**: `--json` produces machine-readable output for
  dashboards and automation.

## Results

First run against the real corpus (365 on-disk files, 366 sources):
- 365 files indexed, 0 missing, 0 orphaned
- 100% coverage across all three source directories
- Books database: not available on cloud machine (local-only)

## Scope

- `tools/corpus/coverage.py`: new tool
- `docs/specs/2026-08-30-corpus-coverage.md`: this spec

## Non-goals

- Triggering re-ingestion for missing files (use `pipeline.py` for that).
- Checking chunk-level freshness (use `staleness.py` for that).
- Reporting on non-local_md sources (the tool covers only the directories
  that `research.py` ingests from).
