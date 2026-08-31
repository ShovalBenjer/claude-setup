# Corpus License Status Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/license_status_profile.py

## Problem

license_liveness_profile.py profiles licenses by source liveness.
publisher_status_profile.py profiles publishers by chunk status.
No tool joins sources.license_spdx with chunks.status to measure which
licenses correlate with accepted versus quarantined or rejected chunks,
or how chunk quality distributes across license types.

## Solution

A new tool `tools/corpus/license_status_profile.py` with four
subcommands:

- `by-license [--db PATH] [--json]`: chunk status distribution per
  license, showing distinct statuses, total chunks, and total words.
- `by-status [--db PATH] [--json]`: license distribution per chunk
  status, showing distinct licenses, total chunks, and total words
  per status.
- `acceptance [--db PATH] [--json]`: per-license acceptance rate,
  filtered to licenses with at least two chunks, ordered by
  acceptance rate descending.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total licenses, licenses with chunks, total chunks, total
  accepted, overall acceptance rate, licenses spanning multiple
  statuses, multi-status rate, and distinct license-status pairs.
- `selftest`: exercises 14 checks covering per-license status
  counts, per-status license counts, acceptance rate filtering,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins sources.license_spdx with chunks.status
  through source_id, bridging source licensing with chunk quality.
- **Quality by license**: reveals whether certain license types
  correlate with higher acceptance rates or more rejections.
- **Acceptance rate filtering**: excludes licenses with fewer than
  two chunks to avoid misleading single-sample rates.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/license_status_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-license-status-profile.md`: this spec

## See also

- [corpus-license-liveness-profile](2026-08-31-corpus-license-liveness-profile.md):
  profiles licenses by liveness state; this tool profiles
  licenses by chunk status.
- [corpus-publisher-status-profile](2026-08-31-corpus-publisher-status-profile.md):
  profiles publishers by chunk status; this tool adds the license
  dimension.

## Non-goals

- License quality scoring from acceptance history.
- Automatic license restriction based on rejection rates.
- License-driven chunk status transitions.
- Acceptance rate prediction from license metadata.
