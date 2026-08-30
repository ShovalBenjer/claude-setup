# Waiver-Falsifier Execution

**Date:** 2026-08-30
**Status:** done
**Gate domain:** n/a (extends gate.py internals)

## Problem

A waiver in `quality-contract.json` is a time-bounded claim about a measurement.
The existing `confirm` field checks a string against the domain's own command
output, but only works when the domain has a `cmd` and the string-in-output test
is sufficient. Some waivers need a dedicated verification command that is
different from the domain's regular check, or the domain uses a builtin/artifact
and has no `cmd` at all.

## Solution

A waiver may now carry a `command` field naming a dedicated falsifier. The gate
runs it and reads the exit code: 0 means the waiver's claim still holds, nonzero
means the claim is stale and the waiver fails. Exit 2 (CANNOT_MEASURE) is the
host-specific escape hatch, same as for `confirm`.

If both `command` and `confirm` are present, the confirm string is checked in the
falsifier's output rather than the domain's own command.

## Schema

```json
{
  "waived": {
    "reason": "3 tests fail on sqlite teardown",
    "until": "2026-10-01",
    "command": "python -c \"import tests; print(tests.count_sqlite_failures())\"",
    "confirm": "3 failures"
  }
}
```

`command` alone: exit code decides. `command` + `confirm`: string match in
falsifier output decides. `confirm` alone: existing behavior (domain's `cmd`
output).

## Scope

- `tools/gate/gate.py`: `eval_domain`, `confirm_waiver`, selftest section 3d
- No contract changes (no active waivers to convert)

## Non-goals

- Converting existing waivers (there are none active)
- Changing the `confirm`-only path (backward compatible)
