# Corpus Liveness Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/liveness_tag_profile.py

## Problem

publisher_tag_profile.py profiles tags by publisher.
liveness_citation_profile.py correlates liveness with citations.
liveness_edge_profile.py correlates liveness with claim edges.
No tool joins sources.liveness with chunk_tags to measure whether
live sources carry different tag vocabularies than stale or archived
ones, or how tag scores vary across liveness states.

## Solution

A new tool `tools/corpus/liveness_tag_profile.py` with four
subcommands:

- `by-liveness [--db PATH] [--json]`: tag distribution per source
  liveness state, showing distinct tags, tag assignments, tagged
  chunk count, and average score.
- `by-tag [--db PATH] [--json]`: liveness distribution per tag,
  showing how many liveness states each tag spans, with assignment
  counts and average score.
- `concentration [--db PATH] [--json]`: per-liveness tag
  concentration, filtered to states with at least two tag
  assignments, ordered by diversity ratio (distinct tags divided
  by total assignments).
- `summary [--db PATH] [--json]`: aggregate statistics including
  total liveness states, states with tags, coverage ratio, distinct
  tags, total assignments, average tags per state, single-state tag
  count, and single-state tag rate.
- `selftest`: exercises 14 checks covering per-state tag counts,
  tag-to-state distributions, concentration filtering, summary
  totals, JSON round-trip, and empty corpus.

### Design properties

- **Source-based liveness attribution**: tags are attributed to the
  liveness state of the source that contains the tagged chunk.
- **Vocabulary diversity**: concentration subcommand reveals whether
  actively maintained sources carry broader tag vocabularies than
  stale or archived ones.
- **Single-state exclusivity**: summary tracks tags that appear in
  only one liveness state, indicating liveness-specific topical
  content.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/liveness_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-liveness-tag-profile.md`: this spec

## See also

- [corpus-liveness-citation-profile](2026-08-31-corpus-liveness-citation-profile.md):
  correlates liveness with citations; this tool correlates liveness
  with chunk tags.
- [corpus-liveness-edge-profile](2026-08-31-corpus-liveness-edge-profile.md):
  correlates liveness with claim edges; this tool adds the tag
  dimension.

## Non-goals

- Liveness state prediction from tag patterns.
- Automatic tag recommendation based on source liveness.
- Tag-based staleness detection.
- Liveness-driven tag pruning or promotion.
