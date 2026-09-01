# Corpus Kind Liveness Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/kind_liveness_profile.py

## Problem

license_liveness_profile.py profiles licenses by source liveness.
publisher_liveness_profile.py profiles publishers by source liveness.
No tool cross-tabulates sources.kind with sources.liveness to measure
which source kinds remain live versus going stale or archived, or how
content volume distributes across kind-liveness combinations.

## Solution

A new tool `tools/corpus/kind_liveness_profile.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: liveness distribution per source
  kind, showing distinct liveness states, total sources, and total
  bytes.
- `by-liveness [--db PATH] [--json]`: kind distribution per liveness
  state, showing distinct kinds, total sources, and total bytes per
  state.
- `concentration [--db PATH] [--json]`: per-kind liveness
  concentration, filtered to kinds with at least two sources,
  ordered by how many states each kind spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total kinds, total liveness states, total sources, kinds spanning
  multiple states, multi-state rate, distinct kind-liveness pairs,
  and live source rate.
- `selftest`: exercises 14 checks covering per-kind state counts,
  per-liveness kind counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Source-level cross-tabulation**: operates on sources table
  only, joining kind with liveness without descending to chunks.
- **Format health visibility**: reveals whether certain source
  formats (local_md, repo, paper, etc.) correlate with better
  maintenance or higher staleness rates.
- **Multi-state detection**: summary tracks kinds that span
  more than one liveness state, indicating mixed maintenance
  patterns within a format category.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/kind_liveness_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-kind-liveness-profile.md`: this spec

## See also

- [corpus-license-liveness-profile](2026-08-31-corpus-license-liveness-profile.md):
  profiles licenses by liveness state; this tool profiles source
  kinds by liveness state.
- [corpus-publisher-liveness-profile](2026-08-31-corpus-publisher-liveness-profile.md):
  profiles publishers by liveness; this tool adds the kind
  dimension.

## Non-goals

- Kind-based liveness prediction.
- Automatic staleness alerts per source kind.
- Kind-driven liveness state transitions.
- Format migration recommendations from liveness patterns.
