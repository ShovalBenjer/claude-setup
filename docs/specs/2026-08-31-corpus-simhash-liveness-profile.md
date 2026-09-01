# Corpus Simhash Liveness Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_liveness_profile.py

## Problem

simhash_kind_profile.py profiles simhash groups by source kind.
simhash_status_profile.py profiles simhash groups by chunk status.
No tool cross-tabulates chunks.simhash with sources.liveness to measure
whether near-duplicate clusters appear more in live versus stale or
archived sources, or how content similarity distributes across source
maintenance states.

## Solution

A new tool `tools/corpus/simhash_liveness_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: liveness distribution per simhash
  collision group (groups with 2+ chunks), showing distinct liveness
  states, total chunks, and total words.
- `by-liveness [--db PATH] [--json]`: simhash distribution per source
  liveness state, showing distinct simhash values, total chunks, and
  total words per liveness.
- `concentration [--db PATH] [--json]`: per-group liveness diversity
  with liveness ratio, filtered to collision groups (2+ chunks),
  ordered by liveness diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, cross-liveness groups,
  cross-liveness rate, and distinct simhash-liveness pairs.
- `selftest`: exercises 14 checks covering per-group liveness counts,
  per-liveness simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate simhash collision groups with source maintenance states.
- **Maintenance duplication**: reveals whether near-duplicate content
  persists across live and unmaintained sources, indicating stale
  copies that could be pruned.
- **Cross-liveness detection**: summary tracks collision groups
  spanning more than one liveness state.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_liveness_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-liveness-profile.md`: this spec

## See also

- [corpus-simhash-kind-profile](2026-08-31-corpus-simhash-kind-profile.md):
  profiles simhash groups by source kind; this tool profiles simhash
  groups by source liveness.
- [corpus-simhash-status-profile](2026-08-31-corpus-simhash-status-profile.md):
  profiles simhash groups by chunk status; this tool adds the liveness
  dimension to simhash.

## Non-goals

- Automatic pruning of stale near-duplicates.
- Liveness prediction from simhash similarity.
- Simhash threshold tuning from liveness patterns.
- Stale content archival based on duplication.
