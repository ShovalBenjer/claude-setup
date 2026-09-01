# Corpus Citation Gate

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/cite_gate.py

## Problem

The ingestion pipeline spec (section 6, stage 4) requires that every
chunk with `kind='claim'` carry at least one citation.  Without
enforcement, 57.7% of files in the local corpus lack any `[S#]`
reference, and that defect is invisible until a retrieval caller
discovers it.  Quarantining uncited claims converts an invisible defect
rate into a visible backlog.

## Solution

A new tool `tools/corpus/cite_gate.py` implementing the stage 4
citation gate:

- `scan [--db PATH] [--json]`: examines all accepted claim chunks for
  citations.  Checks three sources: existing `citations` table rows,
  `[S#]` reference tags in text, and bare URLs.  Also detects DOI
  patterns.  Reports each claim as cited or uncited.
- `apply [--db PATH] [--dry-run]`: creates `citations` table entries
  for extracted references (tags, URLs, DOIs), then quarantines any
  claim chunk that still has zero citations with
  `status_reason='uncited'`.  Idempotent: re-running skips existing
  citation IDs and already-quarantined chunks.
- `backlog [--db PATH] [--json]`: lists all quarantined uncited claims
  with text preview and source title, providing the visible queue the
  spec demands.
- `stats [--db PATH] [--json]`: reports total claims, accepted count,
  quarantined uncited count, total citations, cited chunk count, and
  citation rate.
- `selftest`: exercises 18 checks covering extraction accuracy (tags,
  URLs, DOIs), scan correctness, apply behavior (dry run vs real),
  quarantine enforcement, backlog query, idempotency, stats structure,
  and edge cases.

### Citation extraction

Three detectors, following the spec:

1. **`[S#]` tags**: regex `\[S\d+\]` captures numbered references.
2. **DOI patterns**: `10.\d{4,}/\S+` with automatic `https://doi.org/`
   prefix.
3. **Bare URLs**: `https?://` patterns, deduplicated against DOIs
   already found.

### Design properties

- **Quarantine, not delete**: uncited claims get
  `status='quarantined'`, never removed.  Reversible via promote.py.
- **Idempotent**: citation IDs derived from chunk_id + URI, so
  re-running never duplicates.
- **Existing citations respected**: chunks with pre-existing
  `citations` table rows are recognized as cited without re-extraction.
- **Composable**: the backlog query feeds promote.py for triage.

## Results

- Selftest: 18 checks, all passing

## Scope

- `tools/corpus/cite_gate.py`: new tool
- `docs/specs/2026-08-30-corpus-cite-gate.md`: this spec

## Non-goals

- Resolving `[S#]` tags against a source's reference section.
- Citation verification (checking that URLs resolve).
- Auto-adding citations to uncited claims.
