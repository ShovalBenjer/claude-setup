# Corpus Simhash Status Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_status_profile.py

## Problem

simhash_edge_profile.py profiles simhash collision groups by claim edges.
No tool cross-tabulates chunks.simhash with chunks.status to measure
whether near-duplicate clusters concentrate in accepted versus
quarantined or rejected chunks, or how quality distributes across
content similarity groups.

## Solution

A new tool `tools/corpus/simhash_status_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: status distribution per simhash
  collision group (groups with 2+ chunks), showing distinct statuses,
  total chunks, and total words.
- `by-status [--db PATH] [--json]`: simhash distribution per chunk
  status, showing distinct simhash values, total chunks, and total
  words per status.
- `concentration [--db PATH] [--json]`: per-group status breakdown
  with acceptance rate, filtered to collision groups (2+ chunks),
  ordered by status diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, chunks in collisions,
  mixed-status groups, mixed-status rate, and distinct
  simhash-status pairs.
- `selftest`: exercises 14 checks covering per-group status counts,
  per-status simhash counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Single-table analysis**: operates on the chunks table only,
  grouping by simhash to identify collision clusters.
- **Quality in duplicates**: reveals whether near-duplicate content
  receives consistent quality judgments or mixed statuses.
- **Mixed-status detection**: summary tracks collision groups with
  more than one status, flagging inconsistent quality decisions
  across similar content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_status_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-status-profile.md`: this spec

## See also

- [corpus-simhash-edge-profile](2026-08-31-corpus-simhash-edge-profile.md):
  profiles simhash groups by claim edges; this tool profiles simhash
  groups by chunk status.
- [corpus-heading-status-profile](2026-08-31-corpus-heading-status-profile.md):
  profiles headings by status; this tool profiles simhash groups by
  status.

## Non-goals

- Automatic deduplication from simhash collisions.
- Status prediction from simhash similarity.
- Simhash threshold tuning from status patterns.
- Near-duplicate merging based on quality scores.
