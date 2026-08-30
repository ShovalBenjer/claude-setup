# Corpus Export

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/export.py

## Problem

The research corpus had tools for ingestion, querying, and health checking, but
no way to serialize the full corpus or filtered subsets for external analysis,
dashboards, or consumption by other tools. An operator wanting to analyze corpus
data outside the CLI had to write ad-hoc SQL queries against the database.

## Solution

A new tool `tools/corpus/export.py` with six subcommands:

- `full [--db PATH] [--format json|jsonl] [--status STATUS] [--kind KIND]`:
  exports all chunks as section 7.2 records with source provenance, citations,
  contradictions, artifacts, staleness, and trust. Supports filtering by status
  and kind.
- `defects [--db PATH] [--format json|jsonl]`: exports uncited accepted claims
  and unresolved contradictions with counts.
- `artifacts [--db PATH] [--implemented] [--format json|jsonl]`: exports all
  artifacts with their source chunks and trust flags. `--implemented` filters
  to artifacts with disk evidence.
- `sources [--db PATH] [--format json|jsonl]`: exports all sources with
  staleness verdicts and per-source chunk counts.
- `summary [--db PATH] [--json]`: produces a concise corpus overview with
  counts for sources, chunks, citations, defects, and artifacts.
- `selftest`: exercises 19 checks covering all export modes, filters,
  output formats, and field presence.

### Export shape

Each full export record matches the section 7.2 shape:

```json
{
  "chunk_id": "c9f2...",
  "text": "...",
  "kind": "prose",
  "status": "accepted",
  "word_count": 42,
  "source": {"source_id": "...", "uri": "...", "kind": "local_md",
             "license_verdict": "vendor", "liveness": "live", ...},
  "citations": [...],
  "contradicted_by": [...],
  "artifacts": [...],
  "staleness": {"verdict": "fresh", "age_days": 4, "reasons": []},
  "trust": "trusted"
}
```

### Design properties

- **Filterable**: status and kind filters on full export, implemented filter on
  artifacts, combinable for precise subsets.
- **Two output formats**: JSON (array) for structured consumption, JSONL
  (one record per line) for streaming and line-oriented tools.
- **Summary mode**: human-readable overview without the full export weight.

## Results

First run against the real corpus (366 sources, 5937 chunks):
- 366 sources, all live
- 1362 accepted, 4507 quarantined, 68 superseded chunks
- 3584 citations (3 verified)
- 0 uncited accepted claims, 11 unresolved contradictions
- 1602 artifacts, 46 implemented (2.9%)

## Scope

- `tools/corpus/export.py`: new tool
- `docs/specs/2026-08-30-corpus-export.md`: this spec

## Non-goals

- CSV export (JSON and JSONL cover all structured-data needs).
- Incremental/differential export (use staleness.py sweep for change detection).
- Direct integration with external dashboards (export produces files, not APIs).
