# Corpus Heading Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/heading_citation_profile.py

## Problem

heading_domain_profile.py profiles headings by semantic domains.
heading_tag_profile.py profiles headings by chunk tags.
No tool cross-tabulates chunks.heading_path with chunks.citation_count to
measure which document sections carry the most citations, or how citation
density distributes across heading paths.

## Solution

A new tool `tools/corpus/heading_citation_profile.py` with four
subcommands:

- `by-heading [--db PATH] [--json]`: citation statistics per heading
  path, showing total citations, average, min, max, and citation spread.
- `by-bucket [--db PATH] [--json]`: heading distribution per citation
  bucket (0, 1-5, 6-20, 21+), showing distinct headings, total chunks,
  and total citations per bucket.
- `concentration [--db PATH] [--json]`: per-heading citation spread,
  ordered by spread descending to surface headings with uneven citation
  distribution across their chunks.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  headings, chunks, citations, average citations, cited headings, cited
  heading rate, and uneven citation headings.
- `selftest`: exercises 14 checks covering per-heading citation spread,
  per-bucket chunk counts, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Single-table analysis**: queries chunks table directly without
  joins, since both heading_path and citation_count are chunk-level
  attributes.
- **Section citation mapping**: reveals which document sections carry
  the highest citation density, useful for identifying high-value
  content sections.
- **Citation asymmetry detection**: concentration view surfaces headings
  where citation counts vary widely across chunks.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/heading_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-heading-citation-profile.md`: this spec

## See also

- [corpus-heading-domain-profile](2026-08-31-corpus-heading-domain-profile.md):
  profiles headings by semantic domains; this tool profiles headings by
  citation count.
- [corpus-heading-tag-profile](2026-08-31-corpus-heading-tag-profile.md):
  profiles headings by chunk tags; this tool adds the citation dimension
  to heading.

## Non-goals

- Automatic citation count normalization across sections.
- Citation prediction from heading structure.
- Heading reorganization from citation density.
- Cross-heading citation merging.
