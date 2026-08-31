# Corpus FTS Citation Reachability

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/fts_citation_reachability.py

## Problem

tag_citation_correlation.py correlates tags with citations.
domain_citation_profile.py correlates domains with citations.
No tool measures how citation density relates to FTS word count,
which citation tags produce the most searchable content, or which
sources have the highest citation-to-word ratios.

## Solution

A new tool `tools/corpus/fts_citation_reachability.py` with four
subcommands:

- `by-tag [--db PATH] [--json]`: citation FTS statistics grouped
  by citation tag, including cited chunk count, verification rate,
  and average chunk word count.
- `density [--db PATH] [--json]`: citation density per source
  relative to FTS word count, measured as citations per 1000 words.
- `coverage [--db PATH] [--json]`: per-chunk citation and FTS
  statistics for cited chunks, including status-based searchability.
- `summary [--db PATH] [--json]`: aggregate statistics including
  cited accepted chunks, uncited accepted chunks, citation coverage
  rate, and citations per 1000 words.
- `selftest`: exercises 14 checks covering per-tag statistics,
  citation density computation, word count accuracy, per-chunk
  coverage, searchability flags, summary totals, JSON serialisation,
  and empty corpus.

### Design properties

- **Word count correlation**: measures citation density relative to
  chunk word count, surfacing whether longer or shorter chunks
  attract more citations.
- **Status-aware searchability**: marks cited chunks as searchable
  only when their status is accepted, since quarantined or rejected
  chunks may not appear in search results.
- **Duplication-safe aggregation**: uses subqueries to compute word
  totals separately from citation counts, avoiding row multiplication
  from the citations join.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/fts_citation_reachability.py`: new tool
- `docs/specs/2026-08-31-corpus-fts-citation-reachability.md`: this spec

## See also

- [corpus-tag-citation-correlation](2026-08-31-corpus-tag-citation-correlation.md):
  correlates tags with citations; this tool correlates FTS word
  count with citations.
- [corpus-domain-citation-profile](2026-08-31-corpus-domain-citation-profile.md):
  correlates domains with citations; this tool measures citation
  density per source.

## Non-goals

- FTS query ranking or relevance tuning.
- Citation-weighted search result boosting.
- Full-text content analysis of cited passages.
- Cross-source citation flow measurement.
