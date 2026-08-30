# Corpus Promote

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/promote.py

## Problem

The research corpus quarantines uncited prose chunks during ingestion (4507
of 5937 chunks). There was no tool to review these quarantined chunks and
promote valid content to accepted status, leaving two-thirds of the corpus
inaccessible to search and retrieval queries that filter on
`status='accepted'`.

## Solution

A new tool `tools/corpus/promote.py` with five subcommands:

- `list [--source SOURCE_ID] [--limit N] [--json] [--db PATH]`: lists
  quarantined chunks with source context, snippets, and quarantine reasons.
- `promote CHUNK_ID [...] [--reason TEXT] [--db PATH]`: promotes individual
  chunks from quarantined to accepted.
- `reject CHUNK_ID [...] [--reason TEXT] [--db PATH]`: rejects quarantined
  chunks (marks them as operator-reviewed and not worth keeping).
- `promote-source SOURCE_ID [--reason TEXT] [--db PATH]`: promotes all
  quarantined chunks from a given source in one operation.
- `stats [--json] [--db PATH]`: shows quarantine breakdown by source, reason,
  and kind.
- `selftest`: exercises 16 checks covering list, promote, reject,
  promote-source, stats, edge cases, and JSON serialization.

### Design properties

- **Non-destructive review**: quarantined chunks are promoted or rejected,
  never deleted. The operator can always query the full chunk history.
- **Reason tracking**: every promotion or rejection records a `status_reason`
  so the decision is auditable.
- **Bulk operations**: `promote-source` handles the common case of trusting
  all content from a known source.
- **Statistics**: the `stats` subcommand shows the quarantine backlog by
  source, reason, and kind to help prioritize review.

## Results

First run against the real corpus:
- 4507 quarantined chunks, all with reason "uncited"
- All are prose kind
- Top sources: sales/business books (120, 102, 86 chunks) and technical
  research papers
- Selftest: 16 checks, all passing

## Scope

- `tools/corpus/promote.py`: new tool
- `docs/specs/2026-08-30-corpus-promote.md`: this spec

## Non-goals

- Automatic promotion based on heuristics (the operator decides what to
  promote; the tool executes the decision).
- Bulk reject by kind or word count (individual review or source-level
  promotion covers the practical cases).
- Undo/rollback of promotion (the chunk status can be changed again with
  the same tool if needed).
