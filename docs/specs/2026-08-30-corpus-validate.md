# Corpus Validate

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/validate.py

## Problem

The research corpus has no structural integrity check. Orphaned rows
(chunks referencing deleted sources, citations pointing to missing chunks,
claim edges with dangling endpoints, artifacts tied to nonexistent chunks)
can accumulate silently through ingestion bugs, manual edits, or
interrupted operations. Without a validator, corruption is only discovered
when a downstream query returns unexpected results.

## Solution

A new tool `tools/corpus/validate.py` with two subcommands:

- `check [--db PATH] [--json]`: runs 10 integrity checks and reports a
  verdict (VALID or INVALID) with a list of issues.
- `selftest`: exercises 14 checks covering all detection paths, severity
  classification, and JSON serialization.

### Integrity checks

| Check | Severity | Description |
|---|---|---|
| orphan_chunks | error | Chunks whose source_id has no matching source |
| orphan_citations | error | Citations whose chunk_id has no matching chunk |
| orphan_claim_edges | error | Claim edges where source_chunk or target_chunk is missing |
| orphan_artifacts | error | Artifacts whose chunk_id has no matching chunk |
| empty_chunk_text | error | Chunks with empty or NULL norm_text |
| empty_source_uri | error | Sources with empty or NULL canonical_uri |
| duplicate_chunk_ids | error | Duplicate chunk_id values |
| orphan_supersedes | warning | Sources whose supersedes target does not exist |
| negative_word_count | warning | Chunks with word_count below zero |
| invalid_source_bytes | warning | Sources with bytes below zero |

### Design properties

- **Severity classification**: issues are either errors (which make the
  verdict INVALID) or warnings (informational, do not affect the verdict).
- **Non-destructive**: the tool only reads, never modifies data.
- **Structured output**: `--json` emits machine-readable results with
  verdict, issue list, and table counts.

## Results

- Selftest: 14 checks, all passing
- Ready for integration into the gate or health oracle pipeline

## Scope

- `tools/corpus/validate.py`: new tool
- `docs/specs/2026-08-30-corpus-validate.md`: this spec

## Non-goals

- Automatic repair of detected issues (the operator decides what to fix).
- Content-level validation (duplicate detection, quality scoring).
- FTS5 index consistency checks (those are handled by SQLite itself).
