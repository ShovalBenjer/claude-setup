# Corpus Heading Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_tag_profile.py

## Problem

heading_publisher_profile.py profiles headings by source publisher.
heading_license_profile.py profiles headings by source license.
No tool cross-tabulates chunks.heading_path with chunk_tags.tag to measure
which topic tags appear under which document sections, or how tag vocabulary
distributes across heading paths.

## Solution

A new tool `tools/corpus/heading_tag_profile.py` with four subcommands:

- `by-heading [--db PATH] [--json]`: tag distribution per heading path,
  showing distinct tags, tagged chunks, tag assignments, and average score.
- `by-tag [--db PATH] [--json]`: heading distribution per tag, showing
  distinct headings, tagged chunks, and average score per tag.
- `concentration [--db PATH] [--json]`: per-heading tag diversity with
  tag ratio, ordered by tag diversity.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  headings, tagged chunks, tags, multi-tag headings, multi-tag rate,
  and distinct heading-tag pairs.
- `selftest`: exercises 14 checks covering per-heading tag counts,
  per-tag heading counts, concentration ratios, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Chunk-level join**: joins chunks with chunk_tags on chunk_id to
  associate heading paths with topic annotations.
- **Section topic mapping**: reveals which document sections carry
  which topic tags, useful for understanding content organization.
- **Multi-tag detection**: summary tracks headings spanning more
  than one tag, indicating topically diverse sections.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-tag-profile.md`: this spec

## See also

- [corpus-heading-publisher-profile](2026-08-31-corpus-heading-publisher-profile.md):
  profiles headings by source publisher; this tool profiles headings
  by chunk tags.
- [corpus-heading-license-profile](2026-08-31-corpus-heading-license-profile.md):
  profiles headings by source license; this tool adds the tag
  dimension to heading.

## Non-goals

- Automatic tag assignment from heading structure.
- Tag prediction from heading path patterns.
- Heading reorganization from tag distribution.
- Cross-heading tag merging.
