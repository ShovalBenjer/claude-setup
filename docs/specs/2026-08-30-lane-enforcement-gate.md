# Lane-Enforcement Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** lane_enforcement

## Problem

Cross-lane work is the most frequently logged lesson in state/lessons.jsonl.
A session opens in claude-setup and does resume-engine work, or opens in the
resume repo and edits harness files. The charters exist to prevent this, but
nothing mechanical enforces them at gate time. The gate can pass while the
session's own claims row names the wrong lane.

## Solution

A new gate builtin `lane_enforcement` reads the most recent row from
`state/claims.jsonl`, resolves the lane letter through `tools/lib/lanes.py`
(which handles the 2026-07-30 renumber), and fails the gate if the resolved
lane is not A (the harness lane).

The oracle is `tools/audit/lane_check.py` with a 7-case selftest covering:
missing file (exit 2), empty file (exit 1), correct lane, wrong lane,
pre-cutover scheme resolution, latest-row-wins, and latest-wrong-lane.

## Scope

- `tools/audit/lane_check.py`: oracle with `run_check()` and `selftest`
- `tools/gate/gate.py`: `lane_enforcement` builtin, registered in `BUILTINS`
- `quality-contract.json`: `lane_enforcement` domain entry

## Design decisions

- Only the latest row is checked, not the full history. A session that starts
  in the wrong lane and corrects itself should pass.
- The resolver uses `tools/lib/lanes.py`, so historical rows with pre-cutover
  lane letters are handled correctly.
- Exit 2 (cannot measure) when the claims file is missing, so CI runners
  without a claims ledger report N/A rather than FAIL.

## Non-goals

- Enforcing that a claim row was written before work started (rule 1 from
  charters.md). That would require correlating timestamps with git history
  and is a separate, harder problem.
- Cross-repo enforcement (verifying that a session in new-recruit claims
  lane B). Each repo's contract enforces its own lane.
