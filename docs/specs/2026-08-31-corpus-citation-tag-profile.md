# Corpus Citation Tag Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/citation_tag_profile.py

## Problem

The existing citation_analysis.py and citation_verification.py tools
report basic per-tag counts and verification rates, but no tool
cross-tabulated citation tags against other corpus dimensions.
Understanding which source kinds produce which citation tags, how
tag usage varies across semantic domains, and whether certain tags
systematically lack locators required joining across multiple tables
manually.

## Solution

A new tool `tools/corpus/citation_tag_profile.py` with four
subcommands:

- `by-kind [--db PATH] [--json]`: citation tag distribution per
  source kind (paper, local_md, repo, etc.), showing which source
  types produce which citation patterns.
- `by-domain [--db PATH] [--json]`: citation tag distribution per
  chunk domain, revealing how citation practices differ across
  semantic domains.  Requires the chunk_domains table; returns
  empty if absent.
- `locator-affinity [--db PATH] [--json]`: locator presence and
  verification rates per citation tag, showing which tags
  systematically include or omit locators.
- `summary [--db PATH] [--json]`: aggregate tag profile statistics
  including total citations, distinct tags, source kinds cited,
  tags with highest and lowest locator rates, and overall locator
  and verification rates.
- `selftest`: exercises 14 checks covering by-kind results,
  tag-source-kind combinations, by-domain results, tag-domain
  combinations, locator-affinity tag enumeration, per-tag locator
  rates, summary totals, best/worst tag identification, JSON
  serialisation, and empty corpus.

### Design properties

- **Cross-dimensional**: joins citations with sources and
  chunk_domains to reveal patterns invisible in single-table
  analysis.
- **Locator affinity**: quantifies which citation tags tend to
  include specific locators, enabling targeted documentation
  improvement.
- **Graceful degradation**: by-domain returns empty when the
  chunk_domains table is absent, rather than failing.
- **Accepted-only scope**: all queries join through accepted chunks.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/citation_tag_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-citation-tag-profile.md`: this spec

## See also

- [corpus-citation-analysis](2026-08-31-corpus-citation-analysis.md):
  reports basic per-tag counts; this tool cross-tabulates tags
  against source kinds and domains.
- [corpus-citation-locator-analysis](2026-08-31-corpus-citation-locator-analysis.md):
  analyses locator formats and completeness; this tool analyses
  locator presence per tag as one of several cross-dimensions.
- [corpus-citation-verification](2026-08-31-corpus-citation-verification.md):
  reports verification rates per tag; this tool adds source kind
  and domain context to those rates.
- [corpus-domain-analysis](2026-08-30-corpus-domain-analysis.md):
  analyses domain coverage; this tool analyses how citation
  practices vary by domain.

## Non-goals

- Tag normalisation or reclassification.
- Citation recommendation based on tag patterns.
- Tag co-occurrence network analysis.
- Temporal tag usage trends.
