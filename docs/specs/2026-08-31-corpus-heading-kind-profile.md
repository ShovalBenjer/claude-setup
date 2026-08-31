# Corpus Heading Kind Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_kind_profile.py

## Problem

heading_status_profile.py cross-tabulates headings with chunk status.
heading_liveness_profile.py cross-tabulates headings with source liveness.
No tool cross-tabulates chunks.heading_path with sources.kind to
measure whether certain document sections appear more in local markdown
versus repos or papers, or how section structure distributes across
source formats.

## Solution

A new tool `tools/corpus/heading_kind_profile.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: kind distribution per heading
  path, showing distinct kinds, total chunks, and total words.
- `by-kind [--db PATH] [--json]`: heading distribution per source
  kind, showing distinct headings, total chunks, and total words
  per kind.
- `concentration [--db PATH] [--json]`: per-heading kind
  concentration, filtered to headings with at least two chunks,
  ordered by how many kinds each heading spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total headings, total chunks, total kinds, headings spanning
  multiple kinds, multi-kind rate, and distinct heading-kind pairs.
- `selftest`: exercises 14 checks covering per-heading kind counts,
  per-kind heading counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate heading paths with source format types.
- **Format coverage**: reveals which document sections appear across
  multiple source formats versus sections confined to one format.
- **Multi-kind detection**: summary tracks headings that span
  more than one source kind, indicating sections present across
  different source formats.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_kind_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-kind-profile.md`: this spec

## See also

- [corpus-heading-liveness-profile](2026-08-31-corpus-heading-liveness-profile.md):
  profiles headings by source liveness; this tool profiles headings by
  source kind.
- [corpus-kind-status-profile](2026-08-31-corpus-kind-status-profile.md):
  profiles kinds by status; this tool adds the heading dimension
  to kind.

## Non-goals

- Heading format recommendation from kind patterns.
- Automatic heading migration across source kinds.
- Kind prediction from heading path.
- Heading-driven format transitions.
