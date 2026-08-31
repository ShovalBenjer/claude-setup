# Corpus Publisher Citation Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_citation_profile.py

## Problem

publisher_tag_profile.py profiles publishers by tag vocabulary.
publisher_domain_profile.py profiles publishers by semantic domain.
No tool joins sources.publisher with citations to measure which
publishers attract the most citations, how verification rates vary
by publisher, or which citation targets are exclusive to a single
publisher.

## Solution

A new tool `tools/corpus/publisher_citation_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: citation distribution per
  publisher, showing total citations, citing chunk count, verified
  citation count, distinct target count, and verification rate.
- `by-tag [--db PATH] [--json]`: citation tag distribution per
  publisher, showing how citation tags (ref, note, etc.) distribute
  across publishers.
- `verification [--db PATH] [--json]`: verification rate per
  publisher, ordered from highest to lowest, showing verified and
  unverified counts.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, publishers with citations, coverage ratio,
  total citations, verification rate, average citations per
  publisher, single-publisher targets, and single-publisher target
  rate.
- `selftest`: exercises 14 checks covering per-publisher citation
  counts, verification rates, citation tag counts, null publisher
  handling, summary totals, and empty corpus.

### Design properties

- **Named publisher counting**: COUNT(DISTINCT publisher) excludes
  NULL publishers from aggregate counts, matching the sources
  table convention. NULL-publisher chunks still appear in
  per-publisher groupings but do not inflate publisher metrics.
- **Single-publisher target rate**: measures what fraction of
  citation target URIs are cited exclusively by one named
  publisher, identifying editorial citation exclusivity.
- **Verification as dimension**: treats citation.verified as a
  first-class grouping axis alongside the publisher dimension.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_citation_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-citation-profile.md`: this spec

## See also

- [corpus-publisher-tag-profile](2026-08-31-corpus-publisher-tag-profile.md):
  profiles publishers by tag vocabulary; this tool profiles
  publishers by citation patterns.
- [corpus-publisher-domain-profile](2026-08-31-corpus-publisher-domain-profile.md):
  profiles publishers by semantic domain; this tool adds the
  citation dimension.

## Non-goals

- Publisher normalisation or deduplication.
- Citation quality scoring beyond verification rate.
- Cross-publisher citation network analysis.
- Publisher ranking or recommendation.
