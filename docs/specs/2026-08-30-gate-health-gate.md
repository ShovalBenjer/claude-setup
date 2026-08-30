# Gate Health Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** gate_health

## Problem

`state/gate-runs.jsonl` is the largest ledger in the repository (19,117 rows
at measurement time) and nothing validated its structural integrity. Measured
2026-08-30: 10 rows carry a domain verdict as the integer `2` instead of the
string `"N/A"`, a type inconsistency produced by gate.py's builtin handler
path for the `todo_inbox` domain when the intent store is absent. Downstream
consumers that filter on `status == "N/A"` silently miscount these rows.

## Solution

A new tool `tools/audit/gate_health.py` with two subcommands:

- `check`: validates that every row is parseable JSON, required fields
  (`ts`, `project`, `commit`, `verdict`, `domains`) are present, `verdict`
  is one of `PASS`/`FAIL`/`PARTIAL`, domain status values are recognised
  strings, and timestamps match ISO format. Data quality issues in existing
  rows (non-string domain verdicts) are warnings rather than failures because
  the ledger is append-only.
- `selftest`: exercises the valid, malformed-JSON, missing-field,
  non-string-verdict, invalid-verdict, no-file, mixed-schema, and
  PARTIAL-verdict paths.

A new `cmd` domain `gate_health` in `quality-contract.json` runs `check`.

## Scope

- `tools/audit/gate_health.py`: new oracle
- `quality-contract.json`: `gate_health` domain entry (cmd, timeout 60s)

## Design decisions

- Structural errors (parse failures, missing required fields, unrecognised
  verdict values) fail the gate. These indicate data corruption that should
  not be allowed to accumulate.
- Non-string domain verdicts are warnings, not failures, because the ledger
  is append-only and the 10 existing integer values cannot be retroactively
  fixed. The root cause is a gate.py code path that records a builtin
  handler's raw exit code instead of mapping it to `"N/A"`.
- Schema-evolution fields (`duration_seconds`, `run_id`, `unmeasured`,
  `waivers_unconfirmed`) are not checked for presence. They were added at
  different points in the ledger's history: `run_id` appears in only 6% of
  rows, `duration_seconds` in 49%. Requiring them would fail on all pre-
  existing rows.
- Duplicate `run_id` values within the same project are reported as warnings
  rather than errors because they do not indicate data corruption, only a
  potential collision in the ID generator.

## Non-goals

- Fixing gate.py's builtin handler to produce string verdicts. That is a
  separate bug fix in the gate engine, not this oracle's job.
- Trend analysis (pass rate changes, domain failure frequency, timing
  budgets). Structural integrity is the gate criterion; analytics is a
  follow-up.
