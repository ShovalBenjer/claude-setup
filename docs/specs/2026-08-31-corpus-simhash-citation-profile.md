# Corpus Simhash Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/simhash_citation_profile.py

## Problem

simhash_domain_profile.py profiles simhash groups by semantic domains.
simhash_tag_profile.py profiles simhash groups by chunk tags.
No tool cross-tabulates chunks.simhash with chunks.citation_count to measure
whether near-duplicate clusters differ in citation activity, or how citation
density distributes across simhash collision groups.

## Solution

A new tool `tools/corpus/simhash_citation_profile.py` with four
subcommands:

- `by-simhash [--db PATH] [--json]`: citation statistics per simhash
  collision group (groups with 2+ chunks), showing total citations,
  average, min, max, and citation spread.
- `by-bucket [--db PATH] [--json]`: simhash distribution per citation
  bucket (0, 1-5, 6-20, 21+), showing distinct simhash values, total
  chunks, and total citations per bucket.
- `concentration [--db PATH] [--json]`: per-group citation spread,
  filtered to collision groups (2+ chunks), ordered by citation spread
  descending to surface groups with uneven citation distribution.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total simhashes, collision groups, uneven citation groups, uneven
  citation rate, total citations, and average citations.
- `selftest`: exercises 14 checks covering per-group citation spread,
  per-bucket chunk counts, concentration ordering, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Single-table analysis**: queries chunks table directly without
  source joins, since citation_count is a chunk-level attribute.
- **Citation asymmetry detection**: reveals whether near-duplicate
  content carries different citation counts, indicating that one copy
  is more referenced than another.
- **Bucket aggregation**: groups citation counts into meaningful ranges
  for high-level distribution analysis.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/simhash_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-simhash-citation-profile.md`: this spec

## See also

- [corpus-simhash-domain-profile](2026-08-31-corpus-simhash-domain-profile.md):
  profiles simhash groups by semantic domains; this tool profiles simhash
  groups by citation count.
- [corpus-simhash-tag-profile](2026-08-31-corpus-simhash-tag-profile.md):
  profiles simhash groups by chunk tags; this tool adds the citation
  dimension to simhash.

## Non-goals

- Automatic citation count reconciliation across near-duplicates.
- Citation prediction from simhash similarity.
- Simhash threshold tuning from citation patterns.
- Citation merging across duplicate chunks.
