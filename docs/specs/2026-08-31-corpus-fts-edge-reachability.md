# Corpus FTS Edge Reachability

**Date:** 2026-08-31
**Status:** done
**Tool:** tools/corpus/fts_edge_reachability.py

## Problem

tag_edge_correlation.py correlates tags with claim_edges.
domain_edge_depth.py correlates domains with claim_edges.
No tool measures how claim edge density relates to FTS word count,
which edge types connect the most searchable content, or which
sources have the highest edge-to-word ratios.

## Solution

A new tool `tools/corpus/fts_edge_reachability.py` with four
subcommands:

- `by-type [--db PATH] [--json]`: edge FTS statistics grouped by
  edge type, including source and target chunk counts and average
  source word count.
- `density [--db PATH] [--json]`: edge density per source relative
  to FTS word count, measured as distinct edges per 1000 words.
- `coverage [--db PATH] [--json]`: per-chunk edge and FTS
  statistics for edged chunks, including edge role counts and
  status-based searchability.
- `summary [--db PATH] [--json]`: aggregate statistics including
  edged accepted chunks, unedged accepted chunks, edge coverage
  rate, and edges per 1000 words.
- `selftest`: exercises 14 checks covering per-type statistics,
  edge density computation, word count accuracy, per-chunk
  coverage, searchability flags, summary totals, JSON serialisation,
  and empty corpus.

### Design properties

- **Distinct edge counting**: density uses COUNT(DISTINCT edge_id)
  rather than COUNT(*) to avoid double-counting edges whose source
  and target chunks belong to the same source.
- **Status-aware searchability**: marks edged chunks as searchable
  only when their status is accepted, since quarantined or rejected
  chunks may not appear in search results.
- **Duplication-safe aggregation**: uses subqueries to compute word
  totals separately from edge counts, avoiding row multiplication
  from the edges join.

## Results

- Selftest: 14 checks, all passing
- Lint: clean (ruff)

## Scope

- `tools/corpus/fts_edge_reachability.py`: new tool
- `docs/specs/2026-08-31-corpus-fts-edge-reachability.md`: this spec

## See also

- [corpus-tag-edge-correlation](2026-08-31-corpus-tag-edge-correlation.md):
  correlates tags with edges; this tool correlates FTS word
  count with edges.
- [corpus-domain-edge-depth](2026-08-31-corpus-domain-edge-depth.md):
  correlates domains with edges; this tool measures edge
  density per source.
- [corpus-fts-citation-reachability](2026-08-31-corpus-fts-citation-reachability.md):
  measures citation density relative to FTS word count; this tool
  measures edge density relative to FTS word count.

## Non-goals

- FTS query ranking or relevance tuning.
- Edge-weighted search result boosting.
- Full-text content analysis of edged passages.
- Cross-source edge flow measurement.
