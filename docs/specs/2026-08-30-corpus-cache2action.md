# Corpus Cache-to-Action Proposal Path

**Date:** 2026-08-30
**Status:** done
**Tool:** tools/corpus/cache2action.py

## Problem

The `artifacts` table held 1602 rows (46 implemented with evidence paths)
but no retrieval path existed to surface actionable artifacts in response
to a query. Step 10 of the research corpus spec called for a
cache-to-action proposal path with trust flags, where artifacts from
index-only sources are display-only and nothing is auto-executed.

## Solution

A new tool `tools/corpus/cache2action.py` with three subcommands:

- `propose --query TEXT [--db PATH] [--repo PATH]`: finds actionable
  artifacts matching a query via FTS5, attaches trust flags based on the
  source's `license_verdict`, checks evidence path validity against disk,
  and returns sorted proposals. Never executes anything.
- `verify [--db PATH] [--repo PATH]`: checks all implemented artifacts
  for evidence path validity. Reports valid, invalid, and missing counts.
- `selftest`: exercises 9 checks covering trust classification, evidence
  validation, executability flags, and edge cases.

### Trust model

Each proposal carries a `trust` field derived from the source's
`license_verdict`:

- `actionable`: vendor-licensed sources. These artifacts may be proposed
  for execution (but never auto-executed).
- `display_only`: index-only, link-only, or blocked sources. These
  artifacts are shown for reference only.
- `unknown`: source not found (data integrity issue).

The `executable` flag is `true` only when `trust == "actionable"` AND
`implemented == true`. Display-only artifacts are never marked executable
regardless of implementation status.

### Evidence verification

The `verify` subcommand re-resolves every implemented artifact's
`evidence_path` against the current filesystem. Paths that no longer
exist degrade the artifact to a suggestion rather than an instruction,
per the spec's requirement that proof must be re-resolvable.

## Results

First run against the real corpus:
- 46 implemented artifacts: all 46 evidence paths valid
- Propose query "deploy script service": 25 proposals, 0 executable
  (all referenced but not implemented on this machine)

## Design decisions

- Proposals are sorted by executability, then implementation status,
  then evidence validity, then trust level. Actionable implemented
  artifacts with valid evidence sort first.
- The tool returns proposals only. Execution requires the caller to
  pass through the same permission boundary as any other command (the
  operator approves anything destructive).
- FTS5 search uses OR-combined query words for broad matching, with
  a 200-chunk result limit to bound cost.

## Scope

- `tools/corpus/cache2action.py`: new tool
- `docs/specs/2026-08-30-corpus-cache2action.md`: this spec

## Non-goals

- Auto-execution of any retrieved artifact.
- Integration with the permission boundary (that is the caller's job).
- Crawling or fetching external sources (step 6, separate feature).
