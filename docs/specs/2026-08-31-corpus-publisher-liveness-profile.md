# Corpus Publisher Liveness Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_liveness_profile.py

## Problem

publisher_tag_profile.py profiles publishers by tag vocabulary.
publisher_domain_profile.py profiles publishers by domain coverage.
No tool cross-tabulates sources.publisher with sources.liveness to
measure which publishers maintain live sources, which have gone
stale, or how content volume distributes across publisher-liveness
combinations.

## Solution

A new tool `tools/corpus/publisher_liveness_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: liveness distribution per
  publisher, showing distinct liveness states, total sources,
  total bytes, and source count.
- `by-liveness [--db PATH] [--json]`: publisher distribution per
  liveness state, showing distinct publishers, total sources, and
  total bytes per state.
- `concentration [--db PATH] [--json]`: per-publisher liveness
  concentration, filtered to named publishers with at least two
  sources, ordered by how many states each publisher spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, total liveness states, total sources,
  publishers spanning multiple states, multi-state rate, distinct
  publisher-liveness pairs, and live source rate.
- `selftest`: exercises 14 checks covering per-publisher state
  counts, per-liveness publisher counts, concentration filtering,
  summary totals, JSON round-trip, and empty corpus.

### Design properties

- **Source-level cross-tabulation**: operates on sources table
  only, joining publisher with liveness without descending to
  chunks.
- **Maintenance visibility**: reveals which publishers actively
  maintain their sources versus letting them go stale or archiving
  them.
- **Multi-state detection**: summary tracks publishers that span
  more than one liveness state, indicating mixed maintenance
  patterns.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_liveness_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-liveness-profile.md`: this spec

## See also

- [corpus-publisher-tag-profile](2026-08-31-corpus-publisher-tag-profile.md):
  profiles publishers by tag vocabulary; this tool profiles
  publishers by liveness state.
- [corpus-liveness-citation-profile](2026-08-31-corpus-liveness-citation-profile.md):
  correlates liveness with citations; this tool cross-tabulates
  publisher and liveness directly.

## Non-goals

- Publisher reliability scoring from liveness patterns.
- Automatic staleness alerts per publisher.
- Publisher-driven liveness state transitions.
- Liveness prediction from publisher metadata.
