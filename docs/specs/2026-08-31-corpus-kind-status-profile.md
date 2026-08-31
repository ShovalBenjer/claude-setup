# Corpus Kind Status Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/kind_status_profile.py

## Problem

kind_liveness_profile.py profiles source kinds by liveness state.
license_status_profile.py profiles licenses by chunk status.
No tool joins sources.kind with chunks.status to measure which source
kinds produce accepted versus quarantined or rejected chunks, or how
chunk quality distributes across source formats.

## Solution

A new tool `tools/corpus/kind_status_profile.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: chunk status distribution per
  source kind, showing distinct statuses, total chunks, and total
  words.
- `by-status [--db PATH] [--json]`: kind distribution per chunk
  status, showing distinct kinds, total chunks, and total words
  per status.
- `acceptance [--db PATH] [--json]`: per-kind acceptance rate,
  filtered to kinds with at least two chunks, ordered by
  acceptance rate descending.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total kinds, kinds with chunks, total chunks, total accepted,
  overall acceptance rate, kinds spanning multiple statuses,
  multi-status rate, and distinct kind-status pairs.
- `selftest`: exercises 14 checks covering per-kind status counts,
  per-status kind counts, acceptance rate filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins sources.kind with chunks.status
  through source_id, bridging source format with chunk quality.
- **Format quality visibility**: reveals whether certain source
  formats consistently produce higher acceptance rates or more
  rejections.
- **Acceptance rate filtering**: excludes kinds with fewer than
  two chunks to avoid misleading single-sample rates.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/kind_status_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-kind-status-profile.md`: this spec

## See also

- [corpus-kind-liveness-profile](2026-08-31-corpus-kind-liveness-profile.md):
  profiles source kinds by liveness state; this tool profiles
  source kinds by chunk status.
- [corpus-license-status-profile](2026-08-31-corpus-license-status-profile.md):
  profiles licenses by chunk status; this tool adds the kind
  dimension.

## Non-goals

- Kind-based quality scoring from acceptance history.
- Automatic format restriction based on rejection rates.
- Kind-driven chunk status transitions.
- Acceptance rate prediction from source format metadata.
