# Skip Tracker Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** skip_tracker

## Problem

L-2026-07-29-i records the incident: a generator bug deleted content from 12
shipped files, four tests responded with `pytest.skip()` instead of failing,
the suite reported "89 passed, 4 skipped", and the gate read that as PASS.
The artifacts were visibly corrupt while every automated check was green.

The gate's unit domain checks exit codes. A skip is exit 0. The skip count
was the signal, and it was invisible.

## Solution

A new `cmd` domain `skip_tracker` in `quality-contract.json` runs
`python tools/audit/skip_tracker.py check --project .`. The tool runs each
test suite (root `tests/` and `intent-control-plane`), parses the pytest
summary line for pass and skip counts, and compares them against a baseline
stored in `state/skip-baseline.json`.

The domain fails when the skip count for any suite exceeds its baseline. A
decrease in skips (tests un-skipped) is fine and does not fail.

## Scope

- `tools/audit/skip_tracker.py`: new oracle with `check`, `update`, and
  `selftest` subcommands
- `state/skip-baseline.json`: baseline file recording expected skip counts
- `quality-contract.json`: `skip_tracker` domain entry (cmd, timeout 600s)

## Design decisions

- Runs its own pytest invocations rather than parsing saved output from the
  `unit` domain. The unit domain chains four commands and does not save
  intermediate output. Duplicating the test run costs ~30s but keeps the
  domains decoupled.
- Timeout set to 600s because both test suites run sequentially.
- The baseline is a committed JSON file so changes are visible in review.
  Run `update` to reset it after legitimate skip changes (e.g., a platform
  now supported, a dependency added).
- Returns exit 2 (cannot-measure) when no baseline exists, matching the
  gate's convention for domains that need setup.

## Non-goals

- Replacing the unit domain. This domain checks skip regression, not test
  correctness.
- Tracking xfail or warning counts. Those are informational; skips are the
  signal that hides failures.
