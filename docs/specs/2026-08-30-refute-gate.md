# Refute Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** refute

## Problem

`tools/refute/refute.py` runs each claim's own falsifier and reports whether
it holds, is refuted, or has a broken verifier. The tool existed with a
selftest and was listed in AGENTS.md as repo upkeep the gate reads, but
nothing in the quality contract invoked it. A refuted claim would pass the
gate silently.

## Solution

A new `cmd` domain `refute` in `quality-contract.json` runs
`python tools/refute/refute.py run`. The tool's exit code is the count of
REFUTED plus BROKEN claims, so exit 0 means all claims hold.

Claims with unmet preconditions (e.g. `needs=deployed` on a CI runner without
`~/.claude`) report cannot-measure and do not count toward the exit code.
This is the tool's existing behavior, so no modification was needed.

## Scope

- `quality-contract.json`: `refute` domain entry (cmd, no builtin)
- No changes to `refute.py` itself

## Design decisions

- A `cmd` domain rather than a builtin, because `refute.py run` already has
  the right exit-code contract (0 = pass, N = count of failures) and needs
  no wrapping logic.
- Timeout set to 300s because the refutation engine runs 26 claims
  sequentially, several of which invoke mutation specs that take 5-10s each.
- The append to `state/refutations.jsonl` is a side effect of the run and is
  expected (append-only ledger).

## Non-goals

- Adding new claims. The obligation set is maintained separately; this domain
  enforces whatever claims exist.
- Gating on cannot-measure claims. A runner without `~/.claude` should not
  fail for infrastructure it was never meant to have.
