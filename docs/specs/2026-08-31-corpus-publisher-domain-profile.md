# Corpus Publisher Domain Profile

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/publisher_domain_profile.py

## Problem

publisher_tag_profile.py profiles publishers by tag vocabulary.
domain_analysis.py profiles domains corpus-wide and per source.
No tool joins sources.publisher with chunk_domains to measure which
publishers concentrate which knowledge domains, whether publisher
breadth correlates with domain diversity, or how domain scores
vary by publisher.

## Solution

A new tool `tools/corpus/publisher_domain_profile.py` with four
subcommands:

- `by-publisher [--db PATH] [--json]`: domain distribution per
  publisher, showing distinct domain count, total domain
  assignments, classified chunk count, and average domain score.
- `by-domain [--db PATH] [--json]`: publisher distribution per
  domain, showing how many named publishers contribute each
  domain and average scores, ordered by publisher breadth.
- `concentration [--db PATH] [--json]`: per-publisher domain
  concentration as the ratio of distinct domains to total
  assignments, filtered to publishers with at least two
  assignments, ordered from most concentrated to most diverse.
- `summary [--db PATH] [--json]`: aggregate statistics including
  total publishers, publishers with classified chunks, coverage
  ratio, average domains per publisher, single-publisher domains,
  and the single-publisher domain rate.
- `selftest`: exercises 14 checks covering per-publisher domain
  counts, per-domain publisher counts, concentration ratios, null
  publisher handling, summary totals, and empty corpus.

### Design properties

- **Named publisher counting**: COUNT(DISTINCT publisher) excludes
  NULL publishers from aggregate counts, matching the sources
  table convention. NULL-publisher chunks still appear in
  per-publisher groupings but do not inflate publisher metrics.
- **Single-publisher domain rate**: measures what fraction of
  domains are exclusive to one named publisher, identifying
  editorial specialisation versus shared coverage.
- **Concentration threshold**: only publishers with at least two
  domain assignments appear in the concentration view.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/publisher_domain_profile.py`: new tool
- `docs/specs/2026-08-31-corpus-publisher-domain-profile.md`: this spec

## See also

- [corpus-publisher-tag-profile](2026-08-31-corpus-publisher-tag-profile.md):
  profiles publishers by tag vocabulary; this tool profiles
  publishers by semantic domain vocabulary.
- [corpus-domain-analysis](2026-08-31-corpus-domain-analysis.md):
  profiles domains corpus-wide; this tool stratifies domains
  by their originating publisher.

## Non-goals

- Publisher normalisation or deduplication.
- Domain recommendation based on publisher patterns.
- Publisher quality scoring beyond domain diversity.
- Cross-publisher domain migration tracking.
