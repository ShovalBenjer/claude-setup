# Bus Integrity Gate Domain

**Date:** 2026-08-30
**Status:** done
**Gate domain:** bus_integrity

## Problem

`tools/bus/bus.py verify` checks the hash-chain integrity of
`state/bus.jsonl`, the event bus ledger. The tool existed with a selftest and
was mentioned in AGENTS.md, but nothing in the quality contract invoked it.
A tampered or corrupted bus ledger would pass the gate silently.

## Solution

A new `cmd` domain `bus_integrity` in `quality-contract.json` runs
`python tools/bus/bus.py verify`. The tool exits 0 when the chain is intact
and nonzero when a chained row's hash does not match.

Pre-chain rows (written before hash chaining was added) carry no hash and
are reported but not counted as failures. This is the tool's existing
behavior.

## Scope

- `quality-contract.json`: `bus_integrity` domain entry (cmd, no builtin)
- No changes to `bus.py` itself

## Design decisions

- A `cmd` domain rather than a builtin, because `bus.py verify` already has
  the right exit-code contract.
- No timeout override needed; verification is a single pass over the ledger
  file and completes in under a second.
- Named `bus_integrity` rather than `bus` to be explicit about what the
  domain checks (the ledger's hash chain, not the bus tool's functionality).

## Non-goals

- Detecting truncation of the newest rows. As `bus.py verify` itself states,
  nothing outside the file records where the tip should be.
- Verifying pre-chain rows. They carry no hash and cannot be verified.
