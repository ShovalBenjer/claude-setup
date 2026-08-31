# Corpus Publisher Status Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_status_profile.py

## Problem

publisher_liveness_profile.py profiles publishers by source liveness.
publisher_tag_profile.py profiles publishers by tag vocabulary.
No tool joins sources.publisher with chunks.status to measure which
publishers produce accepted versus quarantined or rejected chunks,
or how chunk quality distributes across publishers.

## Solution

A new tool `tools/corpus/publisher_status_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: chunk status distribution per
  publisher, showing distinct statuses, total chunks, and total words.
- `by-status [--db PATH] [--json]`: publisher distribution per chunk
  status, showing distinct publishers, total chunks, and total words
  per status.
- `acceptance [--db PATH] [--json]`: per-publisher acceptance rate,
  filtered to publishers with at least two chunks, ordered by
  acceptance rate descending.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, publishers with chunks, total chunks, total
  accepted, overall acceptance rate, publishers spanning multiple
  statuses, multi-status rate, and distinct publisher-status pairs.
- `selftest`: exercises 14 checks covering per-publisher status
  counts, per-status publisher counts, acceptance rate filtering,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins sources.publisher with chunks.status
  through source_id, bridging source metadata with chunk quality.
- **Quality visibility**: reveals which publishers consistently
  produce accepted chunks and which have higher quarantine or
  rejection rates.
- **Acceptance rate filtering**: concentration subcommand excludes
  publishers with fewer than two chunks to avoid misleading
  single-sample rates.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_status_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-status-profile.md`: this spec

## See also

- [corpus-publisher-liveness-profile](2026-08-31-corpus-publisher-liveness-profile.md):
  profiles publishers by liveness state; this tool profiles
  publishers by chunk status.
- [corpus-status-edge-profile](2026-08-31-corpus-status-edge-profile.md):
  correlates chunk status with claim edges; this tool correlates
  publisher identity with chunk status.

## Non-goals

- Publisher reliability scoring from acceptance history.
- Automatic publisher blocklisting from rejection rates.
- Publisher-driven chunk status transitions.
- Acceptance rate prediction from publisher metadata.
