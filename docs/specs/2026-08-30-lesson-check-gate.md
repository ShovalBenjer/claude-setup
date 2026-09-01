# Lesson Check Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** lesson_check

## Problem

`state/lessons.jsonl` is an append-only ledger of operational lessons with 58
entries, but nothing validates its structural integrity. Measured 2026-08-30:
one duplicate ID (`L-2026-08-07-d` at rows 46 and 48, two genuinely different
lessons), two entries missing the `status` field, and inconsistent use of `ts`
vs `date` for timestamps. A ledger that no tool reads structurally can
accumulate parse errors and schema drift without detection.

## Solution

A new tool `tools/audit/lesson_check.py` with two subcommands:

- `check`: validates that the ledger is parseable JSON, every row has an `id`
  field, and IDs use a recognised format (dated `L-YYYY-MM-DD-x` or legacy
  `L###`). Schema completeness gaps (missing `status`, missing timestamp,
  closed without explanation) are reported as warnings rather than failures,
  because the ledger is append-only and pre-existing gaps cannot be
  retroactively fixed.
- `selftest`: exercises the valid, malformed-JSON, missing-ID, duplicate-ID,
  bad-format, legacy-ID, no-file, and schema-warning paths.

A new `cmd` domain `lesson_check` in `quality-contract.json` runs `check`.

## Scope

- `tools/audit/lesson_check.py`: new oracle
- `quality-contract.json`: `lesson_check` domain entry (cmd, timeout 60s)

## Design decisions

- Structural errors (parse failures, missing `id`, unrecognised ID format) fail
  the gate. Schema completeness gaps (missing `status`, missing timestamp,
  closed without closure explanation) are warnings that do not fail, because the
  ledger is append-only and historical rows cannot be edited to add fields.
- Duplicate IDs are warnings, not errors, for the same append-only reason. The
  existing duplicate (`L-2026-08-07-d`) represents two genuinely different
  lessons that happened to collide on the same ID.
- Legacy IDs (`L001` through `L018`) are accepted as a recognised format. The
  ledger predates the dated ID convention.

## Non-goals

- Executing lesson falsifiers. Nine lessons carry a `falsifier` field, but
  most are natural-language descriptions of verification conditions rather
  than executable commands. Mechanical execution is a follow-up.
- Editing the ledger to fix pre-existing schema gaps. The ledger is
  append-only by contract.
