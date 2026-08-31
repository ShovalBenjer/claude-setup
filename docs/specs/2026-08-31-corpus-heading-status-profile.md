# Corpus Heading Status Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_status_profile.py

## Problem

heading_citation_correlation.py correlates headings with citations.
heading_tag_correlation.py correlates headings with tags.
No tool cross-tabulates chunks.heading_path with chunks.status to
measure whether certain document sections produce more accepted versus
quarantined or rejected chunks, or how quality distributes across
document structure.

## Solution

A new tool `tools/corpus/heading_status_profile.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: status distribution per heading
  path, showing distinct statuses, total chunks, and total words.
- `by-status [--db PATH] [--json]`: heading distribution per chunk
  status, showing distinct headings, total chunks, and total words
  per status.
- `acceptance [--db PATH] [--json]`: per-heading acceptance rate,
  filtered to headings with at least two chunks, ordered by
  acceptance rate descending.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total headings, total chunks, total accepted, overall acceptance
  rate, headings with multiple statuses, multi-status rate, and
  distinct heading-status pairs.
- `selftest`: exercises 14 checks covering per-heading status counts,
  per-status heading counts, acceptance filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Single-table analysis**: operates on the chunks table only,
  cross-tabulating heading_path with status without joining sources.
- **Section quality measurement**: reveals which document sections
  consistently produce accepted content versus sections that draw
  quarantined or rejected chunks.
- **Multi-status detection**: summary tracks headings that contain
  chunks in more than one status, indicating sections with mixed
  quality outcomes.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_status_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-status-profile.md`: this spec

## See also

- [corpus-heading-citation-correlation](2026-08-25-corpus-heading-citation-correlation.md):
  correlates headings with citations; this tool correlates headings
  with chunk status.
- [corpus-liveness-status-profile](2026-08-31-corpus-liveness-status-profile.md):
  profiles liveness by status; this tool adds the heading dimension
  to status.

## Non-goals

- Heading quality scoring from status patterns.
- Automatic heading reclassification based on status.
- Status prediction from heading path.
- Heading-driven content migration.
