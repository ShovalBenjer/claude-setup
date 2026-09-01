# Corpus Heading Publisher Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_publisher_profile.py

## Problem

heading_kind_profile.py cross-tabulates headings with source kind.
heading_liveness_profile.py cross-tabulates headings with source liveness.
No tool cross-tabulates chunks.heading_path with sources.publisher to
measure whether certain document sections appear more from specific
publishers, or how section structure distributes across content sources.

## Solution

A new tool `tools/corpus/heading_publisher_profile.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: publisher distribution per heading
  path, showing distinct publishers, total chunks, and total words.
- `by-publisher [--db PATH] [--json]`: heading distribution per
  publisher, showing distinct headings, total chunks, and total words
  per publisher.
- `concentration [--db PATH] [--json]`: per-heading publisher
  concentration, filtered to headings with at least two chunks,
  ordered by how many publishers each heading spans.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total headings, total chunks, total publishers, headings spanning
  multiple publishers, multi-publisher rate, and distinct
  heading-publisher pairs.
- `selftest`: exercises 14 checks covering per-heading publisher counts,
  per-publisher heading counts, concentration filtering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Cross-table join**: joins chunks with sources on source_id to
  associate heading paths with publisher identities.
- **Publisher coverage**: reveals which document sections draw content
  from multiple publishers versus sections confined to one publisher.
- **Multi-publisher detection**: summary tracks headings that span
  more than one publisher, indicating sections with diverse sourcing.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_publisher_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-publisher-profile.md`: this spec

## See also

- [corpus-heading-kind-profile](2026-08-31-corpus-heading-kind-profile.md):
  profiles headings by source kind; this tool profiles headings by
  publisher.
- [corpus-publisher-status-profile](2026-08-31-corpus-publisher-status-profile.md):
  profiles publishers by status; this tool adds the heading dimension
  to publisher.

## Non-goals

- Publisher recommendation from heading patterns.
- Automatic heading attribution based on publisher.
- Publisher prediction from heading path.
- Heading-driven publisher transitions.
