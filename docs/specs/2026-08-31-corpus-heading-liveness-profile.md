# Corpus Heading Liveness Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_liveness_profile.py

## Problem

heading_status_profile.py cross-tabulates headings with chunk status.
heading_citation_correlation.py correlates headings with citations.
No tool cross-tabulates chunks.heading_path with sources.liveness to
measure whether certain document sections appear more in live versus
stale or archived sources, or how section structure distributes across
source maintenance states.

## Solution

A new tool `tools/corpus/heading_liveness_profile.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: liveness distribution per heading
  path, showing distinct liveness states, total chunks, and total words.
- `by-liveness [--db PATH] [--json]`: heading distribution per source
  liveness state, showing distinct headings, total chunks, and total
  words per liveness.
- `concentration [--db PATH] [--json]`: per-heading liveness
  concentration, filtered to headings with at least two chunks,
  ordered by how many liveness states each heading spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total headings, total chunks, total live chunks, overall live rate,
  headings spanning multiple liveness states, multi-liveness rate,
  and distinct heading-liveness pairs.
- `selftest`: exercises 14 checks covering per-heading liveness counts,
  per-liveness heading counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate heading paths with source liveness states.
- **Section maintenance visibility**: reveals which document sections
  appear across maintained versus unmaintained sources.
- **Multi-liveness detection**: summary tracks headings that span
  more than one liveness state, indicating sections present in both
  maintained and unmaintained sources.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_liveness_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-liveness-profile.md`: this spec

## See also

- [corpus-heading-status-profile](2026-08-31-corpus-heading-status-profile.md):
  profiles headings by chunk status; this tool profiles headings by
  source liveness.
- [corpus-liveness-status-profile](2026-08-31-corpus-liveness-status-profile.md):
  profiles liveness by status; this tool adds the heading dimension
  to liveness.

## Non-goals

- Heading maintenance scoring from liveness patterns.
- Automatic heading archival based on source liveness.
- Liveness prediction from heading path.
- Heading-driven source lifecycle transitions.
