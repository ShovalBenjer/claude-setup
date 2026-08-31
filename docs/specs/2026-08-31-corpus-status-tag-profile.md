# Corpus Status Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/status_tag_profile.py

## Problem

status_citation_profile.py profiles statuses by citation patterns.
status_edge_profile.py profiles statuses by claim edge patterns.
No tool joins chunks.status with chunk_tags to measure whether
accepted chunks carry different tag vocabularies than quarantined
or rejected ones, or how tag scores vary across chunk statuses.

## Solution

A new tool `tools/corpus/status_tag_profile.py` with four
subcommands:

- `by-status [--db PATH] [--json]`: tag distribution per chunk
  status, showing distinct tags, tag assignments, tagged chunk
  count, and average score.
- `by-tag [--db PATH] [--json]`: status distribution per tag,
  showing how many statuses each tag spans, with assignment counts
  and average score.
- `concentration [--db PATH] [--json]`: per-status tag
  concentration, filtered to statuses with at least two tag
  assignments, ordered by diversity ratio (distinct tags divided
  by total assignments).
- `summary [--db PATH] [--json]`: aggregate statistics including
  total statuses, statuses with tags, coverage ratio, distinct
  tags, total assignments, average tags per status, single-status
  tag count, and single-status tag rate.
- `selftest`: exercises 14 checks covering per-status tag counts,
  tag-to-status distributions, concentration filtering, summary
  totals, JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level status attribution**: tags are attributed directly
  to the chunk's own status, not the source's liveness.
- **Vocabulary diversity**: concentration subcommand reveals whether
  accepted chunks carry broader tag vocabularies than quarantined
  or rejected ones.
- **Single-status exclusivity**: summary tracks tags that appear in
  only one status, indicating quality-tier-specific topical content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/status_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-status-tag-profile.md`: this spec

## See also

- [corpus-status-citation-profile](2026-08-31-corpus-status-citation-profile.md):
  profiles statuses by citation patterns; this tool profiles
  statuses by chunk tag patterns.
- [corpus-status-edge-profile](2026-08-31-corpus-status-edge-profile.md):
  profiles statuses by claim edge patterns; this tool adds the
  tag dimension.

## Non-goals

- Status prediction from tag patterns.
- Automatic tag recommendation based on chunk status.
- Tag-based chunk promotion or demotion decisions.
- Status-driven tag pruning or enrichment.
