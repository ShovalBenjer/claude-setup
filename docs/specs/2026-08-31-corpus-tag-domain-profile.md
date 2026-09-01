# Corpus Tag Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/tag_domain_profile.py

## Problem

heading_tag_profile.py profiles headings by chunk tags.
heading_domain_profile.py profiles headings by semantic domains.
No tool cross-tabulates chunk_tags.tag with chunk_domains.domain to measure
which tags co-occur with which domains, or how domain classifications
distribute across tag assignments.

## Solution

A new tool `tools/corpus/tag_domain_profile.py` with four subcommands:

- `by-tag [--db PATH] [--json]`: domain distribution per tag, showing
  distinct domains, tagged chunks, and classified chunks.
- `by-domain [--db PATH] [--json]`: tag distribution per domain, showing
  distinct tags, classified chunks, and tagged chunks.
- `concentration [--db PATH] [--json]`: per-tag domain diversity with
  domain ratio, ordered by distinct domains descending.
- `summary [--db PATH] [--json]`: aggregate statistics including total
  tags, domains, tags with domains, multi-domain tags, multi-domain
  rate, and distinct tag-domain pairs.
- `selftest`: exercises 14 checks covering per-tag domain counts,
  per-domain tag counts, concentration ratios, summary totals,
  JSON round-trip, and empty corpus.

### Design properties

- **Tag-domain join**: joins chunk_tags with chunk_domains on chunk_id
  to associate tags with semantic domain classifications.
- **Co-occurrence mapping**: reveals which tags co-occur with which
  domains, useful for understanding the relationship between manual
  tags and automated domain classification.
- **Multi-domain detection**: summary tracks tags spanning more than
  one domain, indicating tags that cross semantic boundaries.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/tag_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-tag-domain-profile.md`: this spec

## See also

- [corpus-heading-tag-profile](2026-08-31-corpus-heading-tag-profile.md):
  profiles headings by chunk tags; this tool profiles tags by domains.
- [corpus-heading-domain-profile](2026-08-31-corpus-heading-domain-profile.md):
  profiles headings by semantic domains; this tool profiles domains by
  tags.

## Non-goals

- Automatic domain assignment from tag patterns.
- Tag prediction from domain classifications.
- Tag-domain merging or deduplication.
- Cross-tag domain normalization.
