# Corpus Paper Rule

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/paper_rule.py

## Problem

Stage 7 of the ingestion pipeline enforces the operator's 2026-only
paper rule.  The corpus contains paper sources from multiple years, and
the operator has decided that only 2026 papers should be admitted as
current research.  Papers from earlier years (notably the pwc-archive
2025 snapshot) serve as historical baseline but must not be treated as
current evidence.  Additionally, papers whose publisher cannot be
verified from the paper record itself should be quarantined rather than
admitted with a guess.

## Solution

A new tool `tools/corpus/paper_rule.py` implementing stage 7:

- `scan [--db PATH] [--json]`: examines all `kind='paper'` sources and
  reports pass/fail against the rule.
- `apply [--db PATH] [--dry-run]`: quarantines chunks from failing
  paper sources, setting `status='quarantined'` and
  `status_reason='paper_rule: ...'` with the specific violation.
- `stats [--db PATH] [--json]`: paper source statistics including
  year distribution, missing publisher/date counts, and quarantined
  chunk counts.
- `selftest`: exercises 18 checks.

### Rule checks

Two checks for each `kind='paper'` source:

1. **Year check**: `published_utc` must have year 2026.  Missing date
   or any other year fails.
2. **Publisher check**: `publisher` must be a non-empty, non-whitespace
   value from the paper record.  Missing or blank publisher fails.

Both violations are reported; a source can fail both checks.

### Design properties

- **Non-destructive**: nothing is deleted.  Every failure is a status
  plus a reason.  Quarantine is reversible; deletion is not.
- **Idempotent**: re-applying the rule does not double-quarantine.
  Already-quarantined chunks are skipped by the `status = 'accepted'`
  filter in the UPDATE.
- **Composable**: `_check_source()` is a pure function testable
  without a database.  `scan_papers()` returns a list of dicts usable
  by `pipeline.py`.
- **Selective**: only `kind='paper'` sources are examined.  Local
  markdown, repos, datasets, and derived sources are untouched.

## Results

- Selftest: 18 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/paper_rule.py`: new tool
- `docs/specs/2026-08-30-corpus-paper-rule.md`: this spec

## Non-goals

- Automated publisher verification against external databases.
- Paper metadata extraction (DOI lookup, citation graph).
- Changing the 2026-only threshold (operator decision, not a tool
  parameter).
