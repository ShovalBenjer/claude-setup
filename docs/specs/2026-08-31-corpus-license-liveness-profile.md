# Corpus License Liveness Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_liveness_profile.py

## Problem

publisher_liveness_profile.py profiles publishers by source liveness.
publisher_status_profile.py profiles publishers by chunk status.
No tool cross-tabulates sources.license_spdx with sources.liveness to
measure which licenses correlate with live versus stale or archived
sources, or how content volume distributes across license-liveness
combinations.

## Solution

A new tool `tools/corpus/license_liveness_profile.py` with four
subcommands:

- `by-license [--db PATH] [--json]`: liveness distribution per
  license, showing distinct liveness states, total sources, and
  total bytes.
- `by-liveness [--db PATH] [--json]`: license distribution per
  liveness state, showing distinct licenses, total sources, and
  total bytes per state.
- `concentration [--db PATH] [--json]`: per-license liveness
  concentration, filtered to licenses with at least two sources,
  ordered by how many states each license spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total licenses, total liveness states, total sources, licenses
  spanning multiple states, multi-state rate, distinct
  license-liveness pairs, and live source rate.
- `selftest`: exercises 14 checks covering per-license state
  counts, per-liveness license counts, concentration filtering,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Source-level cross-tabulation**: operates on sources table
  only, joining license_spdx with liveness without descending to
  chunks.
- **License health visibility**: reveals whether certain licenses
  correlate with better source maintenance (live) or abandonment
  (stale, archived).
- **Multi-state detection**: summary tracks licenses that span
  more than one liveness state, indicating mixed maintenance
  patterns within a license category.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_liveness_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-liveness-profile.md`: this spec

## See also

- [corpus-publisher-liveness-profile](2026-08-31-corpus-publisher-liveness-profile.md):
  profiles publishers by liveness state; this tool profiles
  licenses by liveness state.
- [corpus-publisher-status-profile](2026-08-31-corpus-publisher-status-profile.md):
  profiles publishers by chunk status; this tool adds the license
  dimension to liveness.

## Non-goals

- License compatibility analysis from liveness patterns.
- Automatic license migration recommendations.
- License-driven liveness state transitions.
- Liveness prediction from license metadata.
