# Corpus Liveness Status Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/liveness_status_profile.py

## Problem

liveness_tag_profile.py profiles liveness by tag vocabulary.
status_tag_profile.py profiles chunk status by tag vocabulary.
No tool joins sources.liveness with chunks.status to measure whether
stale or archived sources accumulate quarantined or rejected chunks,
or how chunk quality distributes across source liveness states.

## Solution

A new tool `tools/corpus/liveness_status_profile.py` with four
subcommands:

- `by-liveness [--db PATH] [--json]`: chunk status distribution per
  source liveness state, showing distinct statuses, total chunks,
  and total words.
- `by-status [--db PATH] [--json]`: liveness distribution per chunk
  status, showing distinct liveness states, total chunks, and total
  words per status.
- `acceptance [--db PATH] [--json]`: per-liveness acceptance rate,
  filtered to states with at least two chunks, ordered by
  acceptance rate descending.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total liveness states, states with chunks, total chunks, total
  accepted, overall acceptance rate, states spanning multiple
  statuses, multi-status rate, and distinct liveness-status pairs.
- `selftest`: exercises 14 checks covering per-liveness status
  counts, per-status liveness counts, acceptance rate filtering,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins sources.liveness with chunks.status
  through source_id, bridging source maintenance state with chunk
  quality outcomes.
- **Staleness quality signal**: reveals whether stale or archived
  sources correlate with lower acceptance rates, indicating that
  unmaintained sources produce lower-quality chunks.
- **Acceptance rate filtering**: excludes liveness states with fewer
  than two chunks to avoid misleading single-sample rates.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/liveness_status_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-liveness-status-profile.md`: this spec

## See also

- [corpus-liveness-cross-analysis](2026-08-31-corpus-liveness-cross-analysis.md):
  broader liveness analysis; this tool focuses on the liveness-status
  correlation specifically.
- [corpus-kind-status-profile](2026-08-31-corpus-kind-status-profile.md):
  profiles source kinds by chunk status; this tool profiles liveness
  by chunk status.

## Non-goals

- Liveness-based quality prediction.
- Automatic chunk re-evaluation when source liveness changes.
- Liveness-driven chunk status transitions.
- Quality-based staleness detection.
